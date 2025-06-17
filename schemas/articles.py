from pydantic import BaseModel
from typing import Optional

class Article(BaseModel):
    title: str
    body: str

class ArticleOut(Article):
    id: str

class ArticlePaged(BaseModel):
    articles: list[ArticleOut]
    next_page_token: Optional[str] = None