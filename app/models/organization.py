"""
Organization and organization member models
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import String, Text, LargeBinary

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.order import Order
    from app.models.address import Address


class OrganizationRole(str, Enum):
    """Organization member role enumeration"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"


class VerificationStatus(str, Enum):
    """Verification status enumeration"""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    REJECTED = "rejected"


class Organization(BaseModel, table=True):
    """Organization model"""
    __tablename__ = "organizations"
    
    name: str = Field(
        sa_column=Column(String(255), nullable=False),
        description="Organization name"
    )
    description: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Organization description"
    )
    logo_blob: Optional[bytes] = Field(
        sa_column=Column(LargeBinary),
        default=None,
        description="Organization logo stored as blob"
    )
    logo_type: Optional[str] = Field(
        sa_column=Column(String(50)),
        default=None,
        description="MIME type for logo"
    )
    address: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Organization address"
    )
    phone: Optional[str] = Field(
        sa_column=Column(String(10)),
        default=None,
        description="Organization phone number (10 digits)"
    )
    email: Optional[str] = Field(
        sa_column=Column(String(255)),
        default=None,
        description="Organization email"
    )
    industry: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="Industry sector"
    )
    employee_count: Optional[int] = Field(
        default=None,
        description="Number of employees"
    )
    annual_revenue: Optional[float] = Field(
        default=None,
        description="Annual revenue"
    )
    credit_limit: float = Field(
        default=0.00,
        description="Credit limit for purchases"
    )
    
    # Status and Verification
    is_active: bool = Field(
        default=True,
        description="Organization active status"
    )
    is_verified: bool = Field(
        default=False,
        description="Organization verification status"
    )
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.PENDING,
        description="Verification status"
    )
    verification_notes: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Verification notes"
    )
    verified_by: Optional[UUID] = Field(
        default=None,
        foreign_key="users.id",
        description="App admin who verified"
    )
    verified_at: Optional[datetime] = Field(
        default=None,
        description="Verification timestamp"
    )
    
    # Admin Controls
    created_by: UUID = Field(
        foreign_key="users.id",
        description="App super admin who created"
    )
    disabled_by: Optional[UUID] = Field(
        default=None,
        foreign_key="users.id",
        description="Who disabled this organization"
    )
    disabled_at: Optional[datetime] = Field(
        default=None,
        description="Organization disabled timestamp"
    )
    disabled_reason: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Reason for disabling"
    )
    
    # Relationships (temporarily disabled for Phase 3 setup)
    # members: List["OrganizationMember"] = Relationship(back_populates="organization")
    # orders: List["Order"] = Relationship(back_populates="organization")
    # addresses: List["Address"] = Relationship(back_populates="organization")


class OrganizationMember(BaseModel, table=True):
    """Organization member model"""
    __tablename__ = "organization_members"
    
    user_id: UUID = Field(
        foreign_key="users.id",
        description="User ID"
    )
    organization_id: UUID = Field(
        foreign_key="organizations.id",
        description="Organization ID"
    )
    role: OrganizationRole = Field(
        description="Member role"
    )
    department: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="Department"
    )
    employee_id: Optional[str] = Field(
        sa_column=Column(String(50)),
        default=None,
        description="Employee ID"
    )
    reporting_to: Optional[UUID] = Field(
        default=None,
        foreign_key="organization_members.id",
        description="Reports to (manager)"
    )
    is_active: bool = Field(
        default=True,
        description="Member active status"
    )
    joined_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Join timestamp"
    )
    created_by: UUID = Field(
        foreign_key="users.id",
        description="Who created this membership"
    )
    
    # Relationships (temporarily disabled for Phase 3 setup)
    # user: "User" = Relationship(back_populates="organization_memberships")
    # organization: Organization = Relationship(back_populates="members")


# Pydantic schemas
class OrganizationRead(SQLModel):
    """Organization read schema"""
    id: UUID
    name: str
    description: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    annual_revenue: Optional[float] = None
    credit_limit: float
    is_active: bool
    is_verified: bool
    verification_status: VerificationStatus
    created_at: datetime


class OrganizationCreate(SQLModel):
    """Organization creation schema"""
    name: str = Field(min_length=2, max_length=255)
    description: Optional[str] = None
    phone: Optional[str] = Field(default=None, regex=r"^[6-9]\d{9}$")
    email: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = Field(default=None, ge=1)
    annual_revenue: Optional[float] = Field(default=None, ge=0)
    credit_limit: float = Field(default=0.00, ge=0)


class OrganizationUpdate(SQLModel):
    """Organization update schema"""
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    phone: Optional[str] = Field(default=None, regex=r"^[6-9]\d{9}$")
    email: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = Field(default=None, ge=1)
    annual_revenue: Optional[float] = Field(default=None, ge=0)
    credit_limit: Optional[float] = Field(default=None, ge=0)


class OrganizationMemberRead(SQLModel):
    """Organization member read schema"""
    id: UUID
    user_id: UUID
    organization_id: UUID
    role: OrganizationRole
    department: Optional[str] = None
    employee_id: Optional[str] = None
    is_active: bool
    joined_at: datetime


class OrganizationMemberCreate(SQLModel):
    """Organization member creation schema"""
    user_id: UUID
    role: OrganizationRole
    department: Optional[str] = None
    employee_id: Optional[str] = None
    reporting_to: Optional[UUID] = None
