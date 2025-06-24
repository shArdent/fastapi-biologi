from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Optional
from google.cloud.exceptions import GoogleCloudError
from google.cloud.firestore_v1 import (
    Increment,
    SERVER_TIMESTAMP,
    Query as FirestoreQuery,
)
from firebase_admin import auth

from db.firestore import db
from schemas.users import User
from schemas.my_plants import (
    MyPlantSummary,
    MyPlantCreate,
    PaginatedMyPlantSummary,
    MyPlantUpdate,
    SuccessUpdatePlant,
    SuccessResponse,
    SuccessCreatePlant,
)
from utils.middlewares.verify_token import verify_firebase_token
from utils.middlewares.verify_user_id_match import verify_user_id_match
from constants.collection_name import (
    FIRESTORE_COLLECTION_USERS,
    FIRESTORE_COLLECTION_MY_PLANTS,
    FIRESTORE_COLLECTION_PLANTS,
    FIRESTORE_COLLECTION_DISEASES,
    FIRESTORE_DOCUMENT_METADATA,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register")
def register_user(profile: User, user=Depends(verify_firebase_token)):
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
        doc_ref.set(
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
def register_admin(user=Depends(verify_firebase_token)):
    uid = user.get("uid")

    try:
        user_doc = db.collection(FIRESTORE_COLLECTION_USERS).document(uid).get()

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
