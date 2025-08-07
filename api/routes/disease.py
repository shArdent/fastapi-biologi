from fastapi import APIRouter, Depends, HTTPException, Query
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
    DiseaseUpdate,
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
        disease_id = f"{new_disease.plants_listed[0].lower()}_{slugify(new_disease.name)}"
        disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(disease_id)

        if (await disease_ref.get()).exists:
            raise HTTPException(
                status_code=400,
                detail=f"Penyakit dengan nama '{new_disease.name}' sudah ada.",
            )

        categories_list = []
        categories_ref = []
        if new_disease.categories_id:
            cat_refs = [
                db.collection(FIRESTORE_COLLECTION_DISEASE_CATEGORIES).document(cat_id)
                for cat_id in new_disease.categories_id
            ]
            cat_docs = [doc async for doc in db.get_all(cat_refs)]
            for doc in cat_docs:
                if doc.exists:
                    cat_data = doc.to_dict()
                    categories_list.append(cat_data.get("name"))
                    categories_ref = cat_refs
                else:
                    raise HTTPException(
                        status_code=404,
                        detail="Satu atau lebih ID kategori tidak ditemukan.",
                    )

        batch = db.batch()

        data_to_save = new_disease.model_dump()
        data_to_save.pop("categories_id")
        data_to_save["categories"] = categories_list

        batch.set(disease_ref, data_to_save)

        meta_ref = db.collection(FIRESTORE_DOCUMENT_METADATA).document(
            FIRESTORE_COLLECTION_DISEASES
        )
        batch.set(meta_ref, {"total_items": Increment(1)}, merge=True)

        for cat_ref in categories_ref:
            batch.update(cat_ref, {"disease_count": Increment(1)})

        await batch.commit()

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
async def get_all_diseases(
    limit: int = Query(10, ge=1, le=100),
    start_after_doc_id: Optional[str] = Query(None),
    category_name: Optional[str] = Query(None),
    plant_name: Optional[str] = Query(None, description="Nama tanaman"),
):
    try:
        base_query = db.collection(FIRESTORE_COLLECTION_DISEASES)

        meta_doc = (
            await db.collection(FIRESTORE_DOCUMENT_METADATA)
            .document(FIRESTORE_COLLECTION_DISEASES)
            .get()
        )

        meta_data = meta_doc.to_dict()
        total_diseases = meta_data.get("total_items") if meta_data else 0

        if category_name and not plant_name:
            cat_doc = (
                await db.collection(FIRESTORE_COLLECTION_DISEASE_CATEGORIES)
                .document(slugify(category_name))
                .get()
            )
            cat_data = cat_doc.to_dict()
            total_diseases = cat_data.get("disease_count") if cat_data else 0
            base_query = base_query.where(
                filter=FieldFilter("categories", "array_contains", category_name)
            )

        if plant_name and not category_name:
            base_query = base_query.where(
                filter=FieldFilter("plants_listed", "array_contains", plant_name)
            )

        query_for_page = base_query.order_by("__name__")
        if start_after_doc_id:
            start_doc = (
                await db.collection(FIRESTORE_COLLECTION_DISEASES)
                .document(start_after_doc_id)
                .get()
            )
            if start_doc.exists:
                query_for_page = query_for_page.start_after(start_doc)

        docs_stream = query_for_page.limit(limit).stream()
        diseases_docs = [
            doc async for doc in docs_stream if doc.id != FIRESTORE_DOCUMENT_METADATA
        ]

        diseases = []

        for doc in diseases_docs:
            disease_data = doc.to_dict()
            if not disease_data:
                continue
            response_data = {
                **disease_data,
                "id": doc.id,
                "categories_name": disease_data.get("categories"),
            }
            diseases.append(DiseaseResponse(**response_data))

        next_cursor = diseases_docs[-1].id if len(diseases_docs) == limit else None

        return DiseasesCursorResponse(diseases=diseases, next_cursor=next_cursor, total_items=total_diseases)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{disease_id}",
    response_model=DiseaseResponse,
    dependencies=[Depends(verify_firebase_token)],
)
async def get_disease_by_id(disease_id: str):
    try:
        disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(disease_id)
        disease_doc = await disease_ref.get()

        if not disease_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Penyakit dengan ID {disease_id} tidak ditemukan",
            )

        disease_data = disease_doc.to_dict()
        if not disease_data:
            raise HTTPException(status_code=404, detail="Data penyakit rusak.")

        cat_names = disease_data.get("categories")

        response_data = {
            **disease_data,
            "id": disease_doc.id,
            "categories_name": cat_names,
        }

        return DiseaseResponse(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/{disease_id}",
    response_model=SuccessResponse,
    dependencies=[Depends(verify_is_admin)],
)
async def update_disease(disease_id: str, updated_disease: DiseaseUpdate):
    try:
        if not updated_disease.model_dump(exclude_unset=True):
            raise HTTPException(
                status_code=400, detail="Tidak ada data untuk diperbarui."
            )

        disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(disease_id)

        snapshot = await disease_ref.get()
        if not snapshot.exists:
            raise HTTPException(status_code=404, detail="Penyakit tidak ditemukan.")

        existing_data = snapshot.to_dict()
        update_data = updated_disease.model_dump(exclude_unset=True)

        if "categories_id" in update_data:
            new_ids = update_data.pop("categories_id")
            old_list = existing_data.get("categories", []) if existing_data else []

            old_refs = [
                db.collection(FIRESTORE_COLLECTION_DISEASE_CATEGORIES).document(
                    slugify(name)
                )
                for name in old_list
            ]
            old_refs = set(old_refs)

            new_refs_list = []
            new_name_list = []
            if new_ids:
                cat_refs = [
                    db.collection(FIRESTORE_COLLECTION_DISEASE_CATEGORIES).document(cid)
                    for cid in new_ids
                ]
                cat_docs = [doc async for doc in db.get_all(cat_refs)]
                for doc in cat_docs:
                    if doc.exists:
                        new_name_list.append(doc.to_dict().get("name"))
                        new_refs_list.append(doc.reference)
                    else:
                        raise HTTPException(
                            status_code=404, detail="ID kategori baru tidak ditemukan."
                        )

            new_refs = set(new_refs_list)
            update_data["categories"] = new_name_list

            for ref in new_refs - old_refs:
                await ref.update({"disease_count": Increment(1)})
            for ref in old_refs - new_refs:
                await ref.update({"disease_count": Increment(-1)})

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
                detail=f"Penyakit dengan ID {disease_id} tidak ditemukan",
            )

        batch = db.batch()
        batch.delete(disease_ref)

        # Decrement metadata
        meta_ref = db.collection(FIRESTORE_DOCUMENT_METADATA).document(
            FIRESTORE_COLLECTION_DISEASES
        )
        batch.update(meta_ref, {"total_items": Increment(-1)})

        # Decrement semua kategori terkait
        disease_data = disease_doc.to_dict()
        categories_list = disease_data.get("categories")
        if categories_list:
            cat_refs = [
                db.collection(FIRESTORE_COLLECTION_DISEASE_CATEGORIES).document(
                    slugify(name)
                )
                for name in categories_list
            ]
            for cat_ref in cat_refs:
                batch.update(cat_ref, {"disease_count": Increment(-1)})

        await batch.commit()
        return SuccessResponse(message="Penyakit berhasil dihapus")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Gagal menghapus data penyakit: {str(e)}"
        )
