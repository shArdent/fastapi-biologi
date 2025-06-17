from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from google.cloud.firestore_v1.base_query import FieldFilter  

from db.firestore import db
from constants.collection_name import FIRESTORE_COLLECTION_ARTICLES
from schemas.articles import Article, ArticleOut, ArticlePaged
from schemas.default_success import SuccessResponse

router = APIRouter(prefix="/articles", tags=["articles"])
\
@router.post("/", response_model=SuccessResponse, status_code=201)
def add_new_article(new_article: Article):
    try:

        is_exist = db.collection(FIRESTORE_COLLECTION_ARTICLES).where(filter=FieldFilter('title', '==', new_article.title)).get()
        if is_exist:
            raise HTTPException(
                status_code=400,
                detail=f"Artikel dengan judul {new_article.title} sudah ada"
            )

        db.collection(FIRESTORE_COLLECTION_ARTICLES).add(new_article.model_dump())


        return {"message": "Artikel baru berhasil ditambahkan"}
    except Exception as e:
        return {"error": str(e), "message": "Gagal menambahkan artikel baru"}

@router.get("/", response_model=ArticlePaged)
def get_articles_paginated(limit: int = Query(10, gt=0, le=50), start_after_id: Optional[str] = None):
    try:
        query = db.collection(FIRESTORE_COLLECTION_ARTICLES).order_by("__name__")
    
        if start_after_id:
                start_doc_ref = db.collection(FIRESTORE_COLLECTION_ARTICLES).document(start_after_id)
                start_doc = start_doc_ref.get()

                if not start_doc.exists:
                    raise HTTPException(status_code=404, detail="Pagination token is invalid.")
                
                query = query.start_after(start_doc)

        docs = query.limit(limit).stream()
        articles = []

        for doc in docs:
            data = ArticleOut(**doc.to_dict(), id=doc.id)
            articles.append(data)
            last_doc_id = doc.id
        
        next_token = None
        if len(articles) == limit:
            next_token = last_doc_id
            
        return ArticlePaged(articles=articles, next_page_token=next_token)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat mengambil data artikel: {str(e)}"
        )
    
@router.get("/{id}", response_model=ArticleOut)
def get_article_by_id(id:str):
    try:
        article_ref = db.collection(FIRESTORE_COLLECTION_ARTICLES).document(id)
        article_doc = article_ref.get()

        if not article_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Tanaman dengan id {id} tidak ditemukan"
            )

        return ArticleOut(**article_doc.to_dict(), id=article_doc.id)
    
    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat mengambil data artikel: {str(e)}"
        )

@router.patch("/{id}", response_model=SuccessResponse)
def update_article(id: str, updated_articles: Article):
    try:
        article_ref = db.collection(FIRESTORE_COLLECTION_ARTICLES).document(id)
        article_doc = article_ref.get()

        if not article_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Artikel dengan id {id} tidak ditemukan"
            )

        article_ref.update(updated_articles.model_dump(exclude_unset=True))

        return {"message": "Artikel berhasil diperbarui"}
    
    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat memperbarui data artikel: {str(e)}"
        )
    
@router.delete("/{id}", response_model=SuccessResponse)
def delete_article(id: str):
    try:
        article_ref = db.collection(FIRESTORE_COLLECTION_ARTICLES).document(id)
        article_doc = article_ref.get()

        if not article_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Artikel dengan id {id} tidak ditemukan"
            )

        article_ref.delete()

        return {"message": "Artikel berhasil dihapus"}
    
    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat menghapus data artikel: {str(e)}"
        )