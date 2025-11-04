from enum import Enum
import io
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, Request
from PIL import Image
import numpy as np

from schemas.plants import PlantResponse
from schemas.predict_response import PredictResponse, PlantDetail
from utils.decode_prediction import decode_prediction
from utils.gradcam import (
    get_gradcam_heatmap,
    overlay_bounding_boxes,
    overlay_heatmap,
    overlay_heatmap_with_boxes,
)
from utils.image_to_base64 import image_to_base64
from utils.middlewares.verify_token import verify_firebase_token
from schemas.diseases import DiseaseResponse
from db.firestore import db
from constants.collection_name import (
    FIRESTORE_COLLECTION_DISEASES,
    FIRESTORE_COLLECTION_PLANTS,
    FIRESTORE_COLLECTION_SETTINGS,
    FIRESTORE_DOCUMENT_OUTPUT_SETTING,
)
from constants.labels import class_names
from utils.preprocess_image import preprocess_image
from utils.slugify import slugify


class ImageOutputOption(str, Enum):
    HEATMAP = "heatmap"
    BBOX = "bbox"
    BBOX_HEATMAP = "bbox_heatmap"


router = APIRouter(prefix="/predict", tags=["predict"])

concurrent_limit = asyncio.Semaphore(20)


async def try_acquire(sem: asyncio.Semaphore, timeout=0.01) -> bool:
    try:
        await asyncio.wait_for(sem.acquire(), timeout=timeout)
        return True
    except asyncio.TimeoutError:
        return False


@router.post(
    "/", response_model=PredictResponse, dependencies=[Depends(verify_firebase_token)]
)
async def predict_image(
    request: Request,
    file: UploadFile = File(...),
    option: ImageOutputOption = Query(
        ..., description="Opsi output gambar: heatmap | bbox | bbox_heatmap"
    ),
    lm: bool = Query(
        False, description="Learning Mode: True untuk mengaktifkan cam_image"
    ),
):
    acquired = await try_acquire(concurrent_limit)
    if not acquired:
        raise HTTPException(
            status_code=503, detail="Server sedang sibuk, silakan coba lagi nanti."
        )
    try:
        if lm:
            setting_doc = await (
                db.collection(FIRESTORE_COLLECTION_SETTINGS)
                .document(FIRESTORE_DOCUMENT_OUTPUT_SETTING)
                .get()
            )
            setting_data = setting_doc.to_dict() or {}

            option_key = option.value
            if not setting_data.get(option_key, False):
                raise HTTPException(
                    status_code=400,
                    detail=f"Opsi output '{option_key}' tidak tersedia.",
                )

        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        img_preprocessed = preprocess_image(image)

        env2 = request.app.state.env2
        loop = asyncio.get_event_loop()
        prediction = await loop.run_in_executor(None, env2.predict, img_preprocessed)

        pred_values = prediction[0]
        class_index = int(np.argmax(pred_values))
        confidence = float(np.max(pred_values))

        if class_index >= len(class_names):
            raise HTTPException(status_code=400, detail="Invalid class index predicted")

        if class_index >= env2.output_shape[1]:
            raise HTTPException(
                status_code=500,
                detail=f"Model output only has {env2.output_shape[1]} classes, but predicted index is {class_index}",
            )

        predicted_class = class_names[class_index]
        plant_name, disease_name, is_healthy, readable_text = decode_prediction(
            predicted_class
        )

        cam_base64 = None
        if not is_healthy and lm:
            grad_model = request.app.state.grad_model
            heatmap = await loop.run_in_executor(
                None, get_gradcam_heatmap, grad_model, img_preprocessed, class_index
            )

            overlay_map = {
                ImageOutputOption.BBOX: overlay_bounding_boxes,
                ImageOutputOption.HEATMAP: overlay_heatmap,
                ImageOutputOption.BBOX_HEATMAP: overlay_heatmap_with_boxes,
            }

            overlay_func = overlay_map.get(option)

            if overlay_func:
                cam_image = overlay_func(image, heatmap)
                cam_image = np.clip(cam_image, 0, 255).astype(np.uint8)
                cam_base64 = image_to_base64(cam_image)

        return PredictResponse(
            plant=slugify(plant_name),
            disease=f"{plant_name}_{slugify(disease_name)}",
            confidence=(round(confidence, 4)),
            message=readable_text,
            cam_image=cam_base64,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during prediction: {e}")
    finally:
        concurrent_limit.release()


@router.get(
    "/detail", response_model=PlantDetail, dependencies=[Depends(verify_firebase_token)]
)
async def get_plant_and_disease_detail(
    plant_id: str,
    disease_id: Optional[str] = Query(
        None, description="Filter tanaman berdasarkan ID Kategori"
    ),
):
    try:
        plant_doc = (
            await db.collection(FIRESTORE_COLLECTION_PLANTS).document(plant_id).get()
        )
        if not plant_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Tanaman dengan ID '{plant_id}' tidak ditemukan",
            )

        plant_data = plant_doc.to_dict() or {}
        if not plant_data:
            raise HTTPException(
                status_code=500,
                detail=f"Data tanaman dengan ID '{plant_id}' tidak valid",
            )

        cat_names = plant_data.get("categories")

        plant_response = {
            **plant_data,
            "id": plant_doc.id,
            "categories_name": cat_names,
        }
        plant = PlantResponse(**plant_response)

        disease = None
        if disease_id:
            disease_doc = await (
                db.collection(FIRESTORE_COLLECTION_DISEASES).document(disease_id).get()
            )
            if not disease_doc.exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"Penyakit dengan ID '{disease_id}' tidak ditemukan",
                )

            disease_data = disease_doc.to_dict() or {}
            if not disease_data:
                raise HTTPException(
                    status_code=500,
                    detail=f"Data penyakit dengan ID '{disease_id}' tidak valid",
                )

            cat_names = disease_data.get("categories")

            disease_response = {
                **disease_data,
                "id": disease_doc.id,
                "categories_name": cat_names,
            }
            disease = DiseaseResponse(**disease_response)

        return PlantDetail(plant_data=plant, disease_data=disease)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Terjadi kesalahan saat mengambil detail: {str(e)}"
        )
