"""
Integration tests for authentication API
"""
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.models.user import User, UserType
from app.core.auth import get_password_hash


class TestAuthAPI:
    """Test authentication API endpoints"""
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_login_invalid_phone(self):
        """Test login with invalid phone"""
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/login",
            json={"phone": "1234567890", "password": "password123"}
        )
        assert response.status_code == 401
        assert "Incorrect phone or password" in response.json()["detail"]
    
    def test_login_valid_user(self, test_session: Session):
        """Test login with valid user"""
        # Create a test user first
        test_user = User(
            phone="9876543210",
            password_hash=get_password_hash("password123"),
            first_name="Test",
            last_name="User",
            email="test@example.com",
            user_type=UserType.CUSTOMER,
            is_active=True,
            profile_completed=True,
            is_default_login=False,
            must_change_password=False
        )
        test_session.add(test_user)
        test_session.commit()
        
        # Test login
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/login",
            json={"phone": "9876543210", "password": "password123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["phone"] == "9876543210"
        assert data["user"]["full_name"] == "Test User"
        assert data["user"]["user_type"] == "customer"
    
    def test_login_inactive_user(self, test_session: Session):
        """Test login with inactive user"""
        # Create inactive test user
        test_user = User(
            phone="8876543210",
            password_hash=get_password_hash("password123"),
            user_type=UserType.CUSTOMER,
            is_active=False  # Inactive user
        )
        test_session.add(test_user)
        test_session.commit()
        
        # Test login
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/login",
            json={"phone": "8876543210", "password": "password123"}
        )
        
        assert response.status_code == 401
        assert "Account is disabled" in response.json()["detail"]
    
    def test_get_profile_without_token(self):
        """Test getting profile without authentication"""
        client = TestClient(app)
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
    
    def test_get_profile_with_token(self, test_session: Session):
        """Test getting profile with valid token"""
        # Create test user
        test_user = User(
            phone="7876543210",
            password_hash=get_password_hash("password123"),
            first_name="Profile",
            last_name="User",
            email="profile@example.com",
            user_type=UserType.CUSTOMER,
            is_active=True
        )
        test_session.add(test_user)
        test_session.commit()
        
        # Login to get token
        client = TestClient(app)
        login_response = client.post(
            "/api/v1/auth/login",
            json={"phone": "7876543210", "password": "password123"}
        )
        
        token = login_response.json()["access_token"]
        
        # Get profile
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == "7876543210"
        assert data["full_name"] == "Profile User"
        assert data["user_type"] == "customer"
    
    def test_update_profile(self, test_session: Session):
        """Test updating user profile"""
        # Create test user
        test_user = User(
            phone="6876543210",
            password_hash=get_password_hash("password123"),
            user_type=UserType.CUSTOMER,
            is_active=True
        )
        test_session.add(test_user)
        test_session.commit()
        
        # Login to get token
        client = TestClient(app)
        login_response = client.post(
            "/api/v1/auth/login",
            json={"phone": "6876543210", "password": "password123"}
        )
        
        token = login_response.json()["access_token"]
        
        # Update profile
        response = client.put(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "first_name": "Updated",
                "last_name": "Name",
                "email": "updated@example.com"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"
        assert data["email"] == "updated@example.com"
        assert data["full_name"] == "Updated Name"
        assert data["is_profile_complete"] is True
