from fastapi import FastAPI
from dotenv import load_dotenv

from api.main import api_router

load_dotenv()

app = FastAPI()

app.include_router(api_router, prefix="/api")