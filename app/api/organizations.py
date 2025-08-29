"""
Organization management API endpoints
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel

from app.core.deps import get_session, get_current_user, get_admin_user, get_super_admin_user
from app.models import (
    User, Organization, OrganizationMember, OrganizationRole, VerificationStatus
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


class OrganizationCreate(BaseModel):
    """Organization creation schema"""
    name: str
    description: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    annual_revenue: Optional[float] = None
    credit_limit: float = 0.00


class OrganizationUpdate(BaseModel):
    """Organization update schema"""
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    annual_revenue: Optional[float] = None
    credit_limit: Optional[float] = None


class OrganizationRead(BaseModel):
    """Organization read schema"""
    id: UUID
    name: str
    description: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    annual_revenue: Optional[float] = None
    credit_limit: float
    is_active: bool
    is_verified: bool
    verification_status: VerificationStatus
    created_at: datetime


class OrganizationMemberCreate(BaseModel):
    """Organization member creation schema"""
    user_id: UUID
    organization_id: UUID
    role: OrganizationRole
    department: Optional[str] = None
    employee_id: Optional[str] = None


class OrganizationMemberRead(BaseModel):
    """Organization member read schema"""
    id: UUID
    user_id: UUID
    organization_id: UUID
    role: OrganizationRole
    department: Optional[str] = None
    employee_id: Optional[str] = None
    is_active: bool
    joined_at: datetime


@router.post("/", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_admin_user)  # Changed from get_super_admin_user
):
    """Create a new organization (Admin only)"""
    
    # Create organization
    organization = Organization(
        **org_data.model_dump(),
        created_by=current_user.id,
        verification_status=VerificationStatus.PENDING
    )
    
    db.add(organization)
    db.commit()
    db.refresh(organization)
    
    return organization


@router.get("/", response_model=List[OrganizationRead])
async def list_organizations(
    skip: int = 0,
    limit: int = 100,
    is_verified: Optional[bool] = None,
    is_active: Optional[bool] = None,
    industry: Optional[str] = None,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_admin_user)
):
    """List organizations with filtering (Admin only)"""
    
    query = select(Organization)
    
    if is_verified is not None:
        query = query.where(Organization.is_verified == is_verified)
    if is_active is not None:
        query = query.where(Organization.is_active == is_active)
    if industry:
        query = query.where(Organization.industry == industry)
    
    organizations = db.exec(query.offset(skip).limit(limit)).all()
    return organizations


@router.get("/{org_id}", response_model=OrganizationRead)
async def get_organization(
    org_id: UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get organization by ID"""
    
    organization = db.exec(select(Organization).where(Organization.id == org_id)).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if user is member of organization or admin
    is_member = db.exec(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active == True
        )
    ).first()
    
    if not is_member and current_user.user_type not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this organization"
        )
    
    return organization


@router.put("/{org_id}", response_model=OrganizationRead)
async def update_organization(
    org_id: UUID,
    org_data: OrganizationUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update organization"""
    
    organization = db.exec(select(Organization).where(Organization.id == org_id)).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if user is admin of organization or system admin
    is_org_admin = db.exec(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role.in_([OrganizationRole.ADMIN, OrganizationRole.SUPER_ADMIN]),
            OrganizationMember.is_active == True
        )
    ).first()
    
    if not is_org_admin and current_user.user_type not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this organization"
        )
    
    # Update organization fields
    update_data = org_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(organization, field, value)
    
    db.add(organization)
    db.commit()
    db.refresh(organization)
    
    return organization


@router.post("/{org_id}/verify")
async def verify_organization(
    org_id: UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_admin_user)
):
    """Verify organization (Admin only)"""
    
    organization = db.exec(select(Organization).where(Organization.id == org_id)).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    organization.is_verified = True
    organization.verification_status = VerificationStatus.VERIFIED
    organization.verified_by = current_user.id
    organization.verified_at = organization.updated_at
    
    db.add(organization)
    db.commit()
    db.refresh(organization)
    
    return {"message": "Organization verified successfully", "organization_id": org_id}


@router.post("/{org_id}/reject")
async def reject_organization(
    org_id: UUID,
    rejection_reason: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_admin_user)
):
    """Reject organization verification (Admin only)"""
    
    organization = db.exec(select(Organization).where(Organization.id == org_id)).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    organization.is_verified = False
    organization.verification_status = VerificationStatus.REJECTED
    organization.verification_notes = rejection_reason
    organization.verified_by = current_user.id
    organization.verified_at = organization.updated_at
    
    db.add(organization)
    db.commit()
    db.refresh(organization)
    
    return {"message": "Organization rejected", "organization_id": org_id, "reason": rejection_reason}


# Organization Member Management

@router.post("/{org_id}/members", response_model=OrganizationMemberRead, status_code=status.HTTP_201_CREATED)
async def add_organization_member(
    org_id: UUID,
    member_data: OrganizationMemberCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Add member to organization"""
    
    # Verify organization exists
    organization = db.exec(select(Organization).where(Organization.id == org_id)).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check authorization
    is_org_admin = db.exec(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role.in_([OrganizationRole.ADMIN, OrganizationRole.SUPER_ADMIN]),
            OrganizationMember.is_active == True
        )
    ).first()
    
    if not is_org_admin and current_user.user_type not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add members to this organization"
        )
    
    # Check if user exists
    user = db.exec(select(User).where(User.id == member_data.user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is already a member
    existing_member = db.exec(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == member_data.user_id
        )
    ).first()
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this organization"
        )
    
    # Create member
    member = OrganizationMember(
        **member_data.model_dump(),
        created_by=current_user.id
    )
    
    db.add(member)
    db.commit()
    db.refresh(member)
    
    return member


@router.get("/{org_id}/members", response_model=List[OrganizationMemberRead])
async def list_organization_members(
    org_id: UUID,
    skip: int = 0,
    limit: int = 100,
    role: Optional[OrganizationRole] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """List organization members"""
    
    # Check if user is member of organization or admin
    is_member = db.exec(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active == True
        )
    ).first()
    
    if not is_member and current_user.user_type not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view organization members"
        )
    
    query = select(OrganizationMember).where(OrganizationMember.organization_id == org_id)
    
    if role:
        query = query.where(OrganizationMember.role == role)
    if is_active is not None:
        query = query.where(OrganizationMember.is_active == is_active)
    
    members = db.exec(query.offset(skip).limit(limit)).all()
    return members


@router.delete("/{org_id}/members/{member_id}")
async def remove_organization_member(
    org_id: UUID,
    member_id: UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Remove member from organization"""
    
    # Check authorization
    is_org_admin = db.exec(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role.in_([OrganizationRole.ADMIN, OrganizationRole.SUPER_ADMIN]),
            OrganizationMember.is_active == True
        )
    ).first()
    
    if not is_org_admin and current_user.user_type not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to remove members from this organization"
        )
    
    # Find member
    member = db.exec(
        select(OrganizationMember).where(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == org_id
        )
    ).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # Deactivate member instead of deleting
    member.is_active = False
    
    db.add(member)
    db.commit()
    
    return {"message": "Member removed successfully", "member_id": member_id}
