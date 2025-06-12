from fastapi import APIRouter, HTTPException
from firebase_admin import firestore

from db.firestore import db
from constants.collection_name import FIRESTORE_COLLECTION_PLANTS
from schemas.plants import Plants
from schemas.default_success import SuccessResponse

router = APIRouter(prefix="/plants", tags=["plants"])

@router.post("/", response_model=SuccessResponse, status_code=201)
def add_new_plant(new_plant: Plants):
    try:

        print(new_plant.name)

        is_exist = db.collection(FIRESTORE_COLLECTION_PLANTS).document(new_plant.name).get().exists
        if is_exist:
            raise HTTPException(
                status_code=400,
                detail=f"Tanaman dengan nama {new_plant.name} sudah ada"
            )

        db.collection(FIRESTORE_COLLECTION_PLANTS).document(new_plant.name).set(new_plant.model_dump())


        return {"message": "Tanaman baru berhasil ditambahkan"}
    except Exception as e:
        return {"error": str(e), "message": "Gagal menambahkan tanaman baru"}

@router.get("/", response_model=list[Plants])
def get_all_plants():
    try:
        plants_ref = db.collection(FIRESTORE_COLLECTION_PLANTS)
        docs = plants_ref.stream()

        plants = [Plants(**doc.to_dict()) for doc in docs]

        return plants
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat mengambil data tanaman: {str(e)}"
        )
