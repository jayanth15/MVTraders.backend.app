"""
Address models for users and organizations
"""
from enum import Enum
from typing import Optional, TYPE_CHECKING
from uuid import UUID
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import String, Text

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.organization import Organization
    from app.models.order import Order


class AddressType(str, Enum):
    """Address type enumeration"""
    HOME = "home"
    OFFICE = "office"
    BILLING = "billing"
    SHIPPING = "shipping"
    WAREHOUSE = "warehouse"
    OTHER = "other"


class Address(BaseModel, table=True):
    """Address model for users and organizations"""
    __tablename__ = "addresses"
    
    # Owner information (either user or organization)
    user_id: Optional[UUID] = Field(
        default=None,
        foreign_key="users.id",
        description="User who owns this address"
    )
    organization_id: Optional[UUID] = Field(
        default=None,
        foreign_key="organizations.id",
        description="Organization that owns this address"
    )
    
    # Address details
    address_type: AddressType = Field(
        description="Type of address"
    )
    label: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="Custom label for the address"
    )
    
    # Contact information
    contact_name: str = Field(
        sa_column=Column(String(100), nullable=False),
        description="Contact person name"
    )
    contact_phone: Optional[str] = Field(
        sa_column=Column(String(10)),
        default=None,
        description="Contact phone number (10 digits)"
    )
    contact_email: Optional[str] = Field(
        sa_column=Column(String(255)),
        default=None,
        description="Contact email address"
    )
    
    # Address components
    address_line_1: str = Field(
        sa_column=Column(String(255), nullable=False),
        description="First line of address"
    )
    address_line_2: Optional[str] = Field(
        sa_column=Column(String(255)),
        default=None,
        description="Second line of address"
    )
    landmark: Optional[str] = Field(
        sa_column=Column(String(255)),
        default=None,
        description="Nearby landmark"
    )
    city: str = Field(
        sa_column=Column(String(100), nullable=False),
        description="City name"
    )
    state: str = Field(
        sa_column=Column(String(100), nullable=False),
        description="State name"
    )
    postal_code: str = Field(
        sa_column=Column(String(10), nullable=False),
        description="Postal/ZIP code"
    )
    country: str = Field(
        sa_column=Column(String(100), nullable=False),
        default="India",
        description="Country name"
    )
    
    # Geographic coordinates (optional)
    latitude: Optional[float] = Field(
        default=None,
        description="Latitude coordinate"
    )
    longitude: Optional[float] = Field(
        default=None,
        description="Longitude coordinate"
    )
    
    # Status and metadata
    is_default: bool = Field(
        default=False,
        description="Default address flag"
    )
    is_active: bool = Field(
        default=True,
        description="Address active status"
    )
    delivery_instructions: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Special delivery instructions"
    )
    
    # Admin controls
    created_by: UUID = Field(
        foreign_key="users.id",
        description="User who created this address"
    )
    
    # Relationships (temporarily disabled for Phase 4 setup)
    # user: Optional["User"] = Relationship(back_populates="addresses")
    # organization: Optional["Organization"] = Relationship(back_populates="addresses")
    # orders: List["Order"] = Relationship(back_populates="delivery_address")


# Pydantic schemas
class AddressRead(SQLModel):
    """Address read schema"""
    id: UUID
    user_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    address_type: AddressType
    label: Optional[str] = None
    contact_name: str
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    address_line_1: str
    address_line_2: Optional[str] = None
    landmark: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_default: bool
    is_active: bool
    delivery_instructions: Optional[str] = None


class AddressCreate(SQLModel):
    """Address creation schema"""
    user_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    address_type: AddressType
    label: Optional[str] = Field(default=None, max_length=100)
    contact_name: str = Field(min_length=2, max_length=100)
    contact_phone: Optional[str] = Field(default=None, regex=r"^[6-9]\d{9}$")
    contact_email: Optional[str] = None
    address_line_1: str = Field(min_length=5, max_length=255)
    address_line_2: Optional[str] = Field(default=None, max_length=255)
    landmark: Optional[str] = Field(default=None, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    postal_code: str = Field(regex=r"^\d{6}$")  # Indian postal code format
    country: str = Field(default="India", max_length=100)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    is_default: bool = Field(default=False)
    delivery_instructions: Optional[str] = None


class AddressUpdate(SQLModel):
    """Address update schema"""
    address_type: Optional[AddressType] = None
    label: Optional[str] = Field(default=None, max_length=100)
    contact_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    contact_phone: Optional[str] = Field(default=None, regex=r"^[6-9]\d{9}$")
    contact_email: Optional[str] = None
    address_line_1: Optional[str] = Field(default=None, min_length=5, max_length=255)
    address_line_2: Optional[str] = Field(default=None, max_length=255)
    landmark: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, min_length=2, max_length=100)
    state: Optional[str] = Field(default=None, min_length=2, max_length=100)
    postal_code: Optional[str] = Field(default=None, regex=r"^\d{6}$")
    country: Optional[str] = Field(default=None, max_length=100)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    delivery_instructions: Optional[str] = None
