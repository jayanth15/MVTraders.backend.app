"""
Integration tests for database functionality
"""
import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.models.user import User, UserType
from app.models.app_initialization import AppInitialization


class TestDatabaseIntegration:
    """Test database integration functionality"""
    
    def test_app_health_check(self, client: TestClient):
        """Test application health check"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "app_name" in data
        assert "version" in data
    
    def test_app_root_endpoint(self, client: TestClient):
        """Test application root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
    
    def test_database_initialization(self, test_session):
        """Test database initialization creates required tables"""
        # Check if User table exists and can be queried
        users = test_session.query(User).all()
        assert isinstance(users, list)
        
        # Check if AppInitialization table exists
        app_inits = test_session.query(AppInitialization).all()
        assert isinstance(app_inits, list)
    
    def test_model_relationships(self, test_session, super_admin_user, sample_organization):
        """Test model relationships work correctly"""
        from app.models.organization import OrganizationMember, OrganizationRole
        from app.models.vendor import Vendor, SubscriptionPlan
        from app.core.security import get_password_hash
        
        # Create a vendor user
        vendor_user = User(
            phone="9876543218",
            password_hash=get_password_hash("password123"),
            user_type=UserType.VENDOR
        )
        test_session.add(vendor_user)
        test_session.commit()
        test_session.refresh(vendor_user)
        
        # Create vendor
        vendor = Vendor(
            user_id=vendor_user.id,
            business_name="Relationship Test Store",
            business_address="Test Address",
            subscription_plan=SubscriptionPlan.BASIC,
            created_by=super_admin_user.id
        )
        test_session.add(vendor)
        test_session.commit()
        test_session.refresh(vendor)
        
        # Test relationship
        assert vendor.user == vendor_user
        assert vendor_user.vendor_profile == vendor
        
        # Create organization member
        member_user = User(
            phone="9876543219",
            password_hash=get_password_hash("password123"),
            user_type=UserType.ORGANIZATION_MEMBER
        )
        test_session.add(member_user)
        test_session.commit()
        test_session.refresh(member_user)
        
        member = OrganizationMember(
            user_id=member_user.id,
            organization_id=sample_organization.id,
            role=OrganizationRole.USER,
            created_by=super_admin_user.id
        )
        test_session.add(member)
        test_session.commit()
        test_session.refresh(member)
        
        # Test relationships
        assert member.user == member_user
        assert member.organization == sample_organization
        assert member in member_user.organization_memberships
        assert member in sample_organization.members
