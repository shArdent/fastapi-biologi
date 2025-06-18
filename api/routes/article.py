from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from google.cloud.firestore_v1.base_query import FieldFilter  
from google.cloud.firestore_v1 import Increment

from db.firestore import db
from constants.collection_name import FIRESTORE_COLLECTION_ARTICLES, FIRESTORE_DOCUMENT_METADATA
from schemas.articles import Article, ArticleOut, ArticlePaginatedResponse
from schemas.default_success import SuccessResponse

router = APIRouter(prefix="/articles", tags=["articles"])


@router.post("/", response_model=SuccessResponse, status_code=201)
def add_new_article(new_article: Article):
    try:
        query = db.collection(FIRESTORE_COLLECTION_ARTICLES).where(
            filter=FieldFilter('title', '==', new_article.title)
        ).get()

        if query:
            raise HTTPException(
                status_code=400,
                detail=f"Artikel dengan judul '{new_article.title}' sudah ada"
            )

        db.collection(FIRESTORE_COLLECTION_ARTICLES).add(new_article.model_dump())

        meta_ref = db.collection(FIRESTORE_COLLECTION_ARTICLES).document(FIRESTORE_DOCUMENT_METADATA)
        meta_ref.set({"total_items": Increment(1)}, merge=True)

        return SuccessResponse(message="Artikel baru berhasil ditambahkan")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gagal menambahkan artikel baru: {str(e)}"
        )

@router.get("/", response_model=ArticlePaginatedResponse)
def get_articles_paginated(limit: int = Query(10, gt=0, le=50), start_after_id: Optional[str] = None):
    try:
        articles_ref = db.collection(FIRESTORE_COLLECTION_ARTICLES)
        query = articles_ref.order_by("__name__")

        if start_after_id:
            start_doc = articles_ref.document(start_after_id).get()
            if not start_doc.exists:
                raise HTTPException(status_code=404, detail="Pagination token is invalid.")
            query = query.start_after(start_doc)

        docs = query.limit(limit).stream()
        articles = []
        last_doc_id = None

        for doc in docs:
            if doc.id == FIRESTORE_DOCUMENT_METADATA:
                continue
            data = ArticleOut(**doc.to_dict(), id=doc.id)
            articles.append(data)
            last_doc_id = doc.id

        meta_doc = articles_ref.document(FIRESTORE_DOCUMENT_METADATA).get()
        if not meta_doc.exists or "total_items" not in meta_doc.to_dict():
            raise HTTPException(status_code=500, detail="Metadata jumlah artikel tidak tersedia.")
        total_items = meta_doc.to_dict()["total_items"]
        max_page = (total_items + limit - 1) // limit

        return ArticlePaginatedResponse(
            articles=articles,
            total_items=total_items,
            max_page=max_page,
            next_page_token=last_doc_id if len(articles) == limit else None
        )
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

        return SuccessResponse(message="Artikel berhasil diperbarui")
    
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

        meta_ref = db.collection(FIRESTORE_COLLECTION_ARTICLES).document(FIRESTORE_DOCUMENT_METADATA)
        meta_ref.update({"total_items": Increment(-1)})

        return SuccessResponse(message="Artikel berhasil dihapus")
    
    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat menghapus data artikel: {str(e)}"
        )

