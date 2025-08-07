from fastapi import Depends, HTTPException, Path, status

from utils.middlewares.verify_token import verify_firebase_token


def verify_user_id_match(
    uid: str = Path(...), decoded_token: dict = Depends(verify_firebase_token)
):
    if decoded_token["uid"] == uid or decoded_token.get("isAdmin"):
        return decoded_token
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Kamu tidak memiliki akses ke user_id ini.",
    )
