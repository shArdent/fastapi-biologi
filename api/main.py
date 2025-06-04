from fastapi import APIRouter

from api.routes import test
from api.routes import predict 

api_router = APIRouter(prefix="/v1")

api_router.include_router(test.router)
api_router.include_router(predict.router)

