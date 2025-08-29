"""
App initialization model
"""
from datetime import datetime
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import String

from app.models.base import BaseModel


class AppInitialization(BaseModel, table=True):
    """App initialization tracking"""
    __tablename__ = "app_initialization"
    
    app_version: str = Field(
        sa_column=Column(String(50), nullable=False),
        description="Application version"
    )
    default_super_admin_created: bool = Field(
        default=False,
        description="Default super admin creation status"
    )
    default_username: str = Field(
        sa_column=Column(String(100), nullable=False),
        description="Default super admin username"
    )
    default_password_hash: str = Field(
        sa_column=Column(String(255), nullable=False),
        description="Default super admin password hash"
    )
    initialization_date: datetime = Field(
        default_factory=datetime.utcnow,
        description="Initialization timestamp"
    )
    is_initialized: bool = Field(
        default=False,
        description="Initialization completion status"
    )
