from fastapi import APIRouter, Depends, HTTPException, Query
from google.cloud.firestore_v1 import (
    DocumentReference,
    FieldFilter,
    Increment,
    field_path,
)
from typing import Optional

from db.firestore import db
from constants.collection_name import (
    FIRESTORE_COLLECTION_DISEASE_CATEGORIES,
    FIRESTORE_COLLECTION_DISEASES,
    FIRESTORE_DOCUMENT_METADATA,
)
from schemas.diseases import DiseaseCreate, DiseaseResponse, DiseasesPaginatedResponse
from schemas.default_success import SuccessResponse
from utils.get_category_data import get_category_data
from utils.middlewares.verify_is_admin import verify_is_admin
from utils.middlewares.verify_token import verify_firebase_token
from utils.slugify import slugify

router = APIRouter(prefix="/diseases", tags=["diseases"])


@router.post(
    "/",
    response_model=SuccessResponse,
    status_code=201,
    dependencies=[Depends(verify_is_admin)],
)
def add_new_disease(new_disease: DiseaseCreate):
    try:
        disease_id = slugify(new_disease.name)
        disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(disease_id)
        category_ref = db.collection(FIRESTORE_COLLECTION_DISEASE_CATEGORIES).document(
            new_disease.category_id
        )

        if disease_ref.get().exists:
            raise HTTPException(
                status_code=400,
                detail=f"Penyakit dengan nama '{new_disease.name}' sudah ada.",
            )

        category_ref = db.collection(FIRESTORE_COLLECTION_DISEASE_CATEGORIES).document(
            new_disease.category_id
        )
        category_doc = category_ref.get()
        if not category_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Kategori dengan ID '{new_disease.category_id}' tidak ditemukan.",
            )
        category_data = category_doc.to_dict()

        if not category_data:
            raise HTTPException(
                status_code=500,
                detail=f"Data untuk kategori '{new_disease.category_id}' kosong atau korup.",
            )

        category_name = category_data.get("name")

        data_to_save = new_disease.model_dump()
        data_to_save.pop("category_id")
        data_to_save["category_ref"] = category_ref
        data_to_save["category_name"] = category_name

        disease_ref.set(data_to_save)

        meta_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(
            FIRESTORE_DOCUMENT_METADATA
        )
        meta_ref.set({"total_items": Increment(1)}, merge=True)
        category_ref.set({"disease_count": Increment(1)}, merge=True)

        return SuccessResponse(message="Penyakit berhasil ditambahkan")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Gagal menambah data penyakit: {str(e)}"
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
    category_id: Optional[str] = Query(
        None, description="Filter penyakit berdasarkan ID Kategori"
    ),
):
    try:
        diseases_ref = db.collection(FIRESTORE_COLLECTION_DISEASES)
        base_query = diseases_ref
        total_items = 0

        if category_id:
            category_ref = db.collection(
                FIRESTORE_COLLECTION_DISEASE_CATEGORIES
            ).document(category_id)
            category_doc = category_ref.get()
            category_data = category_doc.to_dict()
            if (
                category_doc.exists
                and category_data
                and "disease_count" in category_data
            ):
                total_items = category_data["disease_count"]
            else:
                raise HTTPException(
                    status_code=500, detail="Metadata jumlah penyakit tidak tersedia."
                )
            base_query = base_query.where(
                filter=FieldFilter("category_ref", "==", category_ref)
            )
        else:
            meta_doc = diseases_ref.document(FIRESTORE_DOCUMENT_METADATA).get()
            meta_data = meta_doc.to_dict()
            if meta_doc.exists and meta_data and "total_items" in meta_data:
                total_items = meta_data["total_items"]
            else:
                raise HTTPException(
                    status_code=500, detail="Metadata jumlah penyakit tidak tersedia."
                )

        query_for_page = base_query.order_by(field_path.FieldPath.document_id())

        if start_after_doc_id:
            start_doc_ref = diseases_ref.document(start_after_doc_id).get()
            if not start_doc_ref.exists:
                raise HTTPException(
                    status_code=404, detail="Dokumen awal tidak ditemukan."
                )
            query_for_page = query_for_page.start_after(start_doc_ref)

        docs = query_for_page.limit(limit).stream()
        diseases = []
        for doc in docs:
            if doc.id == FIRESTORE_DOCUMENT_METADATA:
                continue

            disease_data = doc.to_dict()
            if not disease_data:
                continue

            category_ref = disease_data.get("category_ref")
            category_data = (
                get_category_data(category_ref)
                if isinstance(category_ref, DocumentReference)
                else {"id": None, "name": "None", "description": "None"}
            )

            response_data = {**disease_data, "id": doc.id, "category": category_data}
            diseases.append(DiseaseResponse(**response_data))

        max_page = (total_items + limit - 1) // limit if limit > 0 else 0

        return DiseasesPaginatedResponse(
            diseases=diseases, total_items=total_items, max_page=max_page
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{disease_id}",
    response_model=DiseaseResponse,
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

        disease_data = disease_doc.to_dict()
        if not disease_data or not isinstance(disease_data, dict):
            raise HTTPException(
                status_code=500,
                detail="Data penyakit tidak valid atau tidak ditemukan.",
            )
        category_ref = disease_data.get("category_ref")
        response_data = {
            **disease_data,
            "id": disease_doc.id,
            "category": {
                "id": category_ref.id if category_ref else "unknown",
                "name": disease_data.get("category_name", "Tidak ada kategori"),
                "description": None,
            },
        }
        return DiseaseResponse(**response_data)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/{disease_id}",
    response_model=SuccessResponse,
    dependencies=[Depends(verify_is_admin)],
)
def update_disease(disease_id: str, updated_disease: DiseaseResponse):
    try:
        disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(disease_id)
        if not disease_ref.get().exists:
            raise HTTPException(status_code=404, detail="Penyakit tidak ditemukan.")

        update_data = updated_disease.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=400, detail="Tidak ada data untuk diperbarui."
            )

        if "category_id" in update_data:
            category_id = update_data.pop("category_id")
            category_ref = db.collection(
                FIRESTORE_COLLECTION_DISEASE_CATEGORIES
            ).document(category_id)
            category_doc = category_ref.get()
            if not category_doc.exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"Kategori dengan ID '{category_id}' tidak ditemukan.",
                )

            category_data = category_doc.to_dict()

            if not category_data:
                raise HTTPException(
                    status_code=500,
                    detail=f"Ketegori dengan ID '{category_id}' tidak ada atau corrupt",
                )

            update_data["category_ref"] = category_ref
            update_data["category_name"] = category_data.get("name")

        disease_ref.update(update_data)
        return SuccessResponse(message="Penyakit berhasil diperbarui")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

        disease_data = disease_doc.to_dict()

        category_ref = disease_doc.get("category_ref") if disease_data else None

        disease_ref.delete()
        meta_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(
            FIRESTORE_DOCUMENT_METADATA
        )
        meta_ref.update({"total_items": Increment(-1)})
        if category_ref:
            category_ref.update({"disease_count": Increment(-1)})

        return SuccessResponse(message="Penyakit berhasil dihapus")

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat menghapus data penyakit: {str(e)}",
        )
