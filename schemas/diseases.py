from pydantic import BaseModel, Field
from typing import List, Optional


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


class DiseaseBase(BaseModel):
    name: str
    plants_listed: List[str]
    type: str
    symptoms: Symptoms
    preventions: Preventions
    causes: Causes
    treatments: Treatments
    recovery_care: List[RecoveryCare]


class DiseaseCreate(DiseaseBase):
    category_id: str = Field(
        ..., description="ID/slug dari kategori penyakit, contoh: 'penyakit-jamur'"
    )


class DiseaseUpdate(BaseModel):
    name: Optional[str] = None
    plants_listed: Optional[List[str]] = None
    type: Optional[str] = None
    symptoms: Optional[Symptoms] = None
    preventions: Optional[Preventions] = None
    causes: Optional[Causes] = None
    treatments: Optional[Treatments] = None
    recovery_care: Optional[RecoveryCare] = None
    category_id: Optional[str] = None


class DiseaseResponse(DiseaseBase):
    id: str
    category_name: str


class DiseasesCursorResponse(BaseModel):
    diseases: List[DiseaseResponse]
    next_cursor: Optional[str]
