from fastapi import APIRouter, HTTPException, Depends
from google.cloud.exceptions import GoogleCloudError
from firebase_admin import firestore

from db.firestore import db
from schemas.users import User
from utils.verify_token import verify_firebase_token

router = APIRouter(prefix="/users", tags=["register"])

@router.post("/register")
def register_user(profile: User, user=Depends(verify_firebase_token)):
    uid = user.get("uid")
    email = user.get("email")

    try:
        existing = db.collection("users").where("username", "==", profile.username).limit(1).get()
    except GoogleCloudError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")

    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username sudah digunakan")

    try:
        doc_ref = db.collection("users").document(uid)
        doc_ref.set({
            "uid": uid,
            "email": email,
            "username": profile.username,
            "fullname": profile.fullname,
            "phone": profile.phone,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "role": "user",
        })

    except GoogleCloudError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Gagal melakukan registrasi: {e}")
