"""
Authentication schemas for request/response models
"""
from typing import Optional
from pydantic import BaseModel
from sqlmodel import SQLModel

from app.models.user import UserType


class LoginRequest(SQLModel):
    """Login request schema"""
    phone: str
    password: str


class LoginResponse(BaseModel):
    """Login response schema"""
    access_token: str
    token_type: str = "bearer"
    user: dict
    expires_in: int


class ChangePasswordRequest(SQLModel):
    """Change password request schema"""
    current_password: str
    new_password: str


class ChangePasswordResponse(BaseModel):
    """Change password response schema"""
    message: str


class ProfileUpdateRequest(SQLModel):
    """Profile update request schema"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None


class UserCreateByAdmin(SQLModel):
    """User creation by admin schema"""
    phone: str
    user_type: UserType
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None  # Only for super admin users
    temporary_password: Optional[str] = None  # If not provided, default will be used


class CreateUserResponse(BaseModel):
    """Create user response schema"""
    message: str
    user: dict
    temporary_password: str


class UserProfileResponse(BaseModel):
    """User profile response schema"""
    id: str
    phone: str
    username: Optional[str]
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: str
    user_type: UserType
    is_active: bool
    profile_completed: bool
    is_profile_complete: bool
    must_change_password: bool
    created_at: str
