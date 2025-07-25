from typing import Optional
from pydantic import BaseModel, Field


class PlantCategoryBase(BaseModel):
    name: str = Field(..., description="Nama kategori tanaman, contoh: Tanaman Obat")
    description: Optional[str] = Field(None, description="Deskripsi singkat kategori")
    images: list[str] = Field(default_factory=list, description="Daftar URL gambar")
    plant_count: int = Field(
        0,
        description="Jumlah tanaman dalam kategori ini (dikelola otomatis).",
        ge=0,
    )


class PlantCategoryCreate(PlantCategoryBase):
    pass


class PlantCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    images: list[str] = Field(default_factory=list, description="Daftar URL gambar")


class PlantCategoryResponse(PlantCategoryBase):
    id: str = Field(..., description="ID unik kategori, biasanya slug dari nama")
