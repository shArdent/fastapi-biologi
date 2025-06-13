from fastapi import APIRouter, HTTPException

from db.firestore import db
from constants.collection_name import FIRESTORE_COLLECTION_DISEASES
from schemas.diseases import Diseases
from schemas.default_success import SuccessResponse

router = APIRouter(prefix="/diseases", tags=["diseases"])

@router.post("/", response_model=SuccessResponse, status_code=201)
def add_new_disease(new_disease: Diseases):
    try:

        is_exist = db.collection(FIRESTORE_COLLECTION_DISEASES).document(new_disease.name).get().exists
        if is_exist:
            raise HTTPException(
                status_code=400,
                detail=f"Penyakit dengan nama {new_disease.name} sudah ada"
            )

        db.collection(FIRESTORE_COLLECTION_DISEASES).document(new_disease.name).set(new_disease.model_dump())


        return {"message": "Penyakit baru berhasil ditambahkan"}
    except Exception as e:
        return {"error": str(e), "message": "Gagal menambahkan penyakit baru"}

@router.get("/", response_model=list[Diseases])
def get_all_disease():
    try:
        diseases_ref = db.collection(FIRESTORE_COLLECTION_DISEASES)
        docs = diseases_ref.stream()

        diseases = [Diseases(**doc.to_dict()) for doc in docs]

        return diseases
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat mengambil data penyakit: {str(e)}"
        )
    
@router.get("/{disease_name}", response_model=Diseases)
def get_disease_by_name(disease_name:str):
    try:
        disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(disease_name)
        disease_doc = disease_ref.get()

        if not disease_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Penyakit dengan nama {disease_name} tidak ditemukan"
            )

        return Diseases(**disease_doc.to_dict())
    
    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat mengambil data penyakit: {str(e)}"
        )

@router.patch("/{disease_name}", response_model=SuccessResponse)
def update_disease(disease_name: str, updated_disease: Diseases):
    try:
        disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(disease_name)
        disease_doc = disease_ref.get()

        if not disease_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"penyakit dengan nama {disease_name} tidak ditemukan"
            )

        disease_ref.update(updated_disease).model_dump(exclude_unset=True)

        return {"message": "Penyakit berhasil diperbarui"}
    
    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat memperbarui data penyakit: {str(e)}"
        )
    
@router.delete("/{disease_name}", response_model=SuccessResponse)
def delete_disease(disease_name: str):
    try:
        disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(disease_name)
        disease_doc = disease_ref.get()

        if not disease_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Penyakit dengan nama {disease_name} tidak ditemukan"
            )

        disease_ref.delete()

        return {"message": "Penyakit berhasil dihapus"}
    
    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat menghapus data penyakit: {str(e)}"
        )