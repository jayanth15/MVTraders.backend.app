"""
Authentication dependencies for FastAPI
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from app.database import get_session
from app.core.auth import verify_token
from app.models.user import User, UserType


# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session)
) -> User:
    """
    Get current authenticated user from JWT token
    
    Args:
        credentials: HTTP Bearer credentials
        session: Database session
        
    Returns:
        Current authenticated user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verify token
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise credentials_exception
    
    # Get user ID from token
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # Find user in database
    user = session.get(User, user_id)
    if user is None:
        raise credentials_exception
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (alias for get_current_user)
    """
    return current_user


async def get_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user with admin privileges
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user if admin
        
    Raises:
        HTTPException: If user is not admin
    """
    if current_user.user_type not in [UserType.APP_ADMIN, UserType.APP_SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require admin privileges (alias for get_admin_user)
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user if admin
        
    Raises:
        HTTPException: If user is not admin
    """
    return await get_admin_user(current_user)


async def get_super_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user with super admin privileges
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user if super admin
        
    Raises:
        HTTPException: If user is not super admin
    """
    if current_user.user_type != UserType.APP_SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required"
        )
    return current_user


def require_profile_completion(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require user to have completed profile
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user if profile is complete
        
    Raises:
        HTTPException: If profile is not complete
    """
    if not current_user.is_profile_complete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile completion required. Please update your first name, last name, and email."
        )
    return current_user


async def require_vendor(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get vendor associated with current user
    
    Args:
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Vendor associated with the user
        
    Raises:
        HTTPException: If user has no associated vendor
    """
    from app.models.vendor import Vendor
    
    vendor = session.query(Vendor).filter(Vendor.user_id == current_user.id).first()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No vendor profile found for this user"
        )
    
    return vendor
