from fastapi import Depends, HTTPException, status
from utils.middlewares.verify_token import verify_firebase_token


def verify_is_admin(decoded_token: dict = Depends(verify_firebase_token)):
    if not decoded_token.get("isAdmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya admin yang memiliki akses.",
        )
    return decoded_token
