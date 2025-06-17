from pydantic import BaseModel
from typing import Optional

class MyPlantCreate(BaseModel):
    nickname: str
    plant_id: str
    disease_id: Optional[str]

class MyPlantOut(MyPlantCreate):
    id: str

class MyPlantSummary(MyPlantOut):
    plant_name: str
    disease_name: Optional[str]

class PaginatedMyPlantSummary(BaseModel):
    data: list[MyPlantSummary]
    last_doc_id: Optional[str] = None
