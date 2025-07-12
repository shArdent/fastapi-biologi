from pydantic import BaseModel
from typing import Optional

from schemas.plants import PlantResponse
from schemas.diseases import DiseaseResponse


class PredictResponse(BaseModel):
    plant: str
    disease: Optional[str] = None
    confidence: float
    message: str
    cam_image: Optional[str]


class PlantDetail(BaseModel):
    plant_data: PlantResponse
    disease_data: Optional[DiseaseResponse] = None
