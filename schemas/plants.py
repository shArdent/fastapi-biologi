from pydantic import BaseModel, Field
from typing import List, Optional


from schemas.plant_categories import PlantCategoryResponse


class Characteristics(BaseModel):
    max_height: str
    leaf_color: List[str]
    flower_color: List[str]
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
    description: str
    characteristics: Characteristics
    grow_information: GrowInformation
    use: List[str]


class PlantCreate(PlantBase):
    category_id: str = Field(
        ..., description="ID/slug dari kategori tanaman, contoh: 'tanaman-obat'"
    )


class PlantUpdate(BaseModel):
    name: Optional[str] = None
    latin_name: Optional[str] = None
    description: Optional[str] = None
    characteristics: Optional[Characteristics] = None
    grow_information: Optional[GrowInformation] = None
    use: Optional[List[str]] = None
    category_id: Optional[str] = None


class PlantResponse(PlantBase):
    category_name: str
    id: str


class PlantsCursorResponse(BaseModel):
    plants: List[PlantResponse]
    next_cursor: Optional[str]


class PlantsPaginatedResponse(BaseModel):
    plants: list[PlantResponse]
    total_items: int
    max_page: int
