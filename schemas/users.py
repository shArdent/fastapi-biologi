from pydantic import BaseModel

class User(BaseModel):
    username: str
    email: str
    fullname: str
    phone: str
