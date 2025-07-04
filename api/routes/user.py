from fastapi import APIRouter, HTTPException, Depends, status
from google.cloud.exceptions import GoogleCloudError
from google.cloud.firestore_v1 import (
    SERVER_TIMESTAMP,
)
from firebase_admin import auth

from db.firestore import db
from schemas.users import User, UserUpdate
from schemas.my_plants import (
    SuccessResponse,
)
from utils.middlewares.verify_token import verify_firebase_token
from constants.collection_name import (
    FIRESTORE_COLLECTION_USERS,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register")
async def register_user(profile: User, user=Depends(verify_firebase_token)):
    uid = user.get("uid")
    email = user.get("email")

    try:
        existing = (
            db.collection(FIRESTORE_COLLECTION_USERS)
            .where("username", "==", profile.username)
            .limit(1)
            .get()
        )
    except GoogleCloudError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {e}",
        )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username sudah digunakan"
        )

    try:
        doc_ref = db.collection(FIRESTORE_COLLECTION_USERS).document(uid)
        await doc_ref.set(
            {
                "uid": uid,
                "email": email,
                "username": profile.username,
                "fullname": profile.fullname,
                "phone": profile.phone,
                "createdAt": SERVER_TIMESTAMP,
                "role": "user",
            }
        )

    except GoogleCloudError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal melakukan registrasi: {e}",
        )


@router.post("/admin-reg", response_model=SuccessResponse)
async def register_admin(user=Depends(verify_firebase_token)):
    uid = user.get("uid")

    try:
        user_doc = await db.collection(FIRESTORE_COLLECTION_USERS).document(uid).get()

        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Akun tidak ditemukan"
            )

        user_dict = user_doc.to_dict()

        if user_dict is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Akun tidak ditemukan"
            )

        if user_dict["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Anda bukan admin"
            )

        auth.set_custom_user_claims(uid, {"isAdmin": True})

        return SuccessResponse(message="Berhasil login admin")
    except HTTPException as he:
        raise he

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal melakukan registrasi: {e}",
        )


@router.patch("/", response_model=SuccessResponse)
async def update_user(update_data: UserUpdate, user=Depends(verify_firebase_token)):
    uid = user.get("uid")

    if not update_data.model_dump(exclude_unset=True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak ada data yang dikirim untuk diupdate",
        )

    try:
        doc_ref = db.collection(FIRESTORE_COLLECTION_USERS).document(uid)

        if not (await doc_ref.get()).exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User belum terdaftar"
            )

        if update_data.username:
            existing = (
                db.collection(FIRESTORE_COLLECTION_USERS)
                .where("username", "==", update_data.username)
                .where("uid", "!=", uid)
                .limit(1)
                .get()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username sudah digunakan oleh user lain",
                )

        await doc_ref.update(update_data.model_dump(exclude_unset=True))

        return SuccessResponse(message="Profile berhasil diupdate")

    except GoogleCloudError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengupdate data: {e}",
        )
