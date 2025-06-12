from pydantic import BaseModel

class Article(BaseModel):
    title: str
    body: str
