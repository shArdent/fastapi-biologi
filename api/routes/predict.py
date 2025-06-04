from fastapi import APIRouter, UploadFile, File
from PIL import Image
from fastapi.responses import JSONResponse

import io
import numpy as np
import tensorflow as tf

from constants.labels import class_names, plant_translate
from utils.preprocess_image import preprocess_image
from schemas.predict_response import PredictResponse

router = APIRouter(prefix="/predict", tags=["predict"])
model = tf.keras.models.load_model("models/env2l.h5")

@router.post("/", response_model=PredictResponse)
async def predict(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        input_tensor = preprocess_image(image)
        prediction = model.predict(input_tensor)
        predicted_class = class_names[np.argmax(prediction)]
        confidence = float(np.max(prediction))

        plant_raw, disease_raw = predicted_class.split("___")
        plant_name = plant_raw.replace("_", " ").replace("Corn (maize)", "Jagung")

        plant_key = plant_name.replace("(", "").replace(")", "").replace(",", "").strip()
        plant_final = plant_translate.get(plant_key, plant_key.lower())

        if "healthy" in disease_raw.lower():
            result_text = f"Tanaman {plant_final} ini sehat."
            disease_name = None
        else:
            disease_name = disease_raw.replace("_", " ")
            result_text = f"Tanaman {plant_final} ini memiliki penyakit {disease_name.lower()}."

        return PredictResponse(
            plant=plant_final,
            disease=disease_name.lower() if disease_name else None,
            result=result_text,
            confidence=f"{confidence:.2%}"
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})