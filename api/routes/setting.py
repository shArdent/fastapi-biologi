from fastapi import APIRouter, Depends, HTTPException

from constants.collection_name import (
    FIRESTORE_COLLECTION_SETTINGS,
    FIRESTORE_DOCUMENT_OUTPUT_SETTING,
)
from schemas.default_success import SuccessResponse
from schemas.setting import OutputImageOption, Settings
from utils.middlewares.verify_is_admin import verify_is_admin
from utils.middlewares.verify_token import verify_firebase_token
from db.firestore import db


router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/", dependencies=[Depends(verify_firebase_token)])
async def get_all_settings():
    try:
        setting_doc = await (
            db.collection(FIRESTORE_COLLECTION_SETTINGS)
            .document(FIRESTORE_DOCUMENT_OUTPUT_SETTING)
            .get()
        )
        if not setting_doc.exists:
            raise HTTPException(status_code=404, detail="Pengaturan tidak ditemukan.")

        setting_data_dict = setting_doc.to_dict()
        if not setting_data_dict:
            raise HTTPException(status_code=404, detail="Pengaturan kosong.")

        setting_data = OutputImageOption(**setting_data_dict)

        return Settings(output_image_option=setting_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/", response_model=SuccessResponse, dependencies=[Depends(verify_is_admin)]
)
async def set_settings(new_setting: OutputImageOption):
    try:
        setting_doc_ref = db.collection(FIRESTORE_COLLECTION_SETTINGS).document(
            FIRESTORE_DOCUMENT_OUTPUT_SETTING
        )
        setting_doc = await setting_doc_ref.get()

        if not setting_doc.exists:
            raise HTTPException(status_code=404, detail="Pengaturan tidak ditemukan.")

        setting_data_dict = setting_doc.to_dict()
        if not setting_data_dict:
            raise HTTPException(status_code=404, detail="Pengaturan kosong.")

        await setting_doc_ref.update(new_setting.model_dump())

        return SuccessResponse(
            message="Pengaturan berhasil diperbarui.",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
