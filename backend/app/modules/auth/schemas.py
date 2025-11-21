"""
Modulo de Autenticacion - Schemas

Define todos los schemas Pydantic para validacion de datos.
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class LoginRequest(BaseModel):
    """Request para login."""
    email: EmailStr
    password: str = Field(..., min_length=8)


class RegisterRequest(BaseModel):
    """Request para registro."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=2, max_length=100)
    role: str = "ADMIN"  # AdminRole default


class RefreshTokenRequest(BaseModel):
    """Request para renovar token."""
    refresh_token: str


class AuthResponse(BaseModel):
    """Response con tokens de autenticacion."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos
    user: "UserResponse"


class UserResponse(BaseModel):
    """Informacion de usuario."""
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True  # Para compatibilidad con SQLAlchemy
