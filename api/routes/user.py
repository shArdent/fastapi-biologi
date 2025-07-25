from fastapi import APIRouter, HTTPException, Depends, status
from google.cloud.exceptions import GoogleCloudError
from google.cloud.firestore_v1 import (
    SERVER_TIMESTAMP,
    FieldFilter,
)
from firebase_admin import auth

from db.firestore import db
from schemas.users import (
    EmailReq,
    PasswordReq,
    User,
    UserResponse,
    UserUpdate,
)
from schemas.my_plants import (
    SuccessResponse,
)
from utils.middlewares.verify_is_admin import verify_is_admin
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
        existing = await (
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
                "created_at": SERVER_TIMESTAMP,
                "role": "user",
            }
        )

        return SuccessResponse(message="Berhasil melakukan registrasi akun")

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


@router.patch("/{uid}", response_model=SuccessResponse, dependencies=[Depends(verify_firebase_token)])
async def update_user(update_data: UserUpdate, uid=str):
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
                await db.collection(FIRESTORE_COLLECTION_USERS)
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


@router.patch("/email/{uid}", dependencies=[Depends(verify_firebase_token)])
async def update_email(payload: EmailReq, uid:str):
    if not payload.model_dump(exclude_unset=True):
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

        if payload.email:
            existing = (
                await db.collection(FIRESTORE_COLLECTION_USERS)
                .where(filter=FieldFilter("email", "!=", payload.email))
                .where(filter=FieldFilter("uid", "!=", uid))
                .limit(1)
                .get()
            )

            print(existing)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email sudah digunakan oleh user lain",
                )
        auth.update_user(uid=uid, email=payload.email)

        await doc_ref.update(payload.model_dump(exclude_unset=True))

        return SuccessResponse(message="Email berhasil diupdate")

    except GoogleCloudError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengupdate data: {e}",
        )


@router.patch("/password/{uid}")
async def update_password(payload: PasswordReq, uid:str):
    if not payload.model_dump(exclude_unset=True):
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

        auth.update_user(uid=uid, password=payload.password)

        return SuccessResponse(message="Email berhasil diupdate")

    except GoogleCloudError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengupdate data: {e}",
        )


@router.get(
    "/", response_model=list[UserResponse], dependencies=[Depends(verify_is_admin)]
)
async def get_all_user():
    try:
        users_ref = db.collection(FIRESTORE_COLLECTION_USERS).stream()

        users = []
        async for user in users_ref:
            user_data = user.to_dict()
            if user_data:
                ts = user_data.get("created_at")
                user_data["created_at"] = ts.isoformat()
                users.append(UserResponse(**user_data))

        return users

    except HTTPException as he:
        raise he

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengambil data user: {e}",
        )


@router.get(
    "/{uid}",
    response_model=UserResponse,
    dependencies=[Depends(verify_firebase_token)],
)
async def get_user_by_id(uid: str):
    try:
        user_doc = (
            await db.collection(FIRESTORE_COLLECTION_USERS).document(uid).get()
        )

        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User tidak ditemukan.",
            )

        user_data = user_doc.to_dict()

        created_at = user_data.get("created_at")
        if created_at and hasattr(created_at, "isoformat"):
            user_data["created_at"] = created_at.isoformat()

        return UserResponse(**user_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengambil data user: {e}",
        )
