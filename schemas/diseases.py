from pydantic import BaseModel
from typing import List


class RecoveryStep(BaseModel):
    heading: str
    description: str


class RecoveryCare(BaseModel):
    title: str
    step: List[RecoveryStep]


class Treatments(BaseModel):
    heading: str
    items: List[str]


class Preventions(BaseModel):
    heading: str
    items: List[str]


class Causes(BaseModel):
    heading: str
    items: List[str]


class Symptoms(BaseModel):
    heading: str
    items: List[str]


class Diseases(BaseModel):
    name: str
    plants_listed: List[str]
    type: str
    symptoms: Symptoms
    preventions: Preventions
    causes: Causes
    treatments: Treatments
    recovery_care: List[RecoveryCare]


class DiseasesPaginatedResponse(BaseModel):
    diseases: list[Diseases]
    total_items: int
    max_page: int
