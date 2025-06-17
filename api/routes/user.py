from fastapi import APIRouter, HTTPException, Depends, status
from google.cloud.exceptions import GoogleCloudError
from firebase_admin import firestore

from db.firestore import db
from schemas.users import User
from schemas.my_plants import MyPlantCreate
from utils.verify_token import verify_firebase_token
from constants.collection_name import FIRESTORE_COLLECTION_USERS, FIRESTORE_COLLECTION_MY_PLANTS, FIRESTORE_COLLECTION_PLANTS, FIRESTORE_COLLECTION_DISEASES

router = APIRouter(prefix="/users", tags=["register"])

@router.post("/register")
def register_user(profile: User, user=Depends(verify_firebase_token)):
    uid = user.get("uid")
    email = user.get("email")

    try:
        existing = db.collection(FIRESTORE_COLLECTION_USERS).where("username", "==", profile.username).limit(1).get()
    except GoogleCloudError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")

    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username sudah digunakan")

    try:
        doc_ref = db.collection(FIRESTORE_COLLECTION_USERS).document(uid)
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

@router.post("/{user_id}/my-plants", status_code=status.HTTP_201_CREATED)
def add_my_plant(user_id: str, plant_data: MyPlantCreate):
    try:
        my_plants_collection = db.collection(FIRESTORE_COLLECTION_USERS).document(user_id).collection(FIRESTORE_COLLECTION_MY_PLANTS)

        plant_ref = db.collection(FIRESTORE_COLLECTION_PLANTS).document(plant_data.plant_id)

        if not plant_ref.get().exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tanaman dengan ID '{plant_data.plant_id}' tidak ditemukan.")

        data_to_save = {
            "nickname": plant_data.nickname,
            "plant_ref" : plant_ref,
            "added_at": firestore.SERVER_TIMESTAMP
        }

        if plant_data.disease_id:
            disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(plant_data.disease_id)

            if not disease_ref.get().exists:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Penyakit dengan ID '{plant_data.disease_id}' tidak ditemukan.")
            
            data_to_save["disease_ref"] = disease_ref

        _, new_plant_ref = my_plants_collection.add(data_to_save)
        
        return {
            "message": "Tanaman berhasil ditambahkan!",
            "user_id": user_id,
            "new_plat_id": new_plant_ref.id
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
