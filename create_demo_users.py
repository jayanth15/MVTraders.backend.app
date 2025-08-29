#!/usr/bin/env python3
"""
Demo Users Setup Script for MvTraders
Creates test users for all user types with known credentials for testing
"""

import sys
import os
sys.path.append('.')

from sqlalchemy.orm import Session
from app.database import get_db, engine
from app.models.user import User
from app.models.vendor import Vendor
from app.models.organization import Organization
from app.core.security import get_password_hash
from datetime import datetime

def create_demo_users():
    """Create demo users for testing all user types"""
    
    # Get database session
    db = next(get_db())
    
    try:
        print("🚀 Creating Demo Users for MvTraders...")
        print("=" * 50)
        
        # Demo user data
        demo_users = [
            {
                "phone": "9999999999",
                "password": "admin123",
                "user_type": "super_admin",
                "first_name": "Super",
                "last_name": "Admin",
                "email": "admin@mvtraders.com",
                "is_active": True,
                "is_verified": True
            },
            {
                "phone": "9876543210",
                "password": "customer123",
                "user_type": "customer",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.customer@gmail.com",
                "is_active": True,
                "is_verified": True
            },
            {
                "phone": "9876543211",
                "password": "vendor123",
                "user_type": "vendor",
                "first_name": "Raj",
                "last_name": "Sharma",
                "email": "raj@sharmahardware.com",
                "is_active": True,
                "is_verified": True
            },
            {
                "phone": "9876543212",
                "password": "org123",
                "user_type": "organization",
                "first_name": "Priya",
                "last_name": "Patel",
                "email": "priya@techcorp.com",
                "is_active": True,
                "is_verified": True
            }
        ]
        
        created_users = []
        
        for user_data in demo_users:
            # Check if user already exists
            existing_user = db.query(User).filter(User.phone == user_data["phone"]).first()
            if existing_user:
                print(f"⚠️  User with phone {user_data['phone']} already exists. Skipping...")
                created_users.append(existing_user)
                continue
            
            # Create new user
            hashed_password = get_password_hash(user_data["password"])
            
            new_user = User(
                phone=user_data["phone"],
                hashed_password=hashed_password,
                user_type=user_data["user_type"],
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                email=user_data["email"],
                is_active=user_data["is_active"],
                is_verified=user_data["is_verified"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(new_user)
            db.flush()  # Flush to get the ID
            created_users.append(new_user)
            
            print(f"✅ Created {user_data['user_type'].upper()}: {user_data['first_name']} {user_data['last_name']} ({user_data['phone']})")
        
        # Create vendor profile for vendor user
        vendor_user = next((u for u in created_users if u.user_type == "vendor"), None)
        if vendor_user:
            existing_vendor = db.query(Vendor).filter(Vendor.user_id == vendor_user.id).first()
            if not existing_vendor:
                vendor_profile = Vendor(
                    user_id=vendor_user.id,
                    business_name="Sharma Hardware Industries",
                    business_type="Manufacturer",
                    description="Leading manufacturer of industrial hardware with 15+ years of experience",
                    contact_person="Raj Sharma",
                    email="raj@sharmahardware.com",
                    phone="9876543211",
                    address="Industrial Area, Phase 2, Chandigarh, Punjab",
                    city="Chandigarh",
                    state="Punjab",
                    pincode="160002",
                    country="India",
                    is_verified=True,
                    subscription_tier="premium",
                    status="approved",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(vendor_profile)
                print(f"✅ Created vendor profile for: {vendor_profile.business_name}")
        
        # Create organization profile for organization user
        org_user = next((u for u in created_users if u.user_type == "organization"), None)
        if org_user:
            existing_org = db.query(Organization).filter(Organization.user_id == org_user.id).first()
            if not existing_org:
                org_profile = Organization(
                    user_id=org_user.id,
                    name="TechCorp Solutions Pvt Ltd",
                    org_type="private_company",
                    description="Technology solutions provider for enterprise clients",
                    contact_person="Priya Patel",
                    email="priya@techcorp.com",
                    phone="9876543212",
                    address="Tech Park, Sector 18, Gurgaon, Haryana",
                    city="Gurgaon",
                    state="Haryana",
                    pincode="122015",
                    country="India",
                    is_verified=True,
                    subscription_tier="enterprise",
                    status="approved",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(org_profile)
                print(f"✅ Created organization profile for: {org_profile.name}")
        
        # Commit all changes
        db.commit()
        
        print("\n" + "=" * 50)
        print("🎉 Demo Users Created Successfully!")
        print("=" * 50)
        
        print("\n📋 LOGIN CREDENTIALS:")
        print("-" * 30)
        
        for user_data in demo_users:
            user = next((u for u in created_users if u.phone == user_data["phone"]), None)
            if user:
                print(f"\n👤 {user_data['user_type'].upper().replace('_', ' ')}")
                print(f"   📱 Phone: {user_data['phone']}")
                print(f"   🔑 Password: {user_data['password']}")
                print(f"   👨‍💼 Name: {user_data['first_name']} {user_data['last_name']}")
                print(f"   📧 Email: {user_data['email']}")
        
        print("\n" + "=" * 50)
        print("🚀 Ready to test! You can now login with any of these accounts.")
        print("💡 Tip: Use the phone number and password to login through the frontend.")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Error creating demo users: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    create_demo_users()
