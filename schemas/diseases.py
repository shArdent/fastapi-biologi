from pydantic import BaseModel, Field
from typing import List, Optional


class DiseaseBase(BaseModel):
    name: str
    plants_listed: List[str]
    type: str
    symptoms: str
    preventions: str
    causes: str
    treatments: str
    recovery_care: str


class DiseaseCreate(DiseaseBase):
    categories_id: list[str] = Field(
        ..., description="ID/slug dari kategori penyakit, contoh: 'penyakit-jamur'"
    )


class DiseaseUpdate(BaseModel):
    name: Optional[str] = None
    plants_listed: Optional[List[str]] = None
    type: Optional[str] = None
    symptoms: Optional[str] = None
    preventions: Optional[str] = None
    causes: Optional[str] = None
    treatments: Optional[str] = None
    recovery_care: Optional[str] = None
    category_id: Optional[list[str]] = None


class DiseaseResponse(DiseaseBase):
    id: str
    category_name: list[str]


class DiseasesCursorResponse(BaseModel):
    diseases: List[DiseaseResponse]
    next_cursor: Optional[str]
