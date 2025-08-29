"""
Authentication API endpoints
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.database import get_session
from app.core.auth import create_access_token, verify_password, get_password_hash
from app.core.deps import get_current_user, get_admin_user, get_super_admin_user
from app.models.user import User, UserType
from app.schemas.auth import (
    LoginRequest, 
    LoginResponse, 
    ChangePasswordRequest, 
    ChangePasswordResponse,
    ProfileUpdateRequest,
    UserCreateByAdmin,
    CreateUserResponse,
    UserProfileResponse
)
from app.config import settings


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.options("/login")
async def login_options():
    """Handle CORS preflight for login endpoint"""
    return {"message": "OK"}


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    session: Session = Depends(get_session)
):
    """
    Login with phone and password
    
    Args:
        login_data: Login credentials
        session: Database session
        
    Returns:
        JWT access token and user information
        
    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user by phone
    statement = select(User).where(User.phone == login_data.phone)
    user = session.exec(statement).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone or password"
        )
    
    # Verify password
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id), "phone": user.phone, "user_type": user.user_type.value},
        expires_delta=access_token_expires
    )
    
    # Prepare user data for response
    user_data = {
        "id": str(user.id),
        "phone": user.phone,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.full_name,
        "user_type": user.user_type.value,
        "profile_completed": user.profile_completed,
        "must_change_password": user.must_change_password
    }
    
    return LoginResponse(
        access_token=access_token,
        user=user_data,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Change user password
    
    Args:
        password_data: Current and new password
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If current password is incorrect
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.password_hash = get_password_hash(password_data.new_password)
    current_user.must_change_password = False
    current_user.password_changed_at = datetime.utcnow()
    
    session.add(current_user)
    session.commit()
    
    return ChangePasswordResponse(message="Password changed successfully")


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user profile
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User profile information
    """
    return UserProfileResponse(
        id=str(current_user.id),
        phone=current_user.phone,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        full_name=current_user.full_name,
        user_type=current_user.user_type,
        is_active=current_user.is_active,
        profile_completed=current_user.profile_completed,
        is_profile_complete=current_user.is_profile_complete,
        must_change_password=current_user.must_change_password,
        created_at=current_user.created_at.isoformat()
    )


@router.put("/profile", response_model=UserProfileResponse)
async def update_profile(
    profile_data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Update user profile
    
    Args:
        profile_data: Profile update data
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Updated user profile
    """
    # Update provided fields
    if profile_data.first_name is not None:
        current_user.first_name = profile_data.first_name
    if profile_data.last_name is not None:
        current_user.last_name = profile_data.last_name
    if profile_data.email is not None:
        current_user.email = profile_data.email
    
    # Update profile completion status
    current_user.profile_completed = current_user.is_profile_complete
    if current_user.profile_completed and not current_user.profile_completion_date:
        current_user.profile_completion_date = datetime.utcnow()
    
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    
    return UserProfileResponse(
        id=str(current_user.id),
        phone=current_user.phone,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        full_name=current_user.full_name,
        user_type=current_user.user_type,
        is_active=current_user.is_active,
        profile_completed=current_user.profile_completed,
        is_profile_complete=current_user.is_profile_complete,
        must_change_password=current_user.must_change_password,
        created_at=current_user.created_at.isoformat()
    )


@router.post("/admin/create-user", response_model=CreateUserResponse)
async def create_user_by_admin(
    user_data: UserCreateByAdmin,
    current_user: User = Depends(get_super_admin_user),
    session: Session = Depends(get_session)
):
    """
    Create a new user (Super admin only)
    
    Args:
        user_data: User creation data
        current_user: Current authenticated super admin
        session: Database session
        
    Returns:
        Created user information and temporary password
        
    Raises:
        HTTPException: If phone already exists or validation fails
    """
    # Check if phone already exists
    statement = select(User).where(User.phone == user_data.phone)
    existing_user = session.exec(statement).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )
    
    # Check if email already exists (if email is provided)
    if user_data.email:
        email_statement = select(User).where(User.email == user_data.email)
        existing_email_user = session.exec(email_statement).first()
        
        if existing_email_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email address '{user_data.email}' is already registered"
            )
    
    # Generate temporary password if not provided
    temp_password = user_data.temporary_password or "TempPass@123"
    
    try:
        # Create new user
        new_user = User(
            phone=user_data.phone,
            password_hash=get_password_hash(temp_password),
            user_type=user_data.user_type,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=user_data.email,
            username=user_data.username,
            is_active=True,
            is_default_login=False,
            must_change_password=True,
            created_by=current_user.id
        )
        
        # Set profile completion status
        new_user.profile_completed = new_user.is_profile_complete
        if new_user.profile_completed:
            new_user.profile_completion_date = datetime.utcnow()
        
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        
    except IntegrityError as e:
        session.rollback()
        error_msg = str(e.orig)
        
        if "UNIQUE constraint failed: users.email" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email address '{user_data.email}' is already registered"
            )
        elif "UNIQUE constraint failed: users.phone" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
        elif "UNIQUE constraint failed: users.username" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{user_data.username}' is already taken"
            )
        else:
            # Generic integrity error
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User creation failed due to constraint violation. Please check if email, phone, or username is already in use."
            )
    
    # Prepare user data for response
    user_response = {
        "id": str(new_user.id),
        "phone": new_user.phone,
        "username": new_user.username,
        "user_type": new_user.user_type.value,
        "full_name": new_user.full_name,
        "profile_completed": new_user.profile_completed
    }
    
    return CreateUserResponse(
        message="User created successfully",
        user=user_response,
        temporary_password=temp_password
    )


@router.get("/admin/users")
async def list_users(
    skip: int = 0,
    limit: int = 100,
    user_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """
    List all users (Admin only)
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        user_type: Filter by user type
        is_active: Filter by active status
        current_user: Current authenticated admin
        session: Database session
        
    Returns:
        List of users with basic information
    """
    
    # Build query
    query = select(User)
    
    # Apply filters
    if user_type:
        try:
            user_type_enum = UserType(user_type)
            query = query.where(User.user_type == user_type_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid user_type: {user_type}"
            )
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    # Execute query
    users = session.exec(query).all()
    
    # Format response
    user_list = []
    for user in users:
        user_data = {
            "id": str(user.id),
            "phone": user.phone,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "email": user.email,
            "user_type": user.user_type.value,
            "is_active": user.is_active,
            "profile_completed": user.profile_completed,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
        user_list.append(user_data)
    
    # Get total count for pagination
    count_query = select(User)
    if user_type:
        try:
            user_type_enum = UserType(user_type)
            count_query = count_query.where(User.user_type == user_type_enum)
        except ValueError:
            pass
    if is_active is not None:
        count_query = count_query.where(User.is_active == is_active)
    
    total_users = len(session.exec(count_query).all())
    
    return {
        "users": user_list,
        "total": total_users,
        "skip": skip,
        "limit": limit,
        "count": len(user_list)
    }
