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


class UserResponse(User):
    created_at: str
    role: str
    uid: str


class PasswordReq(BaseModel):
    password: str


class EmailReq(BaseModel):
    email: str
