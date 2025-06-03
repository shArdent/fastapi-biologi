from fastapi import APIRouter

from api.routes import test 

api_router = APIRouter(prefix="/v1", tags=["v1"])

api_router.include_router(test.router)

