from pydantic import BaseModel
from typing import Optional

from schemas.default_success import SuccessResponse


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
    total_items: int
    max_page: int


class SuccessCreatePlant(SuccessResponse):
    user_id: str
    new_plant_id: str


class MyPlantUpdate(BaseModel):
    nickname: Optional[str] = None
    disease_id: Optional[str] = None


class SuccessUpdatePlant(SuccessResponse):
    my_plant_id: str
    updated_data: MyPlantCreate
