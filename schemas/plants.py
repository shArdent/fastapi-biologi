from pydantic import BaseModel, Field
from typing import List, Optional


class Characteristics(BaseModel):
    max_height: str
    leaf_color: str
    flower_color: str
    flower_size: str
    leaf_shape: str
    stem_type: str
    root_type: str


class PlantToxicity(BaseModel):
    humans: str
    animals: str


class BasicInformation(BaseModel):
    toxicity: PlantToxicity
    potential_weeds: str
    habitats: str
    type: str
    life_expectacy: str


class GrowInformation(BaseModel):
    growing_time: str
    harvest_season: str
    harvest_time: str
    life_expectacy: str


class PlantBase(BaseModel):
    name: str
    latin_name: str
    family: str
    description: str
    basic_information: BasicInformation
    characteristics: Characteristics
    grow_information: GrowInformation
    use: str
    images: Optional[list[str]]


class PlantCreate(PlantBase):
    categories_id: list[str] = Field(
        ..., description="ID/slug dari kategori tanaman, contoh: 'tanaman-obat'"
    )


class PlantUpdate(BaseModel):
    name: Optional[str] = None
    latin_name: Optional[str] = None
    family: Optional[str] = None
    description: Optional[str] = None
    basic_information: Optional[BasicInformation] = None
    characteristics: Optional[Characteristics] = None
    grow_information: Optional[GrowInformation] = None
    use: Optional[str] = None
    categories_id: Optional[list[str]] = None


class PlantResponse(PlantBase):
    categories_name: list[str]
    id: str


class PlantsCursorResponse(BaseModel):
    plants: List[PlantResponse]
    next_cursor: Optional[str]


class PlantsPaginatedResponse(BaseModel):
    plants: list[PlantResponse]
    total_items: int
    max_page: int
