from pydantic import BaseModel
from typing import Optional

class Article(BaseModel):
    title: str
    body: str

class ArticleOut(Article):
    id: str

class ArticlePaginatedResponse(BaseModel):
    articles: list[ArticleOut]
    total_items: int
    max_page: int
    next_page_token: Optional[str] = None
