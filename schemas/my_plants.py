from pydantic import BaseModel, Field
from typing import Optional

from schemas.default_success import SuccessResponse


class MyPlantCreate(BaseModel):
    nickname: str
    plant_id: str
    disease_id: Optional[str] = Field(None)


class MyPlantOut(MyPlantCreate):
    id: str
    plant_name: str
    disease_name: Optional[str] = Field(None)


class PaginatedMyPlantSummary(BaseModel):
    data: list[MyPlantOut]
    last_doc_id: Optional[str] = None


class SuccessCreatePlant(SuccessResponse):
    user_id: str
    new_plant_id: str


class MyPlantUpdate(BaseModel):
    nickname: Optional[str] = None
    disease_id: Optional[str] = None


class SuccessUpdatePlant(SuccessResponse):
    message: str
    plant: MyPlantOut
