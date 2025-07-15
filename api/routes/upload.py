from fastapi import APIRouter, Depends
from schemas.upload import AuthParams
from utils.imagekit_client import imagekit
from utils.middlewares.verify_is_admin import verify_is_admin

router = APIRouter(prefix="/upload", tags=["upload"])


@router.get(
    "/signature", response_model=AuthParams, dependencies=[Depends(verify_is_admin)]
)
def get_upload_signature():
    auth_params = imagekit.get_authentication_parameters()
    return auth_params
