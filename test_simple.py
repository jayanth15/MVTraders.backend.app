"""
Simple test to check if basic SQLModel works
"""
from sqlmodel import SQLModel, Field, create_engine
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import Column, DateTime, func


class SimpleUser(SQLModel, table=True):
    """Simple user model for testing"""
    __tablename__ = "simple_users"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    phone: str = Field(max_length=10)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )


if __name__ == "__main__":
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    print("Simple model creation successful!")
