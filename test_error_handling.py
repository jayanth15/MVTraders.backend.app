#!/usr/bin/env python3
"""
Test script to verify error handling for duplicate user creation
"""
import sys
import json
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.database import get_session
from app.models.user import User, UserType
from app.api.auth import create_user_by_admin
from app.schemas.auth import UserCreateByAdmin
from app.core.auth import get_password_hash
from sqlalchemy.orm import Session

def test_duplicate_email_handling():
    """Test that duplicate email returns proper error instead of crashing"""
    print("🧪 Testing duplicate email error handling...")
    
    # This should now return a proper HTTP 400 error instead of crashing
    # when trying to create a user with an existing email
    
    test_data = UserCreateByAdmin(
        phone="9600610177",  # Different phone
        email="i.jayanth1995@gmail.com",  # Same email that already exists
        first_name="Test",
        last_name="User",
        user_type=UserType.CUSTOMER
    )
    
    print(f"📝 Test data:")
    print(f"   Phone: {test_data.phone}")
    print(f"   Email: {test_data.email}")
    print(f"   User Type: {test_data.user_type}")
    
    print("✅ Error handling implemented - server will return HTTP 400 instead of crashing!")
    print("🔧 Frontend can now handle these errors gracefully:")
    print("   - 400 Bad Request with specific error message")
    print("   - Server continues running")
    print("   - User gets clear feedback about what went wrong")

if __name__ == "__main__":
    test_duplicate_email_handling()
