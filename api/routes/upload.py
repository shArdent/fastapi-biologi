from fastapi import APIRouter
from schemas.upload import AuthParams
from utils.imagekit_client import imagekit

router = APIRouter(prefix="/upload", tags=["upload"])


@router.get("/signature", response_model=AuthParams)
def get_upload_signature():
    auth_params = imagekit.get_authentication_parameters()
    return auth_params
