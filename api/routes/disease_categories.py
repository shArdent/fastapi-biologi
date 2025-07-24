from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

from constants.cache_time import CACHE_TIME
from constants.collection_name import FIRESTORE_COLLECTION_DISEASE_CATEGORIES
from schemas.default_success import SuccessResponse
from schemas.disease_categories import (
    DiseaseCategoryCreate,
    DiseaseCategoryResponse,
    DiseaseCategoryUpdate,
)
from utils.middlewares.verify_is_admin import verify_is_admin
from utils.middlewares.verify_token import verify_firebase_token
from utils.slugify import slugify
from db.firestore import db


router = APIRouter(prefix="/disease-categories", tags=["Disease Categories"])


@router.post(
    "/",
    response_model=SuccessResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_is_admin)],
)
async def add_disease_category(category_data: DiseaseCategoryCreate):
    try:
        category_id = slugify(category_data.name)
        category_ref = db.collection(FIRESTORE_COLLECTION_DISEASE_CATEGORIES).document(
            category_id
        )

        if (await category_ref.get()).exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Kategori dengan nama '{category_data.name}' sudah ada.",
            )

        await category_ref.set(category_data.model_dump())
        await FastAPICache.clear()
        return SuccessResponse(message="Kategori penyakit berhasil ditambahkan.")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/",
    response_model=List[DiseaseCategoryResponse],
    dependencies=[Depends(verify_firebase_token)],
)
@cache(CACHE_TIME)
async def get_all_disease_categories():
    try:
        docs = db.collection(FIRESTORE_COLLECTION_DISEASE_CATEGORIES).stream()
        categories = []
        async for doc in docs:
            category_data = doc.to_dict()
            if not category_data:
                continue
            category_data["id"] = doc.id
            categories.append(DiseaseCategoryResponse(**category_data))
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{category_id}",
    response_model=DiseaseCategoryResponse,
    dependencies=[Depends(verify_firebase_token)],
)
@cache(CACHE_TIME)
async def get_disease_category_by_id(category_id: str):
    try:
        doc = await (
            db.collection(FIRESTORE_COLLECTION_DISEASE_CATEGORIES)
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
        return DiseaseCategoryResponse(**category_data)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/{category_id}",
    response_model=SuccessResponse,
    dependencies=[Depends(verify_is_admin)],
)
async def update_disease_category(
    category_id: str, category_update: DiseaseCategoryUpdate
):
    try:
        category_ref = db.collection(FIRESTORE_COLLECTION_DISEASE_CATEGORIES).document(
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

        return SuccessResponse(message="Kategori penyakit berhasil diperbarui.")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{category_id}",
    response_model=SuccessResponse,
    dependencies=[Depends(verify_is_admin)],
)
async def delete_disease_category(category_id: str):
    try:
        category_ref = db.collection(FIRESTORE_COLLECTION_DISEASE_CATEGORIES).document(
            category_id
        )
        if not (await category_ref.get()).exists:
            raise HTTPException(status_code=404, detail="Kategori tidak ditemukan.")

        await category_ref.delete()
        await FastAPICache.clear()
        return SuccessResponse(message="Kategori penyakit berhasil dihapus.")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
