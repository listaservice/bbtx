"""
Authentication Pydantic schemas
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


class LoginResponse(TokenResponse):
    subscription_plan: Optional[str] = None
    subscription_status: str
    max_teams: int
    trial_ends_at: Optional[str] = None  # ISO format datetime string
    subscription_ends_at: Optional[str] = None  # ISO format datetime string
