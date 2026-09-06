"""Request and response schemas for authentication."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    """Payload for creating a Pulse account."""

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(RegisterRequest):
    """Payload for signing in to an existing account."""


class TokenResponse(BaseModel):
    """Bearer access token returned after authentication."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Safe public representation of an authenticated user."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    created_at: datetime
