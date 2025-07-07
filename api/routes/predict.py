import io
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from PIL import Image
import numpy as np
import tensorflow as tf

from schemas.plants import PlantResponse
from schemas.predict_response import PlantDetail, PredictResponse
from utils.middlewares.verify_token import verify_firebase_token
from schemas.diseases import DiseaseResponse
from db.firestore import db
from constants.collection_name import (
    FIRESTORE_COLLECTION_DISEASES,
    FIRESTORE_COLLECTION_PLANTS,
)
from constants.labels import class_names, plant_translate
from utils.preprocess_image import preprocess_image

model = tf.keras.models.load_model("models/env2l.h5")

router = APIRouter(prefix="/predict", tags=["predict"])

@router.post(
    "/", response_model=PredictResponse, dependencies=[Depends(verify_firebase_token)]
)
async def predict(file: UploadFile=File(...)):
    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        input_tensor = preprocess_image(image)
        prediction = await run_in_threadpool(model.predict, input_tensor)
        predicted_class = class_names[np.argmax(prediction)]
        confidence = float(np.max(prediction))

        plant_raw, disease_raw = predicted_class.split("___")
        plant_name = plant_raw.replace("_", " ").replace("Corn (maize)", "Jagung")

        plant_key = (
            plant_name.replace("(", "").replace(")", "").replace(",", "").strip()
        )
        plant_final = plant_translate.get(plant_key, plant_key.lower())

        if "healthy" in disease_raw.lower():
            result_text = f"Tanaman {plant_final} ini sehat."
            disease_name = None
        else:
            disease_name = disease_raw.replace("_", " ")
            result_text = (
                f"Tanaman {plant_final} ini memiliki penyakit {disease_name.lower()}."
            )

        return PredictResponse(
            plant=plant_final,
            disease=disease_name.lower() if disease_name else None,
            result=result_text,
            confidence=f"{confidence:.2%}",
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


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

        plant_response = {**plant_data, "id": plant_doc.id}
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

            disease_response = {
                **disease_data,
                "id": disease_doc.id,
            }
            disease = DiseaseResponse(**disease_response)

        return PlantDetail(plant_data=plant, disease_data=disease)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Terjadi kesalahan saat mengambil detail: {str(e)}"
        )
