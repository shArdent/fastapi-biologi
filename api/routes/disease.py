import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_cache.decorator import cache
from google.cloud.firestore_v1 import (
    FieldFilter,
    Increment,
)
from typing import Optional

from db.firestore import db
from constants.collection_name import (
    FIRESTORE_COLLECTION_DISEASE_CATEGORIES,
    FIRESTORE_COLLECTION_DISEASES,
    FIRESTORE_DOCUMENT_METADATA,
)
from schemas.diseases import (
    DiseaseCreate,
    DiseaseResponse,
    DiseasesCursorResponse,
)
from schemas.default_success import SuccessResponse
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
async def add_new_disease(new_disease: DiseaseCreate):
    try:
        disease_id = slugify(new_disease.name)
        disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(disease_id)
        category_ref = db.collection(FIRESTORE_COLLECTION_DISEASE_CATEGORIES).document(
            new_disease.category_id
        )

        if (await disease_ref.get()).exists:
            raise HTTPException(
                status_code=400,
                detail=f"Penyakit dengan nama '{new_disease.name}' sudah ada.",
            )

        category_ref = db.collection(FIRESTORE_COLLECTION_DISEASE_CATEGORIES).document(
            new_disease.category_id
        )
        category_doc = await category_ref.get()
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

        meta_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(
            FIRESTORE_DOCUMENT_METADATA
        )

        tasks = [
            disease_ref.set(data_to_save),
            meta_ref.set({"total_items": Increment(1)}, merge=True),
            category_ref.set({"disease_count": Increment(1)}, merge=True),
        ]

        await asyncio.gather(*tasks)

        return SuccessResponse(message="Penyakit berhasil ditambahkan")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Gagal menambah data penyakit: {str(e)}"
        )


@router.get(
    "/",
    response_model=DiseasesCursorResponse,
    dependencies=[Depends(verify_firebase_token)],
)
@cache(expire=300)
async def get_all_diseases(
    limit: int = Query(10, ge=1, le=100),
    start_after_doc_id: Optional[str] = Query(
        None, description="ID dokumen terakhir dari halaman sebelumnya"
    ),
    category_id: Optional[str] = Query(
        None, description="Filter penyakit berdasarkan ID Kategori"
    ),
):
    try:
        base_query = db.collection(FIRESTORE_COLLECTION_DISEASES)

        if category_id:
            category_ref = db.collection(
                FIRESTORE_COLLECTION_DISEASE_CATEGORIES
            ).document(category_id)
            base_query = base_query.where(
                filter=FieldFilter("category_ref", "==", category_ref)
            )

        query_for_page = base_query.order_by("__name__")

        if start_after_doc_id:
            start_doc_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(
                start_after_doc_id
            )
            start_doc = await start_doc_ref.get()
            if start_doc.exists:
                query_for_page = query_for_page.start_after(start_doc)

        docs_stream = query_for_page.limit(limit).stream()
        diseases_docs = [
            doc async for doc in docs_stream if doc.id != FIRESTORE_DOCUMENT_METADATA
        ]

        if not diseases_docs:
            return DiseasesCursorResponse(diseases=[], next_cursor=None)

        diseases = []
        for doc in diseases_docs:
            disease_data = doc.to_dict()
            if not disease_data:
                continue

            response_data = {**disease_data, "id": doc.id}
            diseases.append(DiseaseResponse(**response_data))

        next_cursor = diseases_docs[-1].id if len(diseases_docs) == limit else None

        return DiseasesCursorResponse(diseases=diseases, next_cursor=next_cursor)

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat mengambil data penyakit: {str(e)}",
        )


@router.get(
    "/{disease_id}",
    response_model=DiseaseResponse,
    dependencies=[Depends(verify_firebase_token)],
)
@cache(expire=300)
async def get_disease_by_id(disease_id: str):
    try:
        disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(disease_id)
        disease_doc = await disease_ref.get()

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
        response_data = {
            **disease_data,
            "id": disease_doc.id,
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
async def update_disease(disease_id: str, updated_disease: DiseaseResponse):
    try:
        disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(disease_id)
        if not (await disease_ref.get()).exists:
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
            category_doc = await category_ref.get()
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

        await disease_ref.update(update_data)
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
async def delete_disease(disease_id: str):
    try:
        disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(disease_id)
        disease_doc = await disease_ref.get()

        if not disease_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Penyakit dengan nama {disease_id} tidak ditemukan",
            )

        disease_data = disease_doc.to_dict()

        category_ref = disease_doc.get("category_ref") if disease_data else None

        await disease_ref.delete()
        meta_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(
            FIRESTORE_DOCUMENT_METADATA
        )
        await meta_ref.update({"total_items": Increment(-1)})
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
