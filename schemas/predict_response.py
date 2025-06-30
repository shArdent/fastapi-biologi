from pydantic import BaseModel
from typing import Optional

from schemas.plants import PlantResponse
from schemas.diseases import Diseases

class PredictResponse(BaseModel):
    plant: str
    disease: Optional[str] = None
    result: str
    confidence: str

class PlantDetail(BaseModel):
    plant_data : PlantResponse
    disease_data: Optional[Diseases] = None
