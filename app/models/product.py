"""
Product models for vendor marketplace
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import String, Text, LargeBinary, JSON

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.vendor import Vendor
    from app.models.user import User
    from app.models.order import OrderItem
    from app.models.review import ProductReview


class ProductStatus(str, Enum):
    """Product status enumeration"""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONTINUED = "discontinued"


class ProductCategory(str, Enum):
    """Product category enumeration"""
    ELECTRONICS = "electronics"
    CLOTHING = "clothing" 
    HOME_GARDEN = "home_garden"
    SPORTS = "sports"
    AUTOMOTIVE = "automotive"
    BOOKS = "books"
    HEALTH_BEAUTY = "health_beauty"
    FOOD_BEVERAGES = "food_beverages"
    TOYS_GAMES = "toys_games"
    OTHER = "other"


class Product(BaseModel, table=True):
    """Product model"""
    __tablename__ = "products"
    
    vendor_id: UUID = Field(
        foreign_key="vendors.id",
        description="Vendor who owns this product"
    )
    name: str = Field(
        sa_column=Column(String(255), nullable=False),
        description="Product name"
    )
    description: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Product description"
    )
    short_description: Optional[str] = Field(
        sa_column=Column(String(500)),
        default=None,
        description="Short product description"
    )
    
    # Categorization
    category: ProductCategory = Field(
        description="Product category"
    )
    subcategory: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="Product subcategory"
    )
    brand: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="Product brand"
    )
    model: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="Product model"
    )
    sku: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="Stock Keeping Unit"
    )
    
    # Pricing
    price: Decimal = Field(
        description="Product price"
    )
    cost_price: Optional[Decimal] = Field(
        default=None,
        description="Cost price for vendor"
    )
    discount_percentage: Decimal = Field(
        default=Decimal('0.00'),
        description="Discount percentage"
    )
    tax_rate: Decimal = Field(
        default=Decimal('0.00'),
        description="Tax rate percentage"
    )
    
    # Inventory
    stock_quantity: int = Field(
        default=0,
        description="Available stock quantity"
    )
    minimum_stock_level: int = Field(
        default=0,
        description="Minimum stock level for alerts"
    )
    maximum_stock_level: Optional[int] = Field(
        default=None,
        description="Maximum stock level"
    )
    
    # Physical attributes
    weight: Optional[Decimal] = Field(
        default=None,
        description="Product weight in kg"
    )
    dimensions: Optional[dict] = Field(
        sa_column=Column(JSON),
        default=None,
        description="Product dimensions (length, width, height)"
    )
    
    # Images stored as blobs
    primary_image_blob: Optional[bytes] = Field(
        sa_column=Column(LargeBinary),
        default=None,
        description="Primary product image as blob"
    )
    primary_image_type: Optional[str] = Field(
        sa_column=Column(String(50)),
        default=None,
        description="MIME type for primary image"
    )
    additional_images: Optional[dict] = Field(
        sa_column=Column(JSON),
        default=None,
        description="Additional images metadata"
    )
    
    # Product attributes
    attributes: Optional[dict] = Field(
        sa_column=Column(JSON),
        default=None,
        description="Custom product attributes"
    )
    specifications: Optional[dict] = Field(
        sa_column=Column(JSON),
        default=None,
        description="Technical specifications"
    )
    
    # SEO and Marketing
    meta_title: Optional[str] = Field(
        sa_column=Column(String(255)),
        default=None,
        description="SEO meta title"
    )
    meta_description: Optional[str] = Field(
        sa_column=Column(String(500)),
        default=None,
        description="SEO meta description"
    )
    keywords: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Search keywords"
    )
    
    # Status and Availability
    status: ProductStatus = Field(
        default=ProductStatus.DRAFT,
        description="Product status"
    )
    is_featured: bool = Field(
        default=False,
        description="Featured product flag"
    )
    is_digital: bool = Field(
        default=False,
        description="Digital product flag"
    )
    requires_shipping: bool = Field(
        default=True,
        description="Requires shipping flag"
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
    total_sales: int = Field(
        default=0,
        description="Total units sold"
    )
    
    # Admin controls
    approved_by: Optional[UUID] = Field(
        default=None,
        foreign_key="users.id",
        description="Admin who approved the product"
    )
    approved_at: Optional[datetime] = Field(
        default=None,
        description="Product approval timestamp"
    )
    is_approved: bool = Field(
        default=False,
        description="Product approval status"
    )
    
    # Relationships (temporarily disabled for Phase 3 setup)
    # vendor: "Vendor" = Relationship(back_populates="products")
    # order_items: List["OrderItem"] = Relationship(back_populates="product")
    # reviews: List["ProductReview"] = Relationship(back_populates="product")


# Pydantic schemas
class ProductRead(SQLModel):
    """Product read schema"""
    id: UUID
    vendor_id: UUID
    name: str
    description: Optional[str] = None
    short_description: Optional[str] = None
    category: ProductCategory
    subcategory: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    sku: Optional[str] = None
    price: Decimal
    discount_percentage: Decimal
    tax_rate: Decimal
    stock_quantity: int
    minimum_stock_level: int
    weight: Optional[Decimal] = None
    dimensions: Optional[dict] = None
    attributes: Optional[dict] = None
    specifications: Optional[dict] = None
    status: ProductStatus
    is_featured: bool
    is_digital: bool
    requires_shipping: bool
    rating_average: Decimal
    total_reviews: int
    total_sales: int
    is_approved: bool
    created_at: datetime


class ProductCreate(SQLModel):
    """Product creation schema"""
    vendor_id: UUID
    name: str = Field(min_length=2, max_length=255)
    description: Optional[str] = None
    short_description: Optional[str] = Field(default=None, max_length=500)
    category: ProductCategory
    subcategory: Optional[str] = Field(default=None, max_length=100)
    brand: Optional[str] = Field(default=None, max_length=100)
    model: Optional[str] = Field(default=None, max_length=100)
    sku: Optional[str] = Field(default=None, max_length=100)
    price: Decimal = Field(gt=0)
    cost_price: Optional[Decimal] = Field(default=None, ge=0)
    discount_percentage: Decimal = Field(default=Decimal('0.00'), ge=0, le=100)
    tax_rate: Decimal = Field(default=Decimal('0.00'), ge=0, le=100)
    stock_quantity: int = Field(default=0, ge=0)
    minimum_stock_level: int = Field(default=0, ge=0)
    maximum_stock_level: Optional[int] = Field(default=None, ge=0)
    weight: Optional[Decimal] = Field(default=None, gt=0)
    dimensions: Optional[dict] = None
    attributes: Optional[dict] = None
    specifications: Optional[dict] = None
    is_featured: bool = Field(default=False)
    is_digital: bool = Field(default=False)
    requires_shipping: bool = Field(default=True)


class ProductUpdate(SQLModel):
    """Product update schema"""
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    short_description: Optional[str] = Field(default=None, max_length=500)
    category: Optional[ProductCategory] = None
    subcategory: Optional[str] = Field(default=None, max_length=100)
    brand: Optional[str] = Field(default=None, max_length=100)
    model: Optional[str] = Field(default=None, max_length=100)
    sku: Optional[str] = Field(default=None, max_length=100)
    price: Optional[Decimal] = Field(default=None, gt=0)
    cost_price: Optional[Decimal] = Field(default=None, ge=0)
    discount_percentage: Optional[Decimal] = Field(default=None, ge=0, le=100)
    tax_rate: Optional[Decimal] = Field(default=None, ge=0, le=100)
    stock_quantity: Optional[int] = Field(default=None, ge=0)
    minimum_stock_level: Optional[int] = Field(default=None, ge=0)
    maximum_stock_level: Optional[int] = Field(default=None, ge=0)
    weight: Optional[Decimal] = Field(default=None, gt=0)
    dimensions: Optional[dict] = None
    attributes: Optional[dict] = None
    specifications: Optional[dict] = None
    status: Optional[ProductStatus] = None
    is_featured: Optional[bool] = None
    is_digital: Optional[bool] = None
    requires_shipping: Optional[bool] = None


class ProductApproval(SQLModel):
    """Product approval schema"""
    is_approved: bool
    approval_notes: Optional[str] = None
