from fastapi import APIRouter

router = APIRouter(prefix="/tests", tags=["test"])

@router.get("/")
def ping():
    return {"message" : "pong"}