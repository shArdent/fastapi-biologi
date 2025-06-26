from pydantic import BaseModel
from typing import List


class FAQ(BaseModel):
    question: str
    answer: str


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


class Plants(BaseModel):
    name: str
    latin_name: str
    description: str
    faq: List[FAQ]
    characteristics: Characteristics
    grow_infromation: GrowInformation
    use: List[str]


class PlantsPaginatedResponse(BaseModel):
    plants: list[Plants]
    total_items: int
    max_page: int
