from typing import Optional
from pydantic import BaseModel


class User(BaseModel):
    username: str
    email: str
    fullname: str
    phone: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    fullname: Optional[str] = None
    phone: Optional[str] = None
