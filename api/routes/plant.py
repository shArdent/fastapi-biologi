from fastapi import APIRouter
from firebase_admin import firestore

from db.firestore import db
from constants.collection_name import FIRESTORE_COLLECTION_PLANTS

router = APIRouter(prefix="/plants", tags=["plants"])

@router.post("/")
def add_new_plant():
    try:
        db.collection(FIRESTORE_COLLECTION_PLANTS).document("tomat").set({
            "name": "Tomat",
            "species": "Unknown",
            "water_frequency": "Weekly",
            "light_requirement": "Indirect sunlight",
            "habitats" : ["Indoor", "Outdoor"],
            "created_at": firestore.firestore.SERVER_TIMESTAMP,
        })


        return {"message": "Tanaman baru berhasil ditambahkan"}
    except Exception as e:
        return {"error": str(e), "message": "Gagal menambahkan tanaman baru"}
