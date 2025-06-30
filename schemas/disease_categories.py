from typing import Optional
from pydantic import BaseModel, Field


class DiseaseCategoryBase(BaseModel):
    name: str = Field(..., description="Nama kategori penyakit, contoh: Penyakit Jamur")
    description: Optional[str] = Field(None, description="Deskripsi singkat kategori")


class DiseaseCategoryCreate(DiseaseCategoryBase):
    pass


class DiseaseCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class DiseaseCategoryResponse(DiseaseCategoryBase):
    id: str = Field(..., description="ID unik kategori, biasanya slug dari nama")


class SuccessResponse(BaseModel):
    message: str
