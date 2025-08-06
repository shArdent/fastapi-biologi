from fastapi import APIRouter, Depends, HTTPException, Query
from google.cloud.firestore_v1 import (
    Increment,
    FieldFilter,
)
from typing import Optional

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

        if (await plant_ref.get()).exists:
            raise HTTPException(
                status_code=400,
                detail=f"Tanaman dengan nama '{new_plant.name}' sudah ada.",
            )

        category_refs = [
            db.collection(FIRESTORE_COLLECTION_PLANT_CATEGORIES).document(cat_id)
            for cat_id in new_plant.categories_id
        ]

        category_docs = [doc async for doc in db.get_all(category_refs)]

        categories_to_save = []
        validated_category_refs = []

        for doc in category_docs:
            if not doc.exists:
                raise HTTPException(
                    status_code=404, detail="Terdapat ID kategori yang tidak ditemukan"
                )

            category_data = doc.to_dict()
            category_name = (
                category_data.get("name") if category_data is not None else "Tanaman"
            )
            categories_to_save.append(category_name)

            validated_category_refs.append(doc.reference)

        batch = db.batch()

        data_to_save = new_plant.model_dump()
        data_to_save.pop("categories_id")
        data_to_save["categories"] = categories_to_save

        batch.set(plant_ref, data_to_save)

        metadata_ref = db.collection(FIRESTORE_DOCUMENT_METADATA).document(
            FIRESTORE_COLLECTION_PLANTS
        )

        batch.set(metadata_ref, {"total_items": Increment(1)}, merge=True)

        for cat_ref in validated_category_refs:
            batch.update(cat_ref, {"plant_count": Increment(1)})

        await batch.commit()

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
async def get_all_plants(
    limit: int = Query(10, ge=1, le=100),
    start_after_doc_id: Optional[str] = Query(
        None, description="ID dokumen terakhir dari halaman sebelumnya"
    ),
    category_name: Optional[str] = Query(
        None,
        description="Filter tanaman berdasarkan nama Kategori",
        example="Tanaman Pangan",
    ),
):
    try:
        plants_ref = db.collection(FIRESTORE_COLLECTION_PLANTS)
        base_query = plants_ref

        metadata_ref = (
            await db.collection(FIRESTORE_DOCUMENT_METADATA)
            .document(FIRESTORE_COLLECTION_PLANTS)
            .get()
        )

        meta_data = metadata_ref.to_dict()

        total_plants = meta_data.get("total_items") if meta_data else 0

        if category_name:
            category_doc = (
                await db.collection(FIRESTORE_COLLECTION_PLANT_CATEGORIES)
                .document(slugify(category_name))
                .get()
            )
            category_data = category_doc.to_dict()
            total_plants = category_data.get("plant_count") if category_data else 0
            base_query = base_query.where(
                filter=FieldFilter("categories", "array_contains", category_name)
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
            return PlantsCursorResponse(plants=[], next_cursor=None, total_items=0)

        plants = []
        for doc in plants_docs:
            plant_data = doc.to_dict()
            if not plant_data:
                continue

            response_data = {
                **plant_data,
                "id": doc.id,
                "categories_name": plant_data.get("categories"),
            }
            plants.append(PlantResponse(**response_data))

        next_cursor = plants[-1].id if len(plants) == limit else None

        return PlantsCursorResponse(
            plants=plants, next_cursor=next_cursor, total_items=total_plants
        )

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
async def get_plant_by_id(plant_id: str):
    try:
        plant_ref = db.collection(FIRESTORE_COLLECTION_PLANTS).document(plant_id)
        plant_doc = await plant_ref.get()
        if not plant_doc.exists:
            raise HTTPException(status_code=404, detail="Tanaman tidak ditemukan.")

        plant_data = plant_doc.to_dict()
        if not plant_data:
            raise HTTPException(status_code=404, detail="Data tanaman kosong.")

        cat_dict = plant_data.get("categories")
        cat_names = cat_dict

        response_data = {**plant_data, "id": plant_doc.id, "categories_name": cat_names}
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
        if not updated_plant.model_dump(exclude_unset=True):
            raise HTTPException(
                status_code=400, detail="Tidak ada data untuk diperbarui."
            )

        plant_ref = db.collection(FIRESTORE_COLLECTION_PLANTS).document(plant_id)

        snapshot = await plant_ref.get()
        if not snapshot.exists:
            raise HTTPException(status_code=404, detail="Tanaman tidak ditemukan.")

        existing_data = snapshot.to_dict()
        update_data = updated_plant.model_dump(exclude_unset=True)

        if "categories_id" in update_data:
            new_category_ids = update_data.pop("categories_id")

            old_categories_name_list = (
                existing_data.get("categories", []) if existing_data else []
            )
            old_categories_ref_list = [
                db.collection(FIRESTORE_COLLECTION_PLANT_CATEGORIES).document(
                    slugify(name)
                )
                for name in old_categories_name_list
            ]
            old_category_set = set(old_categories_ref_list)

            new_category_refs_list = []
            new_category_name_list = []
            if new_category_ids:
                cat_refs_to_fetch = [
                    db.collection(FIRESTORE_COLLECTION_PLANT_CATEGORIES).document(
                        cat_id
                    )
                    for cat_id in new_category_ids
                ]
                # get_all bisa dijalankan di dalam transaksi
                new_category_docs = [doc async for doc in db.get_all(cat_refs_to_fetch)]

                for doc in new_category_docs:
                    if doc.exists:
                        cat_data = doc.to_dict()
                        if not cat_data:
                            raise HTTPException(
                                status_code=404,
                                detail="Satu atau lebih ID kategori baru tidak ditemukan.",
                            )
                        new_category_refs_list.append(doc.reference)
                        new_category_name_list.append(cat_data.get("name"))
                    else:
                        raise HTTPException(
                            status_code=404,
                            detail="Satu atau lebih ID kategori baru tidak ditemukan.",
                        )

            new_category_refs = set(new_category_refs_list)
            update_data["categories"] = new_category_name_list  # Siapkan untuk update

            refs_to_increment = new_category_refs - old_category_set
            refs_to_decrement = old_category_set - new_category_refs

            for ref in refs_to_increment:
                await ref.update({"plant_count": Increment(1)})

            for ref in refs_to_decrement:
                await ref.update({"plant_count": Increment(-1)})

        await plant_ref.update(update_data)
        return SuccessResponse(message="Tanaman berhasil diperbarui")

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Gagal memperbarui tanaman: {str(e)}"
        )


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
        batch = db.batch()

        batch.delete(plant_ref)

        metadata_ref = db.collection(FIRESTORE_DOCUMENT_METADATA).document(
            FIRESTORE_COLLECTION_PLANTS
        )
        batch.update(metadata_ref, {"total_items": Increment(-1)})

        plant_data = plant_doc.to_dict()
        categories_list = plant_data.get("categories") if plant_data else None
        if categories_list:
            category_refs = [
                db.collection(FIRESTORE_COLLECTION_PLANT_CATEGORIES).document(
                    slugify(name)
                )
                for name in categories_list
            ]
            for category_ref in category_refs:
                batch.update(category_ref, {"plant_count": Increment(-1)})

        await batch.commit()

        return SuccessResponse(message="Tanaman berhasil dihapus")

    except HTTPException as he:
        raise he

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat menghapus data tanaman: {str(e)}",
        )
