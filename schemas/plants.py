from pydantic import BaseModel
from typing import List

class FAQ(BaseModel):
    question: str
    answer: str

class Characteristics(BaseModel):
    max_height: str
    max_spread: str
    leaf_color: List[str]
    leaf_type: str
    planting_time: List[str]

class Climate(BaseModel):
    temperature: str
    hardness: str


class CareConditions(BaseModel):
    soil: List[str]
    location: str
    sunlight: str
    climate: Climate

class Plants(BaseModel):
    name: str
    faq: List[FAQ]
    distribution: List[str]
    characteristics: Characteristics
    care_conditions: CareConditions
    use: str
    adaptation_strategy: str
    history: str
    name_origin: str
    symbolism: str
