from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from schemas.plants import PlantResponse
from schemas.predict_response import PlantDetail
from utils.middlewares.verify_token import verify_firebase_token
from schemas.diseases import DiseaseResponse
from db.firestore import db
from constants.collection_name import (
    FIRESTORE_COLLECTION_PLANTS,
    FIRESTORE_COLLECTION_DISEASES,
)

router = APIRouter(prefix="/predict", tags=["predict"])
@router.get(
    "/detail", response_model=PlantDetail, dependencies=[Depends(verify_firebase_token)]
)
async def get_plant_and_disease_detail(
    plant_id: str,
    disease_id: Optional[str] = Query(
        None, description="Filter tanaman berdasarkan ID Kategori"
    ),
):
    try:
        plant_doc = (
            await db.collection(FIRESTORE_COLLECTION_PLANTS).document(plant_id).get()
        )
        if not plant_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Tanaman dengan ID '{plant_id}' tidak ditemukan",
            )

        plant_data = plant_doc.to_dict() or {}
        if not plant_data:
            raise HTTPException(
                status_code=500,
                detail=f"Data tanaman dengan ID '{plant_id}' tidak valid",
            )

        plant_response = {**plant_data, "id": plant_doc.id}
        plant = PlantResponse(**plant_response)

        disease = None
        if disease_id:
            disease_doc = await (
                db.collection(FIRESTORE_COLLECTION_DISEASES).document(disease_id).get()
            )
            if not disease_doc.exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"Penyakit dengan ID '{disease_id}' tidak ditemukan",
                )

            disease_data = disease_doc.to_dict() or {}
            if not disease_data:
                raise HTTPException(
                    status_code=500,
                    detail=f"Data penyakit dengan ID '{disease_id}' tidak valid",
                )

            disease_response = {
                **disease_data,
                "id": disease_doc.id,
            }
            disease = DiseaseResponse(**disease_response)

        return PlantDetail(plant_data=plant, disease_data=disease)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Terjadi kesalahan saat mengambil detail: {str(e)}"
        )
