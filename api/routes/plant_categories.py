from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

from constants.cache_time import CACHE_TIME
from constants.collection_name import FIRESTORE_COLLECTION_PLANT_CATEGORIES
from schemas.default_success import SuccessResponse
from schemas.plant_categories import (
    PlantCategoryCreate,
    PlantCategoryResponse,
    PlantCategoryUpdate,
)
from utils.middlewares.verify_is_admin import verify_is_admin
from db.firestore import db
from utils.middlewares.verify_token import verify_firebase_token
from utils.slugify import slugify


router = APIRouter(prefix="/plant-categories", tags=["Plant Categories"])


@router.post(
    "/",
    response_model=SuccessResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_is_admin)],
)
async def add_plant_category(category_data: PlantCategoryCreate):
    try:
        category_id = slugify(category_data.name)
        category_ref = db.collection(FIRESTORE_COLLECTION_PLANT_CATEGORIES).document(
            category_id
        )

        if (await category_ref.get()).exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Kategori dengan nama '{category_data.name}' sudah ada.",
            )

        await category_ref.set(category_data.model_dump())
        await FastAPICache.clear()
        return SuccessResponse(message="Kategori tanaman berhasil ditambahkan.")

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/",
    response_model=List[PlantCategoryResponse],
    dependencies=[Depends(verify_firebase_token)],
)
@cache(CACHE_TIME)
async def get_all_plant_categories():
    try:
        docs = db.collection(FIRESTORE_COLLECTION_PLANT_CATEGORIES).stream()
        categories = []
        async for doc in docs:
            category_data = doc.to_dict()
            if not category_data:
                continue

            category_data["id"] = doc.id
            categories.append(PlantCategoryResponse(**category_data))
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{category_id}",
    response_model=PlantCategoryResponse,
    dependencies=[Depends(verify_firebase_token)],
)
@cache(CACHE_TIME)
async def get_plant_category_by_id(category_id: str):
    try:
        doc = await (
            db.collection(FIRESTORE_COLLECTION_PLANT_CATEGORIES)
            .document(category_id)
            .get()
        )
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Kategori tidak ditemukan.")

        category_data = doc.to_dict()

        if not category_data:
            raise HTTPException(
                status_code=500,
                detail=f"Data untuk kategori '{category_id}' kosong atau korup.",
            )

        category_data["id"] = doc.id
        return PlantCategoryResponse(**category_data)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/{category_id}",
    response_model=SuccessResponse,
    dependencies=[Depends(verify_is_admin)],
)
async def update_plant_category(category_id: str, category_update: PlantCategoryUpdate):
    try:
        category_ref = db.collection(FIRESTORE_COLLECTION_PLANT_CATEGORIES).document(
            category_id
        )
        if not (await category_ref.get()).exists:
            raise HTTPException(status_code=404, detail="Kategori tidak ditemukan.")

        update_data = category_update.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=400, detail="Tidak ada data untuk diperbarui."
            )

        await category_ref.update(update_data)
        await FastAPICache.clear()

        return SuccessResponse(message="Kategori tanaman berhasil diperbarui.")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{category_id}",
    response_model=SuccessResponse,
    dependencies=[Depends(verify_is_admin)],
)
async def delete_plant_category(category_id: str):
    try:
        category_ref = db.collection(FIRESTORE_COLLECTION_PLANT_CATEGORIES).document(
            category_id
        )
        if not (await category_ref.get()).exists:
            raise HTTPException(status_code=404, detail="Kategori tidak ditemukan.")

        await category_ref.delete()
        await FastAPICache.clear()
        return SuccessResponse(message="Kategori tanaman berhasil dihapus.")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
