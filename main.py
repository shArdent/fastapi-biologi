from fastapi import FastAPI, APIRouter

from api.main import api_router

app = FastAPI()

app.include_router(api_router, prefix="/api")