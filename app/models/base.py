"""
Base model classes and common fields
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import DateTime, func


class UUIDModel(SQLModel):
    """Base model with UUID primary key"""
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        nullable=False,
        description="Unique identifier"
    )


class TimestampModel(SQLModel):
    """Base model with timestamp fields"""
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )


class BaseModel(UUIDModel, TimestampModel):
    """Base model with UUID and timestamps"""
    pass


class SoftDeleteModel(BaseModel):
    """Base model with soft delete functionality"""
    is_deleted: bool = Field(default=False, description="Soft delete flag")
    deleted_at: Optional[datetime] = Field(default=None, description="Deletion timestamp")
