"""
Unit tests for Organization model
"""
import pytest
from sqlmodel import Session

from app.models.organization import (
    Organization, 
    OrganizationMember, 
    OrganizationRole,
    VerificationStatus,
    OrganizationCreate,
    OrganizationUpdate
)
from app.models.user import User, UserType
from app.core.security import get_password_hash


class TestOrganizationModel:
    """Test Organization model functionality"""
    
    def test_create_organization(self, test_session: Session, super_admin_user):
        """Test organization creation"""
        org = Organization(
            name="Test Company",
            description="A test company",
            phone="9876543210",
            email="contact@testcompany.com",
            industry="Technology",
            employee_count=100,
            annual_revenue=5000000.00,
            credit_limit=100000.00,
            created_by=super_admin_user.id
        )
        
        test_session.add(org)
        test_session.commit()
        test_session.refresh(org)
        
        assert org.id is not None
        assert org.name == "Test Company"
        assert org.phone == "9876543210"
        assert org.verification_status == VerificationStatus.PENDING
        assert org.is_active is True
        assert org.created_by == super_admin_user.id
    
    def test_organization_verification_status(self, test_session: Session, super_admin_user):
        """Test organization verification status"""
        org = Organization(
            name="Verified Company",
            verification_status=VerificationStatus.VERIFIED,
            created_by=super_admin_user.id
        )
        
        test_session.add(org)
        test_session.commit()
        
        assert org.verification_status == VerificationStatus.VERIFIED
        assert org.is_verified is False  # Only set to True explicitly
    
    def test_organization_member_creation(self, test_session: Session, sample_organization):
        """Test organization member creation"""
        # Create a user first
        user = User(
            phone="9876543211",
            password_hash=get_password_hash("password123"),
            first_name="Member",
            last_name="User",
            email="member@example.com",
            user_type=UserType.ORGANIZATION_MEMBER
        )
        test_session.add(user)
        test_session.commit()
        test_session.refresh(user)
        
        # Create organization member
        member = OrganizationMember(
            user_id=user.id,
            organization_id=sample_organization.id,
            role=OrganizationRole.USER,
            department="Engineering",
            employee_id="EMP001",
            created_by=user.id
        )
        
        test_session.add(member)
        test_session.commit()
        test_session.refresh(member)
        
        assert member.id is not None
        assert member.user_id == user.id
        assert member.organization_id == sample_organization.id
        assert member.role == OrganizationRole.USER
        assert member.department == "Engineering"
        assert member.is_active is True
    
    def test_organization_member_roles(self, test_session: Session, sample_organization):
        """Test different organization member roles"""
        roles = [
            OrganizationRole.SUPER_ADMIN,
            OrganizationRole.ADMIN,
            OrganizationRole.USER
        ]
        
        for i, role in enumerate(roles):
            # Create user
            user = User(
                phone=f"987654321{i}",
                password_hash=get_password_hash("password123"),
                user_type=UserType.ORGANIZATION_MEMBER
            )
            test_session.add(user)
            test_session.commit()
            test_session.refresh(user)
            
            # Create member with specific role
            member = OrganizationMember(
                user_id=user.id,
                organization_id=sample_organization.id,
                role=role,
                created_by=user.id
            )
            test_session.add(member)
        
        test_session.commit()
        
        # Verify all members were created
        members = test_session.query(OrganizationMember).all()
        assert len(members) == len(roles)


class TestOrganizationSchemas:
    """Test Organization Pydantic schemas"""
    
    def test_organization_create_schema(self):
        """Test OrganizationCreate schema validation"""
        org_data = OrganizationCreate(
            name="New Company",
            description="A new company",
            phone="9876543210",
            email="contact@newcompany.com",
            industry="Healthcare",
            employee_count=50,
            annual_revenue=2000000.00,
            credit_limit=50000.00
        )
        
        assert org_data.name == "New Company"
        assert org_data.phone == "9876543210"
        assert org_data.employee_count == 50
    
    def test_organization_create_invalid_phone(self):
        """Test OrganizationCreate with invalid phone"""
        with pytest.raises(ValueError):
            OrganizationCreate(
                name="Company",
                phone="123456789"  # Invalid phone
            )
    
    def test_organization_update_schema(self):
        """Test OrganizationUpdate schema"""
        update_data = OrganizationUpdate(
            name="Updated Company",
            employee_count=75,
            credit_limit=75000.00
        )
        
        assert update_data.name == "Updated Company"
        assert update_data.employee_count == 75
        assert update_data.credit_limit == 75000.00
    
    def test_organization_update_validation(self):
        """Test OrganizationUpdate validation"""
        # Test negative values
        with pytest.raises(ValueError):
            OrganizationUpdate(employee_count=-1)
        
        with pytest.raises(ValueError):
            OrganizationUpdate(credit_limit=-100.00)
        
        with pytest.raises(ValueError):
            OrganizationUpdate(annual_revenue=-1000.00)
