"""
Order form models for vendor customizable order forms
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from uuid import UUID
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import String, Text, JSON, Boolean

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.vendor import Vendor
    from app.models.order import Order


class FieldType(str, Enum):
    """Form field type enumeration"""
    TEXT = "text"
    EMAIL = "email"
    PHONE = "phone"
    NUMBER = "number"
    TEXTAREA = "textarea"
    SELECT = "select"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    DATE = "date"
    DATETIME = "datetime"
    FILE = "file"
    URL = "url"
    PASSWORD = "password"


class ValidationRule(str, Enum):
    """Validation rule enumeration"""
    REQUIRED = "required"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    MIN_VALUE = "min_value"
    MAX_VALUE = "max_value"
    PATTERN = "pattern"
    EMAIL_FORMAT = "email_format"
    PHONE_FORMAT = "phone_format"
    URL_FORMAT = "url_format"


class OrderForm(BaseModel, table=True):
    """Order form model for vendor customizable forms"""
    __tablename__ = "order_forms"
    
    # Form identification
    vendor_id: UUID = Field(
        foreign_key="vendors.id",
        description="Vendor who owns this form"
    )
    name: str = Field(
        sa_column=Column(String(255), nullable=False),
        description="Form name"
    )
    description: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Form description"
    )
    
    # Form structure
    fields: List[Dict[str, Any]] = Field(
        sa_column=Column(JSON, nullable=False),
        description="Form fields configuration"
    )
    
    # Form settings
    is_active: bool = Field(
        default=True,
        description="Form active status"
    )
    is_default: bool = Field(
        default=False,
        description="Default form for vendor"
    )
    require_approval: bool = Field(
        default=True,
        description="Orders using this form require approval"
    )
    
    # Form metadata
    version: int = Field(
        default=1,
        description="Form version number"
    )
    instructions: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Instructions for customers"
    )
    terms_and_conditions: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Terms and conditions text"
    )
    
    # Usage statistics
    submission_count: int = Field(
        default=0,
        description="Number of submissions"
    )
    last_used_at: Optional[datetime] = Field(
        default=None,
        description="Last submission timestamp"
    )
    
    # Admin controls
    created_by: UUID = Field(
        foreign_key="users.id",
        description="User who created this form"
    )
    approved_by: Optional[UUID] = Field(
        default=None,
        foreign_key="users.id",
        description="Admin who approved this form"
    )
    approved_at: Optional[datetime] = Field(
        default=None,
        description="Form approval timestamp"
    )
    is_approved: bool = Field(
        default=False,
        description="Form approval status"
    )
    
    # Relationships (temporarily disabled for Phase 4 setup)
    # vendor: "Vendor" = Relationship(back_populates="order_forms")
    # orders: List["Order"] = Relationship(back_populates="order_form")


class FormSubmission(BaseModel, table=True):
    """Form submission model for tracking form usage"""
    __tablename__ = "form_submissions"
    
    # Submission identification
    order_form_id: UUID = Field(
        foreign_key="order_forms.id",
        description="Form that was submitted"
    )
    order_id: Optional[UUID] = Field(
        default=None,
        foreign_key="orders.id",
        description="Order created from this submission"
    )
    
    # Submitter information
    submitted_by: UUID = Field(
        foreign_key="users.id",
        description="User who submitted the form"
    )
    organization_id: Optional[UUID] = Field(
        default=None,
        foreign_key="organizations.id",
        description="Organization context for submission"
    )
    
    # Submission data
    form_data: Dict[str, Any] = Field(
        sa_column=Column(JSON, nullable=False),
        description="Submitted form data"
    )
    submission_status: str = Field(
        sa_column=Column(String(50), nullable=False),
        default="submitted",
        description="Submission status (submitted, processed, rejected)"
    )
    
    # Submission metadata
    ip_address: Optional[str] = Field(
        sa_column=Column(String(45)),
        default=None,
        description="IP address of submitter"
    )
    user_agent: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="User agent string"
    )
    
    # Processing information
    processed_by: Optional[UUID] = Field(
        default=None,
        foreign_key="users.id",
        description="User who processed this submission"
    )
    processed_at: Optional[datetime] = Field(
        default=None,
        description="Processing timestamp"
    )
    processing_notes: Optional[str] = Field(
        sa_column=Column(Text),
        default=None,
        description="Notes from processing"
    )


# Pydantic schemas for form field configuration
class FormFieldOption(SQLModel):
    """Form field option schema"""
    label: str
    value: str
    selected: bool = False


class FormFieldValidation(SQLModel):
    """Form field validation schema"""
    rule: ValidationRule
    value: Optional[Any] = None
    message: Optional[str] = None


class FormFieldSchema(SQLModel):
    """Form field configuration schema"""
    id: str  # Unique field ID within the form
    type: FieldType
    label: str
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    default_value: Optional[Any] = None
    required: bool = False
    readonly: bool = False
    
    # Field-specific configurations
    options: Optional[List[FormFieldOption]] = None  # For select, radio, checkbox
    validations: Optional[List[FormFieldValidation]] = None
    
    # Layout and styling
    css_class: Optional[str] = None
    grid_column: Optional[int] = None
    grid_row: Optional[int] = None
    
    # Conditional logic
    conditional_logic: Optional[Dict[str, Any]] = None


# API schemas
class OrderFormRead(SQLModel):
    """Order form read schema"""
    id: UUID
    vendor_id: UUID
    name: str
    description: Optional[str] = None
    fields: List[Dict[str, Any]]
    is_active: bool
    is_default: bool
    require_approval: bool
    version: int
    instructions: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    submission_count: int
    last_used_at: Optional[datetime] = None
    is_approved: bool
    created_at: datetime


class OrderFormCreate(SQLModel):
    """Order form creation schema"""
    name: str = Field(min_length=2, max_length=255)
    description: Optional[str] = None
    fields: List[FormFieldSchema] = Field(min_items=1)
    is_active: bool = Field(default=True)
    is_default: bool = Field(default=False)
    require_approval: bool = Field(default=True)
    instructions: Optional[str] = None
    terms_and_conditions: Optional[str] = None


class OrderFormUpdate(SQLModel):
    """Order form update schema"""
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    fields: Optional[List[FormFieldSchema]] = Field(default=None, min_items=1)
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    require_approval: Optional[bool] = None
    instructions: Optional[str] = None
    terms_and_conditions: Optional[str] = None


class FormSubmissionRead(SQLModel):
    """Form submission read schema"""
    id: UUID
    order_form_id: UUID
    order_id: Optional[UUID] = None
    submitted_by: UUID
    organization_id: Optional[UUID] = None
    form_data: Dict[str, Any]
    submission_status: str
    processed_by: Optional[UUID] = None
    processed_at: Optional[datetime] = None
    processing_notes: Optional[str] = None
    created_at: datetime


class FormSubmissionCreate(SQLModel):
    """Form submission creation schema"""
    order_form_id: UUID
    organization_id: Optional[UUID] = None
    form_data: Dict[str, Any]


class FormSubmissionUpdate(SQLModel):
    """Form submission update schema"""
    submission_status: str
    processing_notes: Optional[str] = None


class OrderFormApproval(SQLModel):
    """Order form approval schema"""
    is_approved: bool
    approval_notes: Optional[str] = None
