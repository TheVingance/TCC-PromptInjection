from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator
import re


class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=3, max_length=150)
    email: str = Field(..., description="E-mail do usuário")
    cpf: str = Field(..., pattern=r"^\d{3}\.\d{3}\.\d{3}-\d{2}$", description="CPF no formato 000.000.000-00")
    password: str = Field(..., min_length=8)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Formato de e-mail inválido")
        return v.lower()


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=3, max_length=150)
    email: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email_format_opt(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
                raise ValueError("Formato de e-mail inválido")
            return v.lower()
        return v


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    cpf: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LoginRequest(BaseModel):
    email: str
    password: str
