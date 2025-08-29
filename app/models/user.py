"""
User model with phone-based authentication
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID
import re
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import String, Text, LargeBinary
from pydantic import field_validator

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import OrganizationMember
    from app.models.vendor import Vendor
    from app.models.order import Order
    from app.models.review import VendorReview
    from app.models.address import Address


class UserType(str, Enum):
    """User type enumeration"""
    CUSTOMER = "customer"
    VENDOR = "vendor"
    ORGANIZATION_MEMBER = "organization_member"
    APP_ADMIN = "app_admin"
    APP_SUPER_ADMIN = "app_super_admin"


class User(BaseModel, table=True):
    """User model with phone-based authentication"""
    __tablename__ = "users"
    
    # Login Credentials
    phone: str = Field(
        sa_column=Column(String(10), unique=True, nullable=False),
        description="10 digit Indian phone number (primary login)"
    )
    username: Optional[str] = Field(
        sa_column=Column(String(100), unique=True),
        default=None,
        description="Only for app_super_admin"
    )
    password_hash: str = Field(
        sa_column=Column(String(255), nullable=False),
        description="Hashed password"
    )
    
    # Profile Information (Optional initially, required for orders)
    email: Optional[str] = Field(
        sa_column=Column(String(255), unique=True),
        default=None,
        description="Email address"
    )
    first_name: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="First name"
    )
    last_name: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="Last name"
    )
    avatar_blob: Optional[bytes] = Field(
        sa_column=Column(LargeBinary),
        default=None,
        description="Profile picture stored as blob"
    )
    avatar_type: Optional[str] = Field(
        sa_column=Column(String(50)),
        default=None,
        description="MIME type for avatar"
    )
    
    # Profile Completion Status
    profile_completed: bool = Field(
        default=False,
        description="Profile completion status"
    )
    profile_completion_date: Optional[datetime] = Field(
        default=None,
        description="Profile completion timestamp"
    )
    
    # User Type and Status
    user_type: UserType = Field(
        description="User type"
    )
    is_active: bool = Field(
        default=True,
        description="User active status"
    )
    
    # Default Login Management
    is_default_login: bool = Field(
        default=True,
        description="True until user changes password"
    )
    password_changed_at: Optional[datetime] = Field(
        default=None,
        description="Password change timestamp"
    )
    must_change_password: bool = Field(
        default=True,
        description="Mandatory password change flag"
    )
    
    # OTP Management (for future implementation)
    otp_enabled: bool = Field(
        default=False,
        description="OTP enabled flag"
    )
    otp_secret: Optional[str] = Field(
        sa_column=Column(String(255)),
        default=None,
        description="For future OTP implementation"
    )
    last_otp_sent: Optional[datetime] = Field(
        default=None,
        description="Last OTP sent timestamp"
    )
    otp_attempts: int = Field(
        default=0,
        description="Failed OTP attempts"
    )
    otp_locked_until: Optional[datetime] = Field(
        default=None,
        description="OTP lockout timestamp"
    )
    
    # Admin Tracking
    created_by: Optional[UUID] = Field(
        default=None,
        foreign_key="users.id",
        description="Who created this user"
    )
    disabled_by: Optional[UUID] = Field(
        default=None,
        foreign_key="users.id",
        description="Who disabled this user"
    )
    disabled_at: Optional[datetime] = Field(
        default=None,
        description="User disabled timestamp"
    )
    disabled_reason: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Reason for disabling"
    )
    
    # Relationships - Disabled for Phase 2 (authentication focus)
    # Will be restored in Phase 3 after fixing model conflicts
    # organization_memberships: List["OrganizationMember"] = Relationship(back_populates="user")
    # vendor_profile: Optional["Vendor"] = Relationship(back_populates="user")
    # orders: List["Order"] = Relationship(back_populates="customer")
    # reviews: List["VendorReview"] = Relationship(back_populates="reviewer")
    # addresses: List["Address"] = Relationship(back_populates="user")
    
    def __str__(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.phone
    
    @property
    def full_name(self) -> str:
        """Get full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return ""
    
    @property
    def is_profile_complete(self) -> bool:
        """Check if profile is complete enough for orders"""
        return bool(
            self.first_name and 
            self.last_name and 
            self.email
        )


class UserRead(SQLModel):
    """User read schema"""
    id: UUID
    phone: str
    username: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    user_type: UserType
    is_active: bool
    profile_completed: bool
    is_default_login: bool
    must_change_password: bool


class UserCreate(SQLModel):
    """User creation schema"""
    phone: str = Field(description="10 digit Indian phone number")
    user_type: UserType
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^[6-9]\d{9}$", v):
            raise ValueError("Phone number must be a 10-digit Indian number starting with 6-9")
        return v


class UserUpdate(SQLModel):
    """User update schema"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None


class UserLogin(SQLModel):
    """User login schema"""
    phone: str = Field(description="10 digit Indian phone number")
    password: str
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^[6-9]\d{9}$", v):
            raise ValueError("Phone number must be a 10-digit Indian number starting with 6-9")
        return v


class PasswordChange(SQLModel):
    """Password change schema"""
    current_password: str
    new_password: str = Field(min_length=8)
