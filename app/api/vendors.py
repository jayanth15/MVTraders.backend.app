"""
Vendor management API endpoints
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.deps import get_session, get_current_user, get_admin_user, get_super_admin_user
from app.models import (
    User, Vendor, VendorRead, VendorCreate, VendorUpdate,
    SubscriptionPlan, SubscriptionStatus, VerificationStatus
)

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.post("/", response_model=VendorRead, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    vendor_data: VendorCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_super_admin_user)
):
    """Create a new vendor (Super Admin only)"""
    
    # Check if user already has a vendor profile
    existing_vendor = db.exec(
        select(Vendor).where(Vendor.user_id == vendor_data.user_id)
    ).first()
    if existing_vendor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a vendor profile"
        )
    
    # Check if user exists
    user = db.exec(select(User).where(User.id == vendor_data.user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Create vendor
    vendor = Vendor(
        **vendor_data.model_dump(),
        created_by=current_user.id,
        subscription_status=SubscriptionStatus.PENDING,
        verification_status=VerificationStatus.PENDING
    )
    
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    
    return vendor


@router.get("/", response_model=List[VendorRead])
async def list_vendors(
    skip: int = 0,
    limit: int = 100,
    is_verified: Optional[bool] = None,
    is_active: Optional[bool] = None,
    subscription_plan: Optional[SubscriptionPlan] = None,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_admin_user)
):
    """List vendors with filtering (Admin only)"""
    
    query = select(Vendor)
    
    if is_verified is not None:
        query = query.where(Vendor.is_verified == is_verified)
    if is_active is not None:
        query = query.where(Vendor.is_active == is_active)
    if subscription_plan:
        query = query.where(Vendor.subscription_plan == subscription_plan)
    
    vendors = db.exec(query.offset(skip).limit(limit)).all()
    return vendors


@router.get("/{vendor_id}", response_model=VendorRead)
async def get_vendor(
    vendor_id: UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get vendor by ID"""
    
    vendor = db.exec(select(Vendor).where(Vendor.id == vendor_id)).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    # Only allow vendor owner or admin to view full details
    if (vendor.user_id != current_user.id and 
        current_user.user_type not in ["admin", "super_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this vendor"
        )
    
    return vendor


@router.put("/{vendor_id}", response_model=VendorRead)
async def update_vendor(
    vendor_id: UUID,
    vendor_data: VendorUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update vendor"""
    
    vendor = db.exec(select(Vendor).where(Vendor.id == vendor_id)).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    # Only allow vendor owner or admin to update
    if (vendor.user_id != current_user.id and 
        current_user.user_type not in ["admin", "super_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this vendor"
        )
    
    # Update vendor fields
    update_data = vendor_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vendor, field, value)
    
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    
    return vendor


@router.post("/{vendor_id}/verify")
async def verify_vendor(
    vendor_id: UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_admin_user)
):
    """Verify vendor (Admin only)"""
    
    vendor = db.exec(select(Vendor).where(Vendor.id == vendor_id)).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    vendor.is_verified = True
    vendor.verification_status = VerificationStatus.VERIFIED
    vendor.verified_by = current_user.id
    vendor.verified_at = vendor.updated_at
    
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    
    return {"message": "Vendor verified successfully", "vendor_id": vendor_id}


@router.post("/{vendor_id}/reject")
async def reject_vendor(
    vendor_id: UUID,
    rejection_reason: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_admin_user)
):
    """Reject vendor verification (Admin only)"""
    
    vendor = db.exec(select(Vendor).where(Vendor.id == vendor_id)).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    vendor.is_verified = False
    vendor.verification_status = VerificationStatus.REJECTED
    vendor.verification_notes = rejection_reason
    vendor.verified_by = current_user.id
    vendor.verified_at = vendor.updated_at
    
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    
    return {"message": "Vendor rejected", "vendor_id": vendor_id, "reason": rejection_reason}


@router.post("/{vendor_id}/activate")
async def activate_vendor(
    vendor_id: UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_admin_user)
):
    """Activate vendor (Admin only)"""
    
    vendor = db.exec(select(Vendor).where(Vendor.id == vendor_id)).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    vendor.is_active = True
    vendor.disabled_by = None
    vendor.disabled_at = None
    vendor.disabled_reason = None
    
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    
    return {"message": "Vendor activated successfully", "vendor_id": vendor_id}


@router.post("/{vendor_id}/deactivate")
async def deactivate_vendor(
    vendor_id: UUID,
    reason: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_admin_user)
):
    """Deactivate vendor (Admin only)"""
    
    vendor = db.exec(select(Vendor).where(Vendor.id == vendor_id)).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    vendor.is_active = False
    vendor.disabled_by = current_user.id
    vendor.disabled_at = vendor.updated_at
    vendor.disabled_reason = reason
    
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    
    return {"message": "Vendor deactivated", "vendor_id": vendor_id, "reason": reason}


@router.get("/me/profile", response_model=VendorRead)
async def get_my_vendor_profile(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get current user's vendor profile"""
    
    vendor = db.exec(select(Vendor).where(Vendor.user_id == current_user.id)).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No vendor profile found for current user"
        )
    
    return vendor


@router.put("/me/profile", response_model=VendorRead)
async def update_my_vendor_profile(
    vendor_data: VendorUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update current user's vendor profile"""
    
    vendor = db.exec(select(Vendor).where(Vendor.user_id == current_user.id)).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No vendor profile found for current user"
        )
    
    # Update vendor fields
    update_data = vendor_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vendor, field, value)
    
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    
    return vendor
