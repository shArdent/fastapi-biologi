from typing import Optional
from pydantic import BaseModel, Field


class PlantCategoryBase(BaseModel):
    name: str = Field(..., description="Nama kategori tanaman, contoh: Tanaman Obat")
    description: Optional[str] = Field(None, description="Deskripsi singkat kategori")


class PlantCategoryCreate(PlantCategoryBase):
    pass


class PlantCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class PlantCategoryResponse(PlantCategoryBase):
    id: str = Field(..., description="ID unik kategori, biasanya slug dari nama")
