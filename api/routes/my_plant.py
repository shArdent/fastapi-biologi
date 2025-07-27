from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
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
    MyPlantOut,
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
    user_id: str, myplant_data: MyPlantCreate, _: dict = Depends(verify_user_id_match)
):
    try:
        my_plants_collection = (
            db.collection(FIRESTORE_COLLECTION_USERS)
            .document(user_id)
            .collection(FIRESTORE_COLLECTION_MY_PLANTS)
        )

        plant_doc = (
            await db.collection(FIRESTORE_COLLECTION_PLANTS)
            .document(myplant_data.plant_id)
            .get()
        )
        if not plant_doc:
            raise HTTPException(
                status_code=404,
                detail=f"Tanaman dengan if {myplant_data.plant_id} tidak ditemukan",
            )

        plant_data = plant_doc.to_dict()
        if not plant_data:
            raise HTTPException(
                status_code=404,
                detail=f"Tanaman dengan if {myplant_data.plant_id} tidak ditemukan",
            )

        data_to_save = {
            "nickname": myplant_data.nickname,
            "plant_id": plant_doc.id,
            "plant_name": plant_data.get("name"),
            "added_at": SERVER_TIMESTAMP,
        }

        if myplant_data.disease_id:
            disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(
                myplant_data.disease_id
            )
            disease_doc = await disease_ref.get()
            if not disease_doc.exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"Penyakit dengan ID '{myplant_data.disease_id}' tidak ditemukan.",
                )
            disease_data = disease_doc.to_dict()

            data_to_save["disease_id"] = disease_doc.id if disease_data else None
            data_to_save["disease_name"] = (
                disease_data.get("name") if disease_data else None
            )

        _, new_plant_ref = await my_plants_collection.add(data_to_save)

        meta_ref = my_plants_collection.document(FIRESTORE_DOCUMENT_METADATA)
        await meta_ref.set({"total_items": Increment(1)}, merge=True)

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
            last_doc_snapshot = await my_plants_ref.document(last_doc_id).get()
            if last_doc_snapshot.exists:
                query = query.start_after(last_doc_snapshot)

        my_plants_docs = await query.limit(page_size).get()

        if not my_plants_docs:
            return PaginatedMyPlantSummary(data=[], last_doc_id=None)

        summary_list = []
        for doc in my_plants_docs:
            if doc.id == FIRESTORE_DOCUMENT_METADATA:
                continue

            myplant_data = doc.to_dict()

            user_plant = {**myplant_data, "id": doc.id}

            summary_list.append(MyPlantOut(**user_plant))

        next_last_doc_id = (
            my_plants_docs[-1].id if len(summary_list) == page_size else None
        )

        return PaginatedMyPlantSummary(
            data=summary_list,
            last_doc_id=next_last_doc_id,
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
        myplant_ref = (
            db.collection(FIRESTORE_COLLECTION_USERS)
            .document(user_id)
            .collection(FIRESTORE_COLLECTION_MY_PLANTS)
            .document(my_plant_id)
        )
        myplant_doc = await myplant_ref.get()

        if not myplant_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tanaman dengan ID '{my_plant_id}' tidak ditemukan.",
            )

        print(plant_update_data.disease_id)
        data_to_update = {}

        if plant_update_data.nickname is not None:
            data_to_update["nickname"] = plant_update_data.nickname

        if plant_update_data.disease_id is not None:
            disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(
                plant_update_data.disease_id
            )
            disease_doc = await disease_ref.get()
            if not disease_doc.exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Penyakit dengan ID '{plant_update_data.disease_id}' tidak ditemukan.",
                )
            disease_data = disease_doc.to_dict()
            data_to_update["disease_id"] = disease_doc.id
            data_to_update["disease_name"] = (
                disease_data.get("name") if disease_data else "Tidak diketahui"
            )
        elif plant_update_data.disease_id is None:
            data_to_update["disease_id"] = None
            data_to_update["disease_name"] = None

        if not data_to_update:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tidak ada data untuk diupdate.",
            )

        await myplant_ref.update(data_to_update)

        updated_doc = await myplant_ref.get()
        updated_doc_data = updated_doc.to_dict()

        return SuccessUpdatePlant(
            message="Berhasil update tanaman",
            plant=MyPlantOut(**updated_doc_data, id=updated_doc.id),
        )
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

        if not (await doc_ref.get()).exists:
            raise HTTPException(
                status_code=404,
                detail=f"Tanaman dengan ID '{my_plant_id}' tidak ditemukan.",
            )

        await doc_ref.delete()

        meta_ref = (
            db.collection(FIRESTORE_COLLECTION_USERS)
            .document(user_id)
            .collection(FIRESTORE_COLLECTION_MY_PLANTS)
            .document(FIRESTORE_DOCUMENT_METADATA)
        )
        await meta_ref.update({"total_items": Increment(-1)})

        return SuccessResponse(message="Tanaman berhasil dihapus.")

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
