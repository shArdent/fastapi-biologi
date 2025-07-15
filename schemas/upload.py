from pydantic import BaseModel


class AuthParams(BaseModel):
    token: str
    expire: int
    signature: str
