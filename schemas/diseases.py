from pydantic import BaseModel
from typing import List

class Diseases(BaseModel):
    name: str
    plants_listed: List[str]
    type: str
    symptom: List[str]
    prevention: List[str]
    cause: List[str]
    recovery_care: List[RecoveryCare]

class RecoveryCare(BaseModel):
    title: str
    step: List[RecoveryStep]

class RecoveryStep(BaseModel):
    head: str
    description: str
