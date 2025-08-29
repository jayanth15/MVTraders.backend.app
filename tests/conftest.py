"""
Test configuration and fixtures
"""
import pytest
import tempfile
import os
from typing import Generator
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_session
from app.config import settings


@pytest.fixture(scope="session")
def temp_db():
    """Create a temporary database file for testing"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_file.close()
    yield temp_file.name
    try:
        os.unlink(temp_file.name)
    except (PermissionError, FileNotFoundError):
        # Windows may have file handle still open, skip cleanup
        pass


@pytest.fixture(scope="function")
def test_engine(temp_db):
    """Create test database engine"""
    engine = create_engine(
        f"sqlite:///{temp_db}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine


@pytest.fixture(scope="function")
def test_session(test_engine) -> Generator[Session, None, None]:
    """Create test database session"""
    from app.models import BaseModel
    
    # Create all tables
    BaseModel.metadata.create_all(test_engine)
    
    with Session(test_engine) as session:
        yield session


@pytest.fixture(scope="function")
def client(test_session: Session) -> Generator[TestClient, None, None]:
    """Create test client with test database"""
    def get_test_session():
        return test_session
    
    app.dependency_overrides[get_session] = get_test_session
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def super_admin_user(test_session: Session):
    """Create a super admin user for testing"""
    from app.models.user import User, UserType
    from app.core.security import get_password_hash
    
    user = User(
        phone="9999999999",
        username="testadmin",
        password_hash=get_password_hash("testpass123"),
        first_name="Test",
        last_name="Admin",
        email="test@example.com",
        user_type=UserType.APP_SUPER_ADMIN,
        profile_completed=True,
        is_default_login=False,
        must_change_password=False,
        is_active=True
    )
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    return user


@pytest.fixture
def sample_organization(test_session: Session, super_admin_user):
    """Create a sample organization for testing"""
    from app.models.organization import Organization, VerificationStatus
    
    org = Organization(
        name="Test Organization",
        description="A test organization",
        phone="9876543210",
        email="org@example.com",
        industry="Technology",
        employee_count=50,
        annual_revenue=1000000.00,
        credit_limit=50000.00,
        is_active=True,
        verification_status=VerificationStatus.VERIFIED,
        created_by=super_admin_user.id
    )
    test_session.add(org)
    test_session.commit()
    test_session.refresh(org)
    return org
