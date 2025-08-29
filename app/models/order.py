"""
Order models for marketplace orders
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from uuid import UUID
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import String, Text, JSON

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.vendor import Vendor
    from app.models.organization import Organization
    from app.models.product import Product
    from app.models.address import Address
    from app.models.order_form import OrderForm


class OrderStatus(str, Enum):
    """Order status enumeration"""
    DRAFT = "draft"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"
    REFUNDED = "refunded"


class PaymentStatus(str, Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIAL = "partial"


class PaymentMethod(str, Enum):
    """Payment method enumeration"""
    CASH_ON_DELIVERY = "cash_on_delivery"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    UPI = "upi"
    NET_BANKING = "net_banking"
    WALLET = "wallet"
    BANK_TRANSFER = "bank_transfer"


class Order(BaseModel, table=True):
    """Order model"""
    __tablename__ = "orders"
    
    # Order identification
    order_number: str = Field(
        sa_column=Column(String(20), unique=True, nullable=False),
        description="Unique order number"
    )
    
    # Customer information
    customer_id: UUID = Field(
        foreign_key="users.id",
        description="Customer who placed the order"
    )
    organization_id: Optional[UUID] = Field(
        default=None,
        foreign_key="organizations.id",
        description="Organization for B2B orders"
    )
    
    # Vendor information
    vendor_id: UUID = Field(
        foreign_key="vendors.id",
        description="Vendor fulfilling the order"
    )
    
    # Order details
    status: OrderStatus = Field(
        default=OrderStatus.DRAFT,
        description="Current order status"
    )
    
    # Address information
    delivery_address_id: UUID = Field(
        foreign_key="addresses.id",
        description="Delivery address for the order"
    )
    billing_address_id: Optional[UUID] = Field(
        default=None,
        foreign_key="addresses.id",
        description="Billing address for the order"
    )
    
    # Pricing information
    subtotal: Decimal = Field(
        description="Subtotal before taxes and discounts"
    )
    tax_amount: Decimal = Field(
        default=Decimal('0.00'),
        description="Total tax amount"
    )
    discount_amount: Decimal = Field(
        default=Decimal('0.00'),
        description="Total discount amount"
    )
    shipping_amount: Decimal = Field(
        default=Decimal('0.00'),
        description="Shipping charges"
    )
    total_amount: Decimal = Field(
        description="Final total amount"
    )
    
    # Payment information
    payment_status: PaymentStatus = Field(
        default=PaymentStatus.PENDING,
        description="Payment status"
    )
    payment_method: Optional[PaymentMethod] = Field(
        default=None,
        description="Payment method used"
    )
    payment_reference: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="Payment reference/transaction ID"
    )
    paid_amount: Decimal = Field(
        default=Decimal('0.00'),
        description="Amount paid so far"
    )
    
    # Order timeline
    order_date: datetime = Field(
        default_factory=datetime.utcnow,
        description="Order placement date"
    )
    expected_delivery_date: Optional[datetime] = Field(
        default=None,
        description="Expected delivery date"
    )
    shipped_date: Optional[datetime] = Field(
        default=None,
        description="Shipping date"
    )
    delivered_date: Optional[datetime] = Field(
        default=None,
        description="Delivery date"
    )
    
    # Order metadata
    order_notes: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Customer notes for the order"
    )
    internal_notes: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Internal notes (vendor/admin only)"
    )
    
    # Custom form data
    custom_form_data: Optional[Dict[str, Any]] = Field(
        sa_column=Column(JSON),
        default=None,
        description="Custom form responses from order form"
    )
    order_form_id: Optional[UUID] = Field(
        default=None,
        foreign_key="order_forms.id",
        description="Custom order form used"
    )
    
    # Tracking information
    tracking_number: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="Shipping tracking number"
    )
    carrier_name: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="Shipping carrier name"
    )
    
    # Cancellation information
    cancelled_by: Optional[UUID] = Field(
        default=None,
        foreign_key="users.id",
        description="User who cancelled the order"
    )
    cancelled_at: Optional[datetime] = Field(
        default=None,
        description="Cancellation timestamp"
    )
    cancellation_reason: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Reason for cancellation"
    )
    
    # Relationships (temporarily disabled for Phase 4 setup)
    # customer: "User" = Relationship(back_populates="orders")
    # organization: Optional["Organization"] = Relationship(back_populates="orders")
    # vendor: "Vendor" = Relationship(back_populates="orders")
    # delivery_address: "Address" = Relationship(back_populates="orders")
    # order_items: List["OrderItem"] = Relationship(back_populates="order")
    # order_form: Optional["OrderForm"] = Relationship(back_populates="orders")


class OrderItem(BaseModel, table=True):
    """Order item model"""
    __tablename__ = "order_items"
    
    order_id: UUID = Field(
        foreign_key="orders.id",
        description="Order this item belongs to"
    )
    product_id: UUID = Field(
        foreign_key="products.id",
        description="Product being ordered"
    )
    
    # Item details
    quantity: int = Field(
        description="Quantity ordered"
    )
    unit_price: Decimal = Field(
        description="Unit price at time of order"
    )
    total_price: Decimal = Field(
        description="Total price for this item (quantity * unit_price)"
    )
    
    # Product snapshot (in case product details change)
    product_name: str = Field(
        sa_column=Column(String(255), nullable=False),
        description="Product name at time of order"
    )
    product_sku: Optional[str] = Field(
        sa_column=Column(String(100)),
        default=None,
        description="Product SKU at time of order"
    )
    
    # Item-specific customizations
    item_notes: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Special notes for this item"
    )
    custom_attributes: Optional[Dict[str, Any]] = Field(
        sa_column=Column(JSON),
        default=None,
        description="Custom attributes for this item"
    )
    
    # Relationships (temporarily disabled for Phase 4 setup)
    # order: Order = Relationship(back_populates="order_items")
    # product: "Product" = Relationship(back_populates="order_items")


# Pydantic schemas
class OrderItemRead(SQLModel):
    """Order item read schema"""
    id: UUID
    order_id: UUID
    product_id: UUID
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    product_name: str
    product_sku: Optional[str] = None
    item_notes: Optional[str] = None
    custom_attributes: Optional[Dict[str, Any]] = None


class OrderItemCreate(SQLModel):
    """Order item creation schema"""
    product_id: UUID
    quantity: int = Field(gt=0)
    item_notes: Optional[str] = None
    custom_attributes: Optional[Dict[str, Any]] = None


class OrderRead(SQLModel):
    """Order read schema"""
    id: UUID
    order_number: str
    customer_id: UUID
    organization_id: Optional[UUID] = None
    vendor_id: UUID
    status: OrderStatus
    delivery_address_id: UUID
    billing_address_id: Optional[UUID] = None
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    total_amount: Decimal
    payment_status: PaymentStatus
    payment_method: Optional[PaymentMethod] = None
    payment_reference: Optional[str] = None
    paid_amount: Decimal
    order_date: datetime
    expected_delivery_date: Optional[datetime] = None
    shipped_date: Optional[datetime] = None
    delivered_date: Optional[datetime] = None
    order_notes: Optional[str] = None
    tracking_number: Optional[str] = None
    carrier_name: Optional[str] = None
    custom_form_data: Optional[Dict[str, Any]] = None
    order_form_id: Optional[UUID] = None


class OrderCreate(SQLModel):
    """Order creation schema"""
    vendor_id: UUID
    organization_id: Optional[UUID] = None
    delivery_address_id: UUID
    billing_address_id: Optional[UUID] = None
    order_notes: Optional[str] = None
    custom_form_data: Optional[Dict[str, Any]] = None
    order_form_id: Optional[UUID] = None
    items: List[OrderItemCreate]


class OrderUpdate(SQLModel):
    """Order update schema"""
    status: Optional[OrderStatus] = None
    expected_delivery_date: Optional[datetime] = None
    internal_notes: Optional[str] = None
    tracking_number: Optional[str] = None
    carrier_name: Optional[str] = None


class OrderStatusUpdate(SQLModel):
    """Order status update schema"""
    status: OrderStatus
    notes: Optional[str] = None
    tracking_number: Optional[str] = None
    carrier_name: Optional[str] = None


class PaymentUpdate(SQLModel):
    """Payment update schema"""
    payment_status: PaymentStatus
    payment_method: Optional[PaymentMethod] = None
    payment_reference: Optional[str] = None
    paid_amount: Optional[Decimal] = None
