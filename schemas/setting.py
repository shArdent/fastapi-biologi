from pydantic import BaseModel


class OutputImageOption(BaseModel):
    heatmap: bool
    bbox: bool
    bbox_heatmap: bool


class Settings(BaseModel):
    output_image_option: OutputImageOption | None
