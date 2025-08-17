from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# from fastapi_cache import FastAPICache
# from fastapi_cache.backends.redis import RedisBackend
# from redis import asyncio as redis
from contextlib import asynccontextmanager

import os

from api.main import api_router
# from utils.key_builder import no_auth_header_key_builder
from utils.load_model import download_model, load_model

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    MODEL_PATH = os.getenv("MODEL_PATH")
    download_model(MODEL_PATH)
    load_model(app, MODEL_PATH)
    # redis_client = redis.Redis(
    #     host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT")
    # )
    # FastAPICache.init(
    #     RedisBackend(redis_client),
    #     prefix="fastapi-cache",
    #     key_builder=no_auth_header_key_builder,
    # )
    yield


def get_cors_origins():
    origins = os.getenv("CORS_ORIGINS", "")
    return [origin.strip() for origin in origins.split(",") if origin.strip()]


origins = get_cors_origins()

app = FastAPI(
    title="API Deteksi Penyakit Tanaman",
    description="API Project penelitian biologi deteksi penyakit & hama tanaman",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # atau ["*"] untuk semua origin
    allow_credentials=True,
    allow_methods=["*"],  # atau ["GET", "POST", ...]
    allow_headers=["*"],  # atau header tertentu: ["Authorization", "Content-Type"]
)


app.include_router(api_router, prefix="/api")
