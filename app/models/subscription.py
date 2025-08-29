"""
Subscription and billing models for vendor subscription management.
"""

from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from datetime import datetime, timedelta
from enum import Enum
from decimal import Decimal

from app.models.base import TimestampModel


class SubscriptionPlanType(str, Enum):
    """Subscription plan types"""
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class BillingCycle(str, Enum):
    """Billing cycle options"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    LIFETIME = "lifetime"


class SubscriptionStatus(str, Enum):
    """Subscription status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    TRIAL = "trial"


class PaymentStatus(str, Enum):
    """Payment status"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    """Payment methods"""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    NET_BANKING = "net_banking"
    UPI = "upi"
    WALLET = "wallet"
    BANK_TRANSFER = "bank_transfer"


class SubscriptionPlan(SQLModel, table=True):
    """
    Subscription plans available for vendors
    """
    __tablename__ = "subscription_plans"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Plan details
    name: str = Field(max_length=100, description="Plan name")
    description: Optional[str] = Field(default=None, max_length=500, description="Plan description")
    plan_type: SubscriptionPlanType = Field(description="Type of subscription plan")
    
    # Pricing
    base_price: Decimal = Field(decimal_places=2, description="Base price for the plan")
    billing_cycle: BillingCycle = Field(description="Billing cycle")
    setup_fee: Optional[Decimal] = Field(default=None, decimal_places=2, description="One-time setup fee")
    
    # Plan features
    features: dict = Field(default_factory=dict, sa_column=Column(JSON), description="Plan features and limits")
    
    # Plan limits
    max_products: Optional[int] = Field(default=None, description="Maximum products allowed")
    max_orders_per_month: Optional[int] = Field(default=None, description="Maximum orders per month")
    max_storage_mb: Optional[int] = Field(default=None, description="Maximum storage in MB")
    
    # Plan settings
    is_active: bool = Field(default=True, description="Whether plan is available for subscription")
    is_featured: bool = Field(default=False, description="Whether plan is featured")
    sort_order: int = Field(default=0, description="Display order")
    
    # Trial settings
    trial_days: Optional[int] = Field(default=None, description="Trial period in days")
    
    # Relationships
    subscriptions: List["Subscription"] = Relationship(back_populates="plan")
    
    def __str__(self):
        return f"{self.name} ({self.plan_type}) - ₹{self.base_price}/{self.billing_cycle}"


class Subscription(SQLModel, table=True):
    """
    Vendor subscriptions
    """
    __tablename__ = "subscriptions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Subscription identification
    vendor_id: int = Field(foreign_key="vendors.id", description="Vendor who owns this subscription")
    plan_id: int = Field(foreign_key="subscription_plans.id", description="Subscription plan")
    
    # Subscription details
    status: SubscriptionStatus = Field(default=SubscriptionStatus.ACTIVE, description="Subscription status")
    
    # Subscription period
    start_date: datetime = Field(description="Subscription start date")
    end_date: Optional[datetime] = Field(default=None, description="Subscription end date")
    trial_end_date: Optional[datetime] = Field(default=None, description="Trial end date")
    
    # Billing
    current_period_start: datetime = Field(description="Current billing period start")
    current_period_end: datetime = Field(description="Current billing period end")
    next_billing_date: Optional[datetime] = Field(default=None, description="Next billing date")
    
    # Pricing
    amount: Decimal = Field(decimal_places=2, description="Subscription amount per billing cycle")
    currency: str = Field(default="INR", max_length=3, description="Currency code")
    
    # Subscription metadata
    subscription_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON), description="Additional subscription data")
    
    # Cancellation
    cancelled_at: Optional[datetime] = Field(default=None, description="Cancellation date")
    cancellation_reason: Optional[str] = Field(default=None, max_length=500, description="Reason for cancellation")
    
    # Auto-renewal
    auto_renew: bool = Field(default=True, description="Whether subscription auto-renews")
    
    # Relationships
    vendor: Optional["Vendor"] = Relationship()
    plan: Optional["SubscriptionPlan"] = Relationship(back_populates="subscriptions")
    payments: List["Payment"] = Relationship(back_populates="subscription")
    usage_records: List["UsageRecord"] = Relationship(back_populates="subscription")
    
    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        if self.status not in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]:
            return False
        
        if self.end_date and self.end_date < datetime.utcnow():
            return False
            
        return True
    
    def is_trial(self) -> bool:
        """Check if subscription is in trial period"""
        if self.status != SubscriptionStatus.TRIAL:
            return False
            
        if self.trial_end_date and self.trial_end_date > datetime.utcnow():
            return True
            
        return False
    
    def days_remaining(self) -> Optional[int]:
        """Get days remaining in subscription"""
        if not self.end_date:
            return None
            
        delta = self.end_date - datetime.utcnow()
        return max(0, delta.days)
    
    def __str__(self):
        return f"Subscription {self.id} for Vendor {self.vendor_id} - {self.status}"


class Payment(SQLModel, table=True):
    """
    Payment records for subscriptions
    """
    __tablename__ = "payments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Payment identification
    subscription_id: int = Field(foreign_key="subscriptions.id", description="Related subscription")
    vendor_id: int = Field(foreign_key="vendors.id", description="Vendor making payment")
    
    # Payment details
    amount: Decimal = Field(decimal_places=2, description="Payment amount")
    currency: str = Field(default="INR", max_length=3, description="Currency code")
    status: PaymentStatus = Field(default=PaymentStatus.PENDING, description="Payment status")
    
    # Payment method
    payment_method: PaymentMethod = Field(description="Payment method used")
    payment_method_details: dict = Field(default_factory=dict, sa_column=Column(JSON), description="Payment method details")
    
    # External payment tracking
    external_payment_id: Optional[str] = Field(default=None, max_length=100, description="External payment gateway ID")
    transaction_id: Optional[str] = Field(default=None, max_length=100, description="Transaction ID")
    
    # Payment timing
    payment_date: Optional[datetime] = Field(default=None, description="When payment was completed")
    due_date: Optional[datetime] = Field(default=None, description="Payment due date")
    
    # Billing period
    billing_period_start: datetime = Field(description="Billing period start")
    billing_period_end: datetime = Field(description="Billing period end")
    
    # Payment metadata
    payment_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON), description="Additional payment data")
    
    # Failure handling
    failure_reason: Optional[str] = Field(default=None, max_length=500, description="Reason for payment failure")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    
    # Relationships
    subscription: Optional["Subscription"] = Relationship(back_populates="payments")
    vendor: Optional["Vendor"] = Relationship()
    
    def __str__(self):
        return f"Payment {self.id} - ₹{self.amount} ({self.status})"


class UsageRecord(SQLModel, table=True):
    """
    Usage tracking for subscription features
    """
    __tablename__ = "usage_records"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Usage identification
    subscription_id: int = Field(foreign_key="subscriptions.id", description="Related subscription")
    vendor_id: int = Field(foreign_key="vendors.id", description="Vendor using the feature")
    
    # Usage details
    feature_name: str = Field(max_length=100, description="Feature being tracked")
    usage_count: int = Field(default=0, description="Current usage count")
    usage_limit: Optional[int] = Field(default=None, description="Usage limit for this feature")
    
    # Usage period
    period_start: datetime = Field(description="Usage tracking period start")
    period_end: datetime = Field(description="Usage tracking period end")
    
    # Usage metadata
    usage_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON), description="Additional usage data")
    
    # Relationships
    subscription: Optional["Subscription"] = Relationship(back_populates="usage_records")
    vendor: Optional["Vendor"] = Relationship()
    
    def is_limit_exceeded(self) -> bool:
        """Check if usage limit is exceeded"""
        if self.usage_limit is None:
            return False
        return self.usage_count >= self.usage_limit
    
    def usage_percentage(self) -> Optional[float]:
        """Get usage as percentage of limit"""
        if self.usage_limit is None:
            return None
        return (self.usage_count / self.usage_limit) * 100
    
    def __str__(self):
        return f"Usage {self.feature_name}: {self.usage_count}/{self.usage_limit or '∞'}"


class Invoice(SQLModel, table=True):
    """
    Invoice records for payments
    """
    __tablename__ = "invoices"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Invoice identification
    invoice_number: str = Field(unique=True, max_length=50, description="Unique invoice number")
    payment_id: int = Field(foreign_key="payments.id", description="Related payment")
    vendor_id: int = Field(foreign_key="vendors.id", description="Vendor for this invoice")
    
    # Invoice details
    subtotal: Decimal = Field(decimal_places=2, description="Subtotal amount")
    tax_amount: Decimal = Field(default=0, decimal_places=2, description="Tax amount")
    discount_amount: Decimal = Field(default=0, decimal_places=2, description="Discount amount")
    total_amount: Decimal = Field(decimal_places=2, description="Total amount")
    
    # Invoice dates
    invoice_date: datetime = Field(description="Invoice date")
    due_date: datetime = Field(description="Payment due date")
    
    # Invoice status
    is_paid: bool = Field(default=False, description="Whether invoice is paid")
    paid_date: Optional[datetime] = Field(default=None, description="Date when invoice was paid")
    
    # Invoice items
    line_items: List[dict] = Field(default_factory=list, sa_column=Column(JSON), description="Invoice line items")
    
    # Invoice metadata
    invoice_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON), description="Additional invoice data")
    
    # Relationships
    payment: Optional["Payment"] = Relationship()
    vendor: Optional["Vendor"] = Relationship()
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - ₹{self.total_amount}"


class BillingAddress(SQLModel, table=True):
    """
    Billing addresses for vendors
    """
    __tablename__ = "billing_addresses"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Address identification
    vendor_id: int = Field(foreign_key="vendors.id", description="Vendor who owns this address")
    
    # Address details
    company_name: str = Field(max_length=200, description="Company name")
    contact_person: str = Field(max_length=100, description="Contact person name")
    email: str = Field(max_length=100, description="Email address")
    phone: str = Field(max_length=20, description="Phone number")
    
    # Address
    address_line_1: str = Field(max_length=200, description="Address line 1")
    address_line_2: Optional[str] = Field(default=None, max_length=200, description="Address line 2")
    city: str = Field(max_length=100, description="City")
    state: str = Field(max_length=100, description="State")
    postal_code: str = Field(max_length=20, description="Postal code")
    country: str = Field(default="India", max_length=100, description="Country")
    
    # Tax details
    gstin: Optional[str] = Field(default=None, max_length=15, description="GST identification number")
    pan: Optional[str] = Field(default=None, max_length=10, description="PAN number")
    
    # Address settings
    is_default: bool = Field(default=False, description="Whether this is the default billing address")
    
    # Relationships
    vendor: Optional["Vendor"] = Relationship()
    
    def __str__(self):
        return f"Billing Address for {self.company_name}"
