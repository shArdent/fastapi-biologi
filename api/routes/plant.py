from fastapi import APIRouter, Depends, HTTPException, Query
from google.cloud.firestore_v1 import (
    DocumentReference,
    Increment,
    field_path,
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
    PlantsPaginatedResponse,
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
def add_new_plant(new_plant: PlantCreate):
    try:
        plant_id = slugify(new_plant.name)
        plant_ref = db.collection(FIRESTORE_COLLECTION_PLANTS).document(plant_id)
        category_ref = db.collection(FIRESTORE_COLLECTION_PLANT_CATEGORIES).document(
            new_plant.category_id
        )

        if plant_ref.get().exists:
            raise HTTPException(
                status_code=400,
                detail=f"Tanaman dengan nama '{new_plant.name}' sudah ada.",
            )

        category_doc = category_ref.get()
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

        plant_ref.set(data_to_save)

        meta_ref = db.collection(FIRESTORE_COLLECTION_PLANTS).document(
            FIRESTORE_DOCUMENT_METADATA
        )
        meta_ref.set({"total_items": Increment(1)}, merge=True)
        category_ref.set({"plant_count": Increment(1)}, merge=True)

        return SuccessResponse(message="Tanaman berhasil ditambahkan")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Gagal menambah data tanaman: {str(e)}"
        )


@router.get(
    "/",
    response_model=PlantsPaginatedResponse,
    dependencies=[Depends(verify_firebase_token)],
)
def get_all_plants(
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
        total_items = 0

        category_response = {}

        if category_id:
            category_ref = db.collection(
                FIRESTORE_COLLECTION_PLANT_CATEGORIES
            ).document(category_id)
            category_doc = category_ref.get()
            category_data = category_doc.to_dict()

            if category_doc.exists and category_data and "plant_count" in category_data:
                total_items = category_data["plant_count"]

            else:
                raise HTTPException(
                    status_code=500, detail="Metadata jumlah tanaman tidak tersedia."
                )
            base_query = base_query.where(
                filter=FieldFilter("category_ref", "==", category_ref)
            )
        else:
            meta_doc = plants_ref.document(FIRESTORE_DOCUMENT_METADATA).get()
            meta_data = meta_doc.to_dict()
            if meta_doc.exists and meta_data and "total_items" in meta_data:
                total_items = meta_data["total_items"]
            else:
                raise HTTPException(
                    status_code=500, detail="Metadata jumlah tanaman tidak tersedia."
                )

        query_for_page = base_query.order_by(field_path.FieldPath.document_id())

        if start_after_doc_id:
            start_doc_ref = plants_ref.document(start_after_doc_id).get()
            if not start_doc_ref.exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"Dokumen dengan ID '{start_after_doc_id}' tidak ditemukan.",
                )
            query_for_page = query_for_page.start_after(start_doc_ref)

        docs = query_for_page.limit(limit).stream()

        plants = []
        for doc in docs:
            if doc.id == FIRESTORE_DOCUMENT_METADATA:
                continue
            plant_data = doc.to_dict()

            if not plant_data:
                continue

            category_ref = plant_data.get("category_ref")

            if isinstance(category_ref, DocumentReference):
                cat_doc = category_ref.get()
                cat_data = cat_doc.to_dict()
                category_response["id"] = cat_doc.id
                category_response["name"] = (
                    cat_data.get("name") if cat_data is not None else "None"
                )
                category_response["description"] = (
                    cat_data.get("description") if cat_data is not None else "None"
                )

            response_data = {**plant_data, "id": doc.id, "category": category_response}

            plants.append(PlantResponse(**response_data))

        max_page = (total_items + limit - 1) // limit if limit > 0 else 0

        return PlantsPaginatedResponse(
            plants=plants, total_items=total_items, max_page=max_page
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
def get_plant_by_id(plant_id: str):
    try:
        plant_doc = db.collection(FIRESTORE_COLLECTION_PLANTS).document(plant_id).get()
        if not plant_doc.exists:
            raise HTTPException(status_code=404, detail="Tanaman tidak ditemukan.")

        plant_data = plant_doc.to_dict()
        if not plant_data:
            raise HTTPException(status_code=404, detail="Data tanaman kosong.")

        category_ref = plant_data.get("category_ref")
        response_data = {
            **plant_data,
            "id": plant_doc.id,
            "category": {
                "id": category_ref.id if category_ref else "unknown",
                "name": plant_data.get("category_name", "Tidak ada kategori"),
                "description": None,
            },
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
def update_plant(plant_id: str, updated_plant: PlantUpdate):
    try:
        plant_ref = db.collection(FIRESTORE_COLLECTION_PLANTS).document(plant_id)
        if not plant_ref.get().exists:
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
                    detail=f"Data untuk kategori '{category_id}' kosong atau korup.",
                )

            update_data["category_ref"] = category_ref
            update_data["category_name"] = category_data.get("name")

        plant_ref.update(update_data)
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
def delete_plant(plant_id: str):
    try:
        plant_ref = db.collection(FIRESTORE_COLLECTION_PLANTS).document(plant_id)
        plant_doc = plant_ref.get()

        if not plant_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Tanaman dengan nama {plant_id} tidak ditemukan",
            )

        plant_data = plant_doc.to_dict()
        category_ref = plant_data.get("category_ref") if plant_data else None

        plant_ref.delete()
        meta_ref = db.collection(FIRESTORE_COLLECTION_PLANTS).document(
            FIRESTORE_DOCUMENT_METADATA
        )
        meta_ref.update({"total_items": Increment(-1)})

        if category_ref:
            category_ref.update({"plant_count": Increment(-1)})

        return SuccessResponse(message="Tanaman berhasil dihapus")

    except HTTPException as he:
        raise he

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat menghapus data tanaman: {str(e)}",
        )
