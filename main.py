from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

from api.main import api_router

load_dotenv()

app = FastAPI(
    title="API Deteksi Penyakit Tanaman",
    description="API Project penelitian biologi deteksi penyakit & hama tanaman",
    version="1.0.0",
    servers=[
        {"url": "https://stapin.site", "description": "Server"}
    ],
)


origins = [
    "http://localhost:3000",  # contoh frontend lokal
    "http://localhost:5173",  # contoh frontend lokal
    "https://your-frontend-domain.com",  # frontend production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # atau ["*"] untuk semua origin
    allow_credentials=True,
    allow_methods=["*"],  # atau ["GET", "POST", ...]
    allow_headers=["*"],  # atau header tertentu: ["Authorization", "Content-Type"]
)

app.include_router(api_router, prefix="/api")
