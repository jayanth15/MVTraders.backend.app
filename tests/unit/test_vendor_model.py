"""
Unit tests for Vendor model
"""
import pytest
from decimal import Decimal
from sqlmodel import Session

from app.models.vendor import (
    Vendor,
    SubscriptionPlan,
    SubscriptionStatus,
    VendorCreate,
    VendorUpdate
)
from app.models.user import User, UserType
from app.models.organization import VerificationStatus
from app.core.security import get_password_hash


class TestVendorModel:
    """Test Vendor model functionality"""
    
    def test_create_vendor(self, test_session: Session, super_admin_user):
        """Test vendor creation"""
        # Create vendor user first
        vendor_user = User(
            phone="9876543212",
            password_hash=get_password_hash("password123"),
            first_name="Vendor",
            last_name="Owner",
            email="vendor@example.com",
            user_type=UserType.VENDOR
        )
        test_session.add(vendor_user)
        test_session.commit()
        test_session.refresh(vendor_user)
        
        # Create vendor
        vendor = Vendor(
            user_id=vendor_user.id,
            business_name="Test Electronics Store",
            business_description="Electronics and gadgets store",
            business_address="123 Main Street, City, State",
            business_phone="9876543213",
            business_email="store@electronics.com",
            subscription_plan=SubscriptionPlan.PREMIUM,
            monthly_fee=Decimal('999.00'),
            created_by=super_admin_user.id
        )
        
        test_session.add(vendor)
        test_session.commit()
        test_session.refresh(vendor)
        
        assert vendor.id is not None
        assert vendor.user_id == vendor_user.id
        assert vendor.business_name == "Test Electronics Store"
        assert vendor.subscription_plan == SubscriptionPlan.PREMIUM
        assert vendor.monthly_fee == Decimal('999.00')
        assert vendor.verification_status == VerificationStatus.PENDING
        assert vendor.is_active is True
    
    def test_vendor_subscription_plans(self, test_session: Session, super_admin_user):
        """Test different subscription plans"""
        plans = [
            (SubscriptionPlan.BASIC, Decimal('499.00')),
            (SubscriptionPlan.PREMIUM, Decimal('999.00')),
            (SubscriptionPlan.ENTERPRISE, Decimal('1999.00'))
        ]
        
        for i, (plan, fee) in enumerate(plans):
            # Create vendor user
            vendor_user = User(
                phone=f"987654321{i+2}",
                password_hash=get_password_hash("password123"),
                user_type=UserType.VENDOR
            )
            test_session.add(vendor_user)
            test_session.commit()
            test_session.refresh(vendor_user)
            
            # Create vendor with specific plan
            vendor = Vendor(
                user_id=vendor_user.id,
                business_name=f"Store {i+1}",
                business_address="Test Address",
                subscription_plan=plan,
                monthly_fee=fee,
                created_by=super_admin_user.id
            )
            test_session.add(vendor)
        
        test_session.commit()
        
        # Verify all vendors were created
        vendors = test_session.query(Vendor).all()
        assert len(vendors) == len(plans)
    
    def test_vendor_subscription_status(self, test_session: Session, super_admin_user):
        """Test vendor subscription status"""
        # Create vendor user
        vendor_user = User(
            phone="9876543215",
            password_hash=get_password_hash("password123"),
            user_type=UserType.VENDOR
        )
        test_session.add(vendor_user)
        test_session.commit()
        test_session.refresh(vendor_user)
        
        vendor = Vendor(
            user_id=vendor_user.id,
            business_name="Active Store",
            business_address="Test Address",
            subscription_status=SubscriptionStatus.ACTIVE,
            created_by=super_admin_user.id
        )
        
        test_session.add(vendor)
        test_session.commit()
        
        assert vendor.subscription_status == SubscriptionStatus.ACTIVE
    
    def test_vendor_performance_metrics(self, test_session: Session, super_admin_user):
        """Test vendor performance metrics"""
        # Create vendor user
        vendor_user = User(
            phone="9876543216",
            password_hash=get_password_hash("password123"),
            user_type=UserType.VENDOR
        )
        test_session.add(vendor_user)
        test_session.commit()
        test_session.refresh(vendor_user)
        
        vendor = Vendor(
            user_id=vendor_user.id,
            business_name="Performance Store",
            business_address="Test Address",
            total_orders=100,
            on_time_delivery_rate=Decimal('95.50'),
            order_fulfillment_rate=Decimal('98.00'),
            created_by=super_admin_user.id
        )
        
        test_session.add(vendor)
        test_session.commit()
        test_session.refresh(vendor)
        
        assert vendor.total_orders == 100
        assert vendor.on_time_delivery_rate == Decimal('95.50')
        assert vendor.order_fulfillment_rate == Decimal('98.00')


class TestVendorSchemas:
    """Test Vendor Pydantic schemas"""
    
    def test_vendor_create_schema(self, super_admin_user):
        """Test VendorCreate schema validation"""
        vendor_data = VendorCreate(
            user_id=super_admin_user.id,
            business_name="New Electronics Store",
            business_description="Latest electronics and gadgets",
            business_address="456 Commerce Street, Business District",
            business_phone="9876543217",
            business_email="contact@newstore.com",
            subscription_plan=SubscriptionPlan.BASIC,
            monthly_fee=Decimal('499.00')
        )
        
        assert vendor_data.business_name == "New Electronics Store"
        assert vendor_data.subscription_plan == SubscriptionPlan.BASIC
        assert vendor_data.monthly_fee == Decimal('499.00')
    
    def test_vendor_create_invalid_phone(self, super_admin_user):
        """Test VendorCreate with invalid phone"""
        with pytest.raises(ValueError):
            VendorCreate(
                user_id=super_admin_user.id,
                business_name="Store",
                business_address="Address",
                business_phone="123456789"  # Invalid phone
            )
    
    def test_vendor_create_short_address(self, super_admin_user):
        """Test VendorCreate with short address"""
        with pytest.raises(ValueError):
            VendorCreate(
                user_id=super_admin_user.id,
                business_name="Store",
                business_address="Short"  # Too short
            )
    
    def test_vendor_update_schema(self):
        """Test VendorUpdate schema"""
        update_data = VendorUpdate(
            business_name="Updated Store Name",
            business_description="Updated description",
            subscription_plan=SubscriptionPlan.PREMIUM,
            monthly_fee=Decimal('999.00')
        )
        
        assert update_data.business_name == "Updated Store Name"
        assert update_data.subscription_plan == SubscriptionPlan.PREMIUM
        assert update_data.monthly_fee == Decimal('999.00')
    
    def test_vendor_update_validation(self):
        """Test VendorUpdate validation"""
        # Test negative monthly fee
        with pytest.raises(ValueError):
            VendorUpdate(monthly_fee=Decimal('-100.00'))
        
        # Test short business name
        with pytest.raises(ValueError):
            VendorUpdate(business_name="A")  # Too short
