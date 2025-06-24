from fastapi import APIRouter

from api.routes import my_plant, predict, plant, disease, test, user, article

api_router = APIRouter(prefix="/v1")

api_router.include_router(test.router)
api_router.include_router(predict.router)
api_router.include_router(plant.router)
api_router.include_router(disease.router)
api_router.include_router(article.router)
api_router.include_router(user.router)
api_router.include_router(my_plant.router)
