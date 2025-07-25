from typing import Optional
from pydantic import BaseModel, Field


class DiseaseCategoryBase(BaseModel):
    name: str = Field(..., description="Nama kategori penyakit, contoh: Penyakit Jamur")
    description: Optional[str] = Field(None, description="Deskripsi singkat kategori")
    images: Optional[list[str]] = Field(
        default_factory=list, description="Daftar URL gambar"
    )
    disease_count: int = Field(
        0,
        description="Jumlah penyakit dalam kategori ini (dikelola otomatis).",
        ge=0,
    )


class DiseaseCategoryCreate(DiseaseCategoryBase):
    pass


class DiseaseCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    images: Optional[list[str]] = Field(
        default_factory=list, description="Daftar URL gambar"
    )


class DiseaseCategoryResponse(DiseaseCategoryBase):
    id: str = Field(..., description="ID unik kategori, biasanya slug dari nama")


class SuccessResponse(BaseModel):
    message: str
