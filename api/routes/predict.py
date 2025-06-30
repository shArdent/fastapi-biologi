from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from PIL import Image
from fastapi.responses import JSONResponse
from typing import Optional
import io
import numpy as np
from starlette.concurrency import run_in_threadpool
import tensorflow as tf

from constants.labels import class_names, plant_translate
from utils.middlewares.verify_token import verify_firebase_token
from utils.preprocess_image import preprocess_image
from schemas.predict_response import PredictResponse, PlantDetail
from schemas.plants import PlantResponse
from schemas.diseases import Diseases
from db.firestore import db
from constants.collection_name import (
    FIRESTORE_COLLECTION_PLANTS,
    FIRESTORE_COLLECTION_DISEASES,
)

router = APIRouter(prefix="/predict", tags=["predict"])
model = tf.keras.models.load_model("models/env2l.h5")


@router.post(
    "/", response_model=PredictResponse, dependencies=[Depends(verify_firebase_token)]
)
async def predict(file: UploadFile = File(...)):
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
def get_plant_and_disease_detail(plant_id: str, disease_id: Optional[str]):
    try:
        plant_ref = db.collection(FIRESTORE_COLLECTION_PLANTS).document(plant_id)
        plant_doc = plant_ref.get()

        if not plant_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Tanaman dengan ID '{plant_id}' tidak ditemukan",
            )

        plant_data = plant_doc.to_dict()
        if not plant_data:
            raise HTTPException(
                status_code=500,
                detail=f"Data tanaman dengan ID '{plant_id}' tidak valid",
            )
        plant = PlantResponse(**plant_data)

        disease = None
        if disease_id:
            disease_ref = db.collection(FIRESTORE_COLLECTION_DISEASES).document(
                disease_id
            )
            disease_doc = disease_ref.get()

            if not disease_doc.exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"Penyakit dengan ID '{disease_id}' tidak ditemukan",
                )

            disease_data = disease_doc.to_dict()
            if not disease_data:
                raise HTTPException(
                    status_code=500,
                    detail=f"Data penyakit dengan ID '{disease_id}' tidak valid",
                )

            disease = Diseases(**disease_data)

        return PlantDetail(plant_data=plant, disease_data=disease)

    except HTTPException as he:
        raise he

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Terjadi kesalahan saat mengambil detail: {str(e)}"
        )
