from fastapi import APIRouter, HTTPException, Query
from google.cloud.firestore_v1 import Increment, field_path
from typing import Optional

from db.firestore import db
from constants.collection_name import FIRESTORE_COLLECTION_PLANTS, FIRESTORE_DOCUMENT_METADATA
from schemas.plants import PlantsPaginatedResponse, Plants
from schemas.default_success import SuccessResponse

router = APIRouter(prefix="/plants", tags=["plants"])

@router.post("/", response_model=SuccessResponse, status_code=201)
def add_new_plant(new_plant: Plants):
    try:
        is_exist = db.collection(FIRESTORE_COLLECTION_PLANTS).document(new_plant.name).get().exists
        if is_exist:
            raise HTTPException(
                status_code=400,
                detail=f"Tanaman dengan nama {new_plant.name} sudah ada"
            )

        db.collection(FIRESTORE_COLLECTION_PLANTS).document(new_plant.name).set(new_plant.model_dump())
        meta_ref = db.collection(FIRESTORE_COLLECTION_PLANTS).document(FIRESTORE_DOCUMENT_METADATA)
        meta_ref.set({"total_items": Increment(1)}, merge=True)

        return SuccessResponse(message="Tanaman berhasil ditambahkan")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"gagal menambah data tanaman: {str(e)}"
        )

@router.get("/", response_model=PlantsPaginatedResponse)
def get_all_plants(
    limit: int = Query(10, ge=1, le=100),
    start_after_doc_id: Optional[str] = Query(None, description="ID dokumen terakhir dari halaman sebelumnya")
):
    try:
        plants_ref = db.collection(FIRESTORE_COLLECTION_PLANTS)
        query = plants_ref.order_by(field_path.FieldPath.document_id())

        if start_after_doc_id:
            start_doc_ref = plants_ref.document(start_after_doc_id).get()
            if not start_doc_ref.exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"Dokumen dengan ID '{start_after_doc_id}' tidak ditemukan."
                )
            query = query.start_after(start_doc_ref)

        docs = query.limit(limit).stream()

        plants = []
        for doc in docs:
            if doc.id == FIRESTORE_DOCUMENT_METADATA:
                continue
            plant_data = doc.to_dict()
            plant_data["id"] = doc.id
            plants.append(Plants(**plant_data))

        meta_doc = plants_ref.document(FIRESTORE_DOCUMENT_METADATA).get()
        if not meta_doc.exists or "total_items" not in meta_doc.to_dict():
            raise HTTPException(status_code=500, detail="Metadata jumlah tanaman tidak tersedia.")

        total_items = meta_doc.to_dict()["total_items"]
        max_page = (total_items + limit - 1) // limit

        return PlantsPaginatedResponse(
            plants=plants,
            total_items=total_items,
            max_page=max_page
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat mengambil data tanaman: {str(e)}"
        )
   
@router.get("/{plant_id}", response_model=Plants)
def get_plant_by_id(plant_id:str):
    try:
        plant_ref = db.collection(FIRESTORE_COLLECTION_PLANTS).document(plant_id)
        plant_doc = plant_ref.get()

        if not plant_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Tanaman dengan nama {plant_id} tidak ditemukan"
            )

        return Plants(**plant_doc.to_dict())
    
    except HTTPException as he:
        raise he

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat mengambil data tanaman: {str(e)}"
        )

@router.patch("/{plant_id}", response_model=SuccessResponse)
def update_plant(plant_id: str, updated_plant: Plants):
    try:
        plant_ref = db.collection(FIRESTORE_COLLECTION_PLANTS).document(plant_id)
        plant_doc = plant_ref.get()

        if not plant_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Tanaman dengan nama {plant_id} tidak ditemukan"
            )

        plant_ref.update(updated_plant.model_dump(exclude_unset=True))

        return {"message": "Tanaman berhasil diperbarui"}
    
    except HTTPException as he:
        raise he

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat memperbarui data tanaman: {str(e)}"
        )
    
@router.delete("/{plant_id}", response_model=SuccessResponse)
def delete_plant(plant_id: str):
    try:
        plant_ref = db.collection(FIRESTORE_COLLECTION_PLANTS).document(plant_id)
        plant_doc = plant_ref.get()

        if not plant_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Tanaman dengan nama {plant_id} tidak ditemukan"
            )

        plant_ref.delete()
        meta_ref = db.collection(FIRESTORE_COLLECTION_PLANTS).document(FIRESTORE_DOCUMENT_METADATA)
        meta_ref.update({"total_items": Increment(-1)})

        return {"message": "Tanaman berhasil dihapus"}
    
    except HTTPException as he:
        raise he

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat menghapus data tanaman: {str(e)}"
        )
