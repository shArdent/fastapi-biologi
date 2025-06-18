from pydantic import BaseModel
from typing import Optional

from schemas.plants import Plants
from schemas.diseases import Diseases

class PredictResponse(BaseModel):
    plant: str
    disease: Optional[str] = None
    result: str
    confidence: str

class PlantDetail(BaseModel):
    plant_data : Plants
    disease_data: Optional[Diseases] = None
