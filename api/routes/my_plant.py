from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi_cache.decorator import cache
from google.cloud.firestore_v1 import (
    SERVER_TIMESTAMP,
    Increment,
    Query as FirestoreQuery,
)

from constants.collection_name import (
    FIRESTORE_COLLECTION_DISEASES,
    FIRESTORE_COLLECTION_MY_PLANTS,
    FIRESTORE_COLLECTION_PLANTS,
    FIRESTORE_COLLECTION_USERS,
    FIRESTORE_DOCUMENT_METADATA,
)
from schemas.default_success import SuccessResponse
from schemas.my_plants import (
    MyPlantCreate,
    MyPlantSummary,
    MyPlantUpdate,
    PaginatedMyPlantSummary,
    SuccessCreatePlant,
    SuccessUpdatePlant,
)
from utils.middlewares.verify_user_id_match import verify_user_id_match
from db.firestore import db


router = APIRouter(prefix="/my-plants", tags=["my plants"])


@router.post(
    "/{user_id}",
    response_model=SuccessCreatePlant,
    status_code=status.HTTP_201_CREATED,
)
async def add_my_plant(
    user_id: str, plant_data: MyPlantCreate, _: dict = Depends(verify_user_id_match)
):
    try:
        my_plants_collection = (
            db.collection(FIRESTORE_COLLECTION_USERS)
            .document(user_id)
            .collection(FIRESTORE_COLLECTION_MY_PLANTS)
        )
        plant_ref = db.collection(FIRESTORE_COLLECTION_PLANTS).document(
            plant_data.plant_id
        )

        if not (await plant_ref.get()).exists:
            raise HTTPException(
                status_code=404,
                detail=f"Tanaman dengan ID '{plant_data.plant_id}' tidak ditemukan.",
            )

        data_to_save = {
            "nickname": plant_data.nickname,
            "nickname_lowercase": plant_data.nickname.lower(),
            "plant_ref": plant_ref,
            "added_at": SERVER_TIMESTAMP,
        }

        if plant_data.disease_id:
            disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(
                plant_data.disease_id
            )
            if not (await disease_ref.get()).exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"Penyakit dengan ID '{plant_data.disease_id}' tidak ditemukan.",
                )
            data_to_save["disease_ref"] = disease_ref

        _, new_plant_ref = my_plants_collection.add(data_to_save)

        meta_ref = my_plants_collection.document(FIRESTORE_DOCUMENT_METADATA)
        meta_ref.set({"total_items": Increment(1)}, merge=True)

        return SuccessCreatePlant(
            message="Tanaman berhasil ditambahkan!",
            user_id=user_id,
            new_plant_id=new_plant_ref.id,
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}", response_model=PaginatedMyPlantSummary)
@cache(expire=300)
async def get_all_my_plants(
    user_id: str,
    page_size: int = Query(10, gt=0, le=50),
    last_doc_id: Optional[str] = None,
    _: dict = Depends(verify_user_id_match),
):
    try:
        my_plants_ref = (
            db.collection(FIRESTORE_COLLECTION_USERS)
            .document(user_id)
            .collection(FIRESTORE_COLLECTION_MY_PLANTS)
        )

        query = my_plants_ref.order_by("added_at", direction=FirestoreQuery.DESCENDING)

        if last_doc_id:
            last_doc_snapshot = my_plants_ref.document(last_doc_id).get()
            if last_doc_snapshot.exists:
                query = query.start_after(last_doc_snapshot)

        my_plants_docs = list(query.limit(page_size).stream())

        summary_list = []
        for doc in my_plants_docs:
            if doc.id == FIRESTORE_DOCUMENT_METADATA:
                continue

            my_plant_data = doc.to_dict()
            plant_ref = my_plant_data.get("plant_ref")
            if not plant_ref:
                continue

            plant_doc = plant_ref.get()
            plant_name = (
                plant_doc.to_dict().get("name", "Tanpa Nama")
                if plant_doc.exists
                else "Data Tanaman Tidak Ditemukan"
            )
            plant_id = plant_doc.id if plant_doc.exists else None

            summary = {
                "id": doc.id,
                "nickname": my_plant_data.get("nickname", ""),
                "plant_name": plant_name,
                "plant_id": plant_id,
                "disease_id": None,
                "disease_name": None,
            }

            disease_ref = my_plant_data.get("disease_ref")
            if disease_ref:
                disease_doc = disease_ref.get()
                if disease_doc.exists:
                    summary["disease_id"] = disease_doc.id
                    summary["disease_name"] = disease_doc.to_dict().get(
                        "name", "Tanpa Nama"
                    )

            summary_list.append(MyPlantSummary(**summary))

        next_last_doc_id = (
            my_plants_docs[-1].id if len(my_plants_docs) == page_size else None
        )

        meta_doc = my_plants_ref.document(FIRESTORE_DOCUMENT_METADATA).get()
        total_items = meta_doc.to_dict().get("total_items", 0) if meta_doc.exists else 0
        max_page = (total_items + page_size - 1) // page_size

        return PaginatedMyPlantSummary(
            data=summary_list,
            last_doc_id=next_last_doc_id,
            total_items=total_items,
            max_page=max_page,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/{user_id}/d/{my_plant_id}",
    status_code=status.HTTP_200_OK,
    response_model=SuccessUpdatePlant,
)
async def update_my_plant(
    user_id: str,
    my_plant_id: str,
    plant_update_data: MyPlantUpdate,
    _: dict = Depends(verify_user_id_match),
):
    try:
        doc_ref = (
            db.collection(FIRESTORE_COLLECTION_USERS)
            .document(user_id)
            .collection(FIRESTORE_COLLECTION_MY_PLANTS)
            .document(my_plant_id)
        )
        main_doc = doc_ref.get()

        if not main_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tanaman dengan ID '{my_plant_id}' tidak ditemukan.",
            )

        data_to_update = {}

        if plant_update_data.nickname is not None:
            data_to_update["nickname"] = plant_update_data.nickname
            data_to_update["nickname_lowercase"] = plant_update_data.nickname.lower()

        if plant_update_data.disease_id is not None:
            disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(
                plant_update_data.disease_id
            )
            if not (await disease_ref.get()).exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Penyakit dengan ID '{plant_update_data.disease_id}' tidak ditemukan.",
                )
            data_to_update["disease_ref"] = disease_ref
        elif plant_update_data.disease_id is None:
            data_to_update["disease_ref"] = None

        if not data_to_update:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tidak ada data untuk diupdate.",
            )

        doc_ref.update(data_to_update)

        updated_doc = doc_ref.get()
        updated_doc_data = updated_doc.to_dict()

        return {
            "message": "Tanaman berhasil diupdate!",
            "my_plant_id": updated_doc.id,
            "updated_data": {
                "plant_id": updated_doc_data["plant_ref"].id,
                "nickname": updated_doc_data["nickname"],
                "disease_id": plant_update_data.disease_id,
            },
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.delete("/{user_id}/d/{my_plant_id}", response_model=SuccessResponse)
async def delete_my_plant(
    user_id: str, my_plant_id: str, _: dict = Depends(verify_user_id_match)
):
    try:
        doc_ref = (
            db.collection(FIRESTORE_COLLECTION_USERS)
            .document(user_id)
            .collection(FIRESTORE_COLLECTION_MY_PLANTS)
            .document(my_plant_id)
        )

        if not doc_ref.get().exists:
            raise HTTPException(
                status_code=404,
                detail=f"Tanaman dengan ID '{my_plant_id}' tidak ditemukan.",
            )

        doc_ref.delete()

        meta_ref = (
            db.collection(FIRESTORE_COLLECTION_USERS)
            .document(user_id)
            .collection(FIRESTORE_COLLECTION_MY_PLANTS)
            .document(FIRESTORE_DOCUMENT_METADATA)
        )
        meta_ref.update({"total_items": Increment(-1)})

        return SuccessResponse(message="Tanaman berhasil dihapus.")

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
