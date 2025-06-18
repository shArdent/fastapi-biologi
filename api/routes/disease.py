from fastapi import APIRouter, Depends, HTTPException, Query
from google.cloud.firestore_v1 import Increment, field_path
from typing import Optional

from db.firestore import db
from constants.collection_name import (
    FIRESTORE_COLLECTION_DISEASES,
    FIRESTORE_DOCUMENT_METADATA,
)
from schemas.diseases import Diseases, DiseasesPaginatedResponse
from schemas.default_success import SuccessResponse
from utils.middlewares.verify_is_admin import verify_is_admin
from utils.middlewares.verify_token import verify_firebase_token

router = APIRouter(prefix="/diseases", tags=["diseases"])


@router.post(
    "/",
    response_model=SuccessResponse,
    status_code=201,
    dependencies=[Depends(verify_is_admin)],
)
def add_new_disease(new_disease: Diseases):
    try:
        is_exist = (
            db.collection(FIRESTORE_COLLECTION_DISEASES)
            .document(new_disease.name)
            .get()
            .exists
        )
        if is_exist:
            raise HTTPException(
                status_code=400,
                detail=f"Penyakit dengan nama {new_disease.name} sudah ada",
            )

        db.collection(FIRESTORE_COLLECTION_DISEASES).document(new_disease.name).set(
            new_disease.model_dump()
        )
        meta_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(
            FIRESTORE_DOCUMENT_METADATA
        )
        meta_ref.set({"total_items": Increment(1)}, merge=True)

        return SuccessResponse(message="Penyakit baru berhasil ditambahkan")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Gagal menambahkan penyakit baru: {str(e)}"
        )


@router.get(
    "/",
    response_model=DiseasesPaginatedResponse,
    dependencies=[Depends(verify_firebase_token)],
)
def get_all_diseases(
    limit: int = Query(10, ge=1, le=100),
    start_after_doc_id: Optional[str] = Query(
        None, description="ID dokumen terakhir dari halaman sebelumnya"
    ),
):
    try:
        diseases_ref = db.collection(FIRESTORE_COLLECTION_DISEASES)
        query = diseases_ref.order_by(field_path.FieldPath.document_id())

        if start_after_doc_id:
            start_doc = diseases_ref.document(start_after_doc_id).get()
            if not start_doc.exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"Dokumen dengan ID '{start_after_doc_id}' tidak ditemukan.",
                )
            query = query.start_after(start_doc)

        docs = query.limit(limit).stream()

        diseases = []
        for doc in docs:
            if doc.id == FIRESTORE_DOCUMENT_METADATA:
                continue
            disease_data = doc.to_dict()
            disease_data["id"] = doc.id
            diseases.append(Diseases(**disease_data))

        meta_doc = diseases_ref.document(FIRESTORE_DOCUMENT_METADATA).get()
        if not meta_doc.exists or "total_items" not in meta_doc.to_dict():
            raise HTTPException(
                status_code=500, detail="Metadata jumlah penyakit tidak tersedia."
            )

        total_items = meta_doc.to_dict()["total_items"]
        max_page = (total_items + limit - 1) // limit

        return DiseasesPaginatedResponse(
            diseases=diseases, total_items=total_items, max_page=max_page
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat mengambil data penyakit: {str(e)}",
        )


@router.get(
    "/{disease_id}",
    response_model=Diseases,
    dependencies=[Depends(verify_firebase_token)],
)
def get_disease_by_id(disease_id: str):
    try:
        disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(disease_id)
        disease_doc = disease_ref.get()

        if not disease_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Penyakit dengan nama {disease_id} tidak ditemukan",
            )

        return Diseases(**disease_doc.to_dict())

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat mengambil data penyakit: {str(e)}",
        )


@router.patch(
    "/{disease_id}",
    response_model=SuccessResponse,
    dependencies=[Depends(verify_is_admin)],
)
def update_disease(disease_id: str, updated_disease: Diseases):
    try:
        disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(disease_id)
        disease_doc = disease_ref.get()

        if not disease_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"penyakit dengan nama {disease_id} tidak ditemukan",
            )

        disease_ref.update(updated_disease.model_dump(exclude_unset=True))

        return {"message": "Penyakit berhasil diperbarui"}

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat memperbarui data penyakit: {str(e)}",
        )


@router.delete(
    "/{disease_id}",
    response_model=SuccessResponse,
    dependencies=[Depends(verify_is_admin)],
)
def delete_disease(disease_id: str):
    try:
        disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(disease_id)
        disease_doc = disease_ref.get()

        if not disease_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Penyakit dengan nama {disease_id} tidak ditemukan",
            )

        disease_ref.delete()

        meta_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(
            FIRESTORE_DOCUMENT_METADATA
        )
        meta_ref.update({"total_items": Increment(-1)})

        return SuccessResponse(message="Penyakit berhasil dihapus")

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat menghapus data penyakit: {str(e)}",
        )
