import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from google.cloud.firestore_v1 import (
    Increment,
    FieldFilter,
)
from typing import Optional
from fastapi_cache.decorator import cache

from db.firestore import db
from constants.collection_name import (
    FIRESTORE_COLLECTION_PLANT_CATEGORIES,
    FIRESTORE_COLLECTION_PLANTS,
    FIRESTORE_DOCUMENT_METADATA,
)
from schemas.plants import (
    PlantsCursorResponse,
    PlantResponse,
    PlantCreate,
    PlantUpdate,
)
from schemas.default_success import SuccessResponse
from utils.middlewares.verify_is_admin import verify_is_admin
from utils.middlewares.verify_token import verify_firebase_token
from utils.slugify import slugify

router = APIRouter(prefix="/plants", tags=["plants"])


@router.post(
    "/",
    response_model=SuccessResponse,
    status_code=201,
    dependencies=[Depends(verify_is_admin)],
)
async def add_new_plant(new_plant: PlantCreate):
    try:
        plant_id = slugify(new_plant.name)
        plant_ref = db.collection(FIRESTORE_COLLECTION_PLANTS).document(plant_id)
        category_ref = db.collection(FIRESTORE_COLLECTION_PLANT_CATEGORIES).document(
            new_plant.category_id
        )

        if (await plant_ref.get()).exists:
            raise HTTPException(
                status_code=400,
                detail=f"Tanaman dengan nama '{new_plant.name}' sudah ada.",
            )

        category_doc = await category_ref.get()
        if not category_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Kategori dengan ID '{new_plant.category_id}' tidak ditemukan.",
            )

        category_data = category_doc.to_dict()

        if not category_data:
            raise HTTPException(
                status_code=500,
                detail=f"Data untuk kategori '{new_plant.category_id}' kosong atau korup.",
            )

        category_name = category_data.get("name")

        data_to_save = new_plant.model_dump()
        data_to_save.pop("category_id")
        data_to_save["category_ref"] = category_ref
        data_to_save["category_name"] = category_name

        tasks = [
            plant_ref.set(data_to_save),
            db.collection(FIRESTORE_COLLECTION_PLANTS)
            .document(FIRESTORE_DOCUMENT_METADATA)
            .set({"total_items": Increment(1)}, merge=True),
            category_ref.set({"plant_count": Increment(1)}, merge=True),
        ]

        await asyncio.gather(*tasks)

        return SuccessResponse(message="Tanaman berhasil ditambahkan")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Gagal menambah data tanaman: {str(e)}"
        )


@router.get(
    "/",
    response_model=PlantsCursorResponse,
    dependencies=[Depends(verify_firebase_token)],
)
@cache(expire=300)
async def get_all_plants(
    limit: int = Query(10, ge=1, le=100),
    start_after_doc_id: Optional[str] = Query(
        None, description="ID dokumen terakhir dari halaman sebelumnya"
    ),
    category_id: Optional[str] = Query(
        None, description="Filter tanaman berdasarkan ID Kategori"
    ),
):
    try:
        plants_ref = db.collection(FIRESTORE_COLLECTION_PLANTS)
        base_query = plants_ref

        if category_id:
            category_ref = db.collection(
                FIRESTORE_COLLECTION_PLANT_CATEGORIES
            ).document(category_id)
            base_query = base_query.where(
                filter=FieldFilter("category_ref", "==", category_ref)
            )

        query_for_page = base_query.order_by("__name__")

        if start_after_doc_id:
            start_doc_ref = db.collection(FIRESTORE_COLLECTION_PLANTS).document(
                start_after_doc_id
            )
            start_doc = await start_doc_ref.get()
            if start_doc.exists:
                query_for_page = query_for_page.start_after(start_doc)

        docs_stream = query_for_page.limit(limit).stream()
        plants_docs = []
        async for doc in docs_stream:
            if doc.id != FIRESTORE_DOCUMENT_METADATA:
                plants_docs.append(doc)

        if not plants_docs:
            return PlantsCursorResponse(plants=[], next_cursor=None)

        plants = []
        for doc in plants_docs:
            plant_data = doc.to_dict()
            if not plant_data:
                continue

            response_data = {**plant_data, "id": doc.id}
            plants.append(PlantResponse(**response_data))

        next_cursor = plants_docs[-1].id if len(plants_docs) == limit else None

        return PlantsCursorResponse(plants=plants, next_cursor=next_cursor)

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat mengambil data tanaman: {str(e)}",
        )


@router.get(
    "/{plant_id}",
    response_model=PlantResponse,
    dependencies=[Depends(verify_firebase_token)],
)
@cache(expire=300)
async def get_plant_by_id(plant_id: str):
    try:
        plant_ref = db.collection(FIRESTORE_COLLECTION_PLANTS).document(plant_id)
        plant_doc = await plant_ref.get()
        if not plant_doc.exists:
            raise HTTPException(status_code=404, detail="Tanaman tidak ditemukan.")

        plant_data = plant_doc.to_dict()
        if not plant_data:
            raise HTTPException(status_code=404, detail="Data tanaman kosong.")

        response_data = {
            **plant_data,
            "id": plant_doc.id,
        }
        return PlantResponse(**response_data)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/{plant_id}",
    response_model=SuccessResponse,
    dependencies=[Depends(verify_is_admin)],
)
async def update_plant(plant_id: str, updated_plant: PlantUpdate):
    try:
        plant_ref = db.collection(FIRESTORE_COLLECTION_PLANTS).document(plant_id)
        if not (await plant_ref.get()).exists:
            raise HTTPException(status_code=404, detail="Tanaman tidak ditemukan.")

        update_data = updated_plant.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=400, detail="Tidak ada data untuk diperbarui."
            )

        if "category_id" in update_data:
            category_id = update_data.pop("category_id")
            category_ref = db.collection(
                FIRESTORE_COLLECTION_PLANT_CATEGORIES
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
                    detail=f"Data untuk kategori '{category_id}' kosong atau korup.",
                )

            update_data["category_ref"] = category_ref
            update_data["category_name"] = category_data.get("name")

        await plant_ref.update(update_data)
        return SuccessResponse(message="Tanaman berhasil diperbarui")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{plant_id}",
    response_model=SuccessResponse,
    dependencies=[Depends(verify_is_admin)],
)
async def delete_plant(plant_id: str):
    try:
        plant_ref = db.collection(FIRESTORE_COLLECTION_PLANTS).document(plant_id)
        plant_doc = await plant_ref.get()

        if not plant_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Tanaman dengan nama {plant_id} tidak ditemukan",
            )

        plant_data = plant_doc.to_dict()
        category_ref = plant_data.get("category_ref") if plant_data else None

        tasks = [
            plant_ref.delete(),
            db.collection(FIRESTORE_COLLECTION_PLANTS)
            .document(FIRESTORE_DOCUMENT_METADATA)
            .update({"total_items": Increment(-1)}),
        ]

        if category_ref:
            tasks.append(category_ref.update({"plant_count": Increment(-1)}))

        await asyncio.gather(*tasks)

        return SuccessResponse(message="Tanaman berhasil dihapus")

    except HTTPException as he:
        raise he

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat menghapus data tanaman: {str(e)}",
        )
