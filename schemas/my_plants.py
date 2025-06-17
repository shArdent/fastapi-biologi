from pydantic import BaseModel
from typing import Optional

class MyPlantCreate(BaseModel):
    nickname: str
    plant_id: str
    disease_id: Optional[str]
