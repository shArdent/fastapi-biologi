from fastapi import APIRouter

from api.routes import test
from api.routes import predict 
from api.routes import plant

api_router = APIRouter(prefix="/v1")

api_router.include_router(test.router)
api_router.include_router(predict.router)
api_router.include_router(plant.router)

