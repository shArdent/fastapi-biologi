from pydantic import BaseModel
from typing import Optional

class PredictResponse(BaseModel):
    plant: str
    disease: Optional[str] = None
    result: str
    confidence: str