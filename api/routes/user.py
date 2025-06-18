from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Optional
from google.cloud.exceptions import GoogleCloudError
from firebase_admin import firestore

from db.firestore import db
from schemas.users import User
from schemas.my_plants import MyPlantCreate, PaginatedMyPlantSummary, MyPlantUpdate, SuccessUpdatePlant, SuccessResponse
from utils.verify_token import verify_firebase_token
from constants.collection_name import FIRESTORE_COLLECTION_USERS, FIRESTORE_COLLECTION_MY_PLANTS, FIRESTORE_COLLECTION_PLANTS, FIRESTORE_COLLECTION_DISEASES

router = APIRouter(prefix="/users", tags=["users"])

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

@router.get("/{user_id}/my-plants", response_model=PaginatedMyPlantSummary)
def get_all_my_plants(
    user_id: str,
    page_size: int = Query(10, gt=0, le=50, description="Number of items per page"),
    last_doc_id: Optional[str] = Query(None, description="ID of the last document from the previous page to fetch the next page")
):
    try:
        my_plants_ref = db.collection(FIRESTORE_COLLECTION_USERS).document(user_id).collection(FIRESTORE_COLLECTION_MY_PLANTS)

        query = my_plants_ref.order_by("added_at", direction=FirestoreQuery.DESCENDING)
            
        if last_doc_id:
            last_doc_snapshot = my_plants_ref.document(last_doc_id).get()
            if last_doc_snapshot.exists:
                query = query.start_after(last_doc_snapshot)
            else:
                return PaginatedPlantSummary(data=[], last_doc_id=None)

        query = query.limit(page_size)
        my_plants_docs = list(query.stream())

        summary_list = []
        for doc in my_plants_docs:
            my_plant_data = doc.to_dict()
            
            plant_ref = my_plant_data.get('plant_ref')
            if not plant_ref:
                continue

            plant_doc = plant_ref.get()
            if not plant_doc.exists:
                plant_name = "Data Tanaman Tidak Ditemukan"
            else:
                plant_name = plant_doc.to_dict().get('name', 'Tanpa Nama')
                plant_id = plant_doc.id

            my_plant_data_sent = {
                "id" : doc.id,
                "nickname": my_plant_data.get('nickname', ''),
                "plant_name": plant_name,
                "plant_id": plant_doc.id
            }

            disease_ref = my_plant_data.get('disease_ref')
            disease_id = None
            disease_name = None

            if disease_ref:
                disease_doc = disease_ref.get()
                if disease_doc.exists:
                    disease_id = disease_doc.id
                    disease_name = disease_doc.to_dict().get('name', 'Tanpa Nama')

            my_plant_data_sent["disease_id"] = disease_id
            my_plant_data_sent["disease_name"] = disease_name

            summary_list.append(
                MyPlantSummary(**my_plant_data_sent)
            )

        new_last_doc_id = my_plants_docs[-1].id if len(my_plants_docs) == page_size else None

        return PaginatedPlantSummary(data=summary_list, last_doc_id=new_last_doc_id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{user_id}/my-plants/{my_plant_id}", status_code=status.HTTP_200_OK, response_model=SuccessUpdatePlant)
def update_my_plant(user_id: str, my_plant_id: str, plant_update_data: MyPlantUpdate):
    try:
        doc_ref = db.collection(FIRESTORE_COLLECTION_USERS).document(user_id).collection(FIRESTORE_COLLECTION_MY_PLANTS).document(my_plant_id)
        main_doc = doc_ref.get()

        if not main_doc.exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tanaman dengan ID '{my_plant_id}' tidak ditemukan.")

        data_to_update = {}

        if plant_update_data.nickname is not None:
            data_to_update["nickname"] = plant_update_data.nickname

        if plant_update_data.disease_id is not None:
            disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(plant_update_data.disease_id)
            if not disease_ref.get().exists:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Penyakit dengan ID '{plant_update_data.disease_id}' tidak ditemukan.")
            data_to_update["disease_ref"] = disease_ref
        elif plant_update_data.disease_id is None:
            data_to_update["disease_ref"] = None

        if not data_to_update:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tidak ada data untuk diupdate.")

        doc_ref.update(data_to_update)

        updated_doc = doc_ref.get()
        updated_doc_id = updated_doc.id
        updated_doc_data = updated_doc.to_dict()
        updated_doc_plant_id = updated_doc_data['plant_ref'].id

        return {
            "message": "Tanaman berhasil diupdate!",
            "my_plant_id": updated_doc_id,
            "updated_data": {
                "plant_id": updated_doc_plant_id,
                "nickname": updated_doc_data['nickname'],
                "disease_id": plant_update_data.disease_id
            }
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/{user_id}/my-plants/{my_plant_id}", status_code=status.HTTP_200_OK, response_model=SuccessResponse)
def delete_my_plant(user_id: str, my_plant_id: str):
    try:
        doc_ref = db.collection(FIRESTORE_COLLECTION_USERS).document(user_id).collection(FIRESTORE_COLLECTION_MY_PLANTS).document(my_plant_id)
        
        if not doc_ref.get().exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tanaman dengan ID '{my_plant_id}' tidak ditemukan untuk dihapus.")

        doc_ref.delete()

        return {
            "message": "Tanaman berhasil dihapus.",
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
