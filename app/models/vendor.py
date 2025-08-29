"""
Vendor model with subscription management
"""
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import String, Text, LargeBinary, JSON

from app.models.base import BaseModel
from app.models.organization import VerificationStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.product import Product
    from app.models.order import Order
    from app.models.review import VendorReview


class SubscriptionPlan(str, Enum):
    """Subscription plan enumeration"""
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    """Subscription status enumeration"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    PENDING = "pending"


class Vendor(BaseModel, table=True):
    """Vendor model with subscription management"""
    __tablename__ = "vendors"
    
    user_id: UUID = Field(
        foreign_key="users.id",
        unique=True,
        description="Associated user account"
    )
    business_name: str = Field(
        sa_column=Column(String(255), nullable=False),
        description="Business name"
    )
    business_description: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Business description"
    )
    business_address: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Business address"
    )
    business_phone: Optional[str] = Field(
        sa_column=Column(String(10)),
        default=None,
        description="Business phone number (10 digits)"
    )
    business_email: Optional[str] = Field(
        sa_column=Column(String(255)),
        default=None,
        description="Business email"
    )
    
    # Images stored as blobs
    logo_blob: Optional[bytes] = Field(
        sa_column=Column(LargeBinary),
        default=None,
        description="Vendor logo stored as blob"
    )
    logo_type: Optional[str] = Field(
        sa_column=Column(String(50)),
        default=None,
        description="MIME type for logo"
    )
    banner_blob: Optional[bytes] = Field(
        sa_column=Column(LargeBinary),
        default=None,
        description="Vendor banner stored as blob"
    )
    banner_type: Optional[str] = Field(
        sa_column=Column(String(50)),
        default=None,
        description="MIME type for banner"
    )
    
    # Ratings and Reviews
    rating_average: Decimal = Field(
        default=Decimal('0.00'),
        description="Average rating"
    )
    total_reviews: int = Field(
        default=0,
        description="Total number of reviews"
    )
    
    # Subscription Management
    subscription_plan: SubscriptionPlan = Field(
        default=SubscriptionPlan.BASIC,
        description="Current subscription plan"
    )
    subscription_status: SubscriptionStatus = Field(
        default=SubscriptionStatus.PENDING,
        description="Subscription status"
    )
    subscription_start_date: Optional[date] = Field(
        default=None,
        description="Subscription start date"
    )
    subscription_end_date: Optional[date] = Field(
        default=None,
        description="Subscription end date"
    )
    monthly_fee: Decimal = Field(
        default=Decimal('0.00'),
        description="Monthly subscription fee"
    )
    last_payment_date: Optional[date] = Field(
        default=None,
        description="Last payment date"
    )
    next_payment_due: Optional[date] = Field(
        default=None,
        description="Next payment due date"
    )
    
    # Verification & Approval
    is_verified: bool = Field(
        default=False,
        description="Vendor verification status"
    )
    is_active: bool = Field(
        default=True,
        description="Vendor active status"
    )
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.PENDING,
        description="Verification status"
    )
    verification_documents: Optional[dict] = Field(
        sa_column=Column(JSON),
        default=None,
        description="Store optional document URLs and types"
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
        description="App super admin who onboarded"
    )
    approved_by: Optional[UUID] = Field(
        default=None,
        foreign_key="users.id",
        description="App admin who approved"
    )
    approved_at: Optional[datetime] = Field(
        default=None,
        description="Approval timestamp"
    )
    disabled_by: Optional[UUID] = Field(
        default=None,
        foreign_key="users.id",
        description="Who disabled this vendor"
    )
    disabled_at: Optional[datetime] = Field(
        default=None,
        description="Vendor disabled timestamp"
    )
    disabled_reason: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Reason for disabling"
    )
    
    # Performance Metrics (for tracking purposes)
    total_orders: int = Field(
        default=0,
        description="Total number of orders"
    )
    on_time_delivery_rate: Decimal = Field(
        default=Decimal('0.00'),
        description="On-time delivery rate percentage"
    )
    order_fulfillment_rate: Decimal = Field(
        default=Decimal('0.00'),
        description="Order fulfillment rate percentage"
    )
    
    # Relationships (temporarily disabled for Phase 3 setup)
    # user: "User" = Relationship(back_populates="vendor_profile")
    # products: List["Product"] = Relationship(back_populates="vendor")
    # orders: List["Order"] = Relationship(back_populates="vendor")
    # reviews: List["VendorReview"] = Relationship(back_populates="vendor")


# Pydantic schemas
class VendorRead(SQLModel):
    """Vendor read schema"""
    id: UUID
    user_id: UUID
    business_name: str
    business_description: Optional[str] = None
    business_address: str
    business_phone: Optional[str] = None
    business_email: Optional[str] = None
    rating_average: Decimal
    total_reviews: int
    subscription_plan: SubscriptionPlan
    subscription_status: SubscriptionStatus
    monthly_fee: Decimal
    is_verified: bool
    is_active: bool
    verification_status: VerificationStatus
    total_orders: int
    on_time_delivery_rate: Decimal
    order_fulfillment_rate: Decimal
    created_at: datetime


class VendorCreate(SQLModel):
    """Vendor creation schema"""
    user_id: UUID
    business_name: str = Field(min_length=2, max_length=255)
    business_description: Optional[str] = None
    business_address: str = Field(min_length=10)
    business_phone: Optional[str] = Field(default=None, regex=r"^[6-9]\d{9}$")
    business_email: Optional[str] = None
    subscription_plan: SubscriptionPlan = SubscriptionPlan.BASIC
    monthly_fee: Decimal = Field(default=Decimal('0.00'), ge=0)


class VendorUpdate(SQLModel):
    """Vendor update schema"""
    business_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    business_description: Optional[str] = None
    business_address: Optional[str] = Field(default=None, min_length=10)
    business_phone: Optional[str] = Field(default=None, regex=r"^[6-9]\d{9}$")
    business_email: Optional[str] = None
    subscription_plan: Optional[SubscriptionPlan] = None
    monthly_fee: Optional[Decimal] = Field(default=None, ge=0)
