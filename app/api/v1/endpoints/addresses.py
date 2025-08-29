"""
Address management endpoints for user and organization addresses.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.database import get_session
from app.models.address import Address
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.core.deps import get_current_user

router = APIRouter()


@router.post("/", response_model=Address, status_code=status.HTTP_201_CREATED)
async def create_address(
    address: Address,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new address for the current user or organization."""
    
    # Validate ownership
    if address.user_id and address.user_id != current_user.id:
        # Check if user is admin of the organization
        if address.organization_id:
            org_member = session.exec(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == address.organization_id,
                    OrganizationMember.user_id == current_user.id,
                    OrganizationMember.role.in_(["admin", "owner"])
                )
            ).first()
            if not org_member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to create address for this entity"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only create addresses for yourself or your organizations"
            )
    
    # Auto-assign user_id if not provided
    if not address.user_id and not address.organization_id:
        address.user_id = current_user.id
    
    session.add(address)
    session.commit()
    session.refresh(address)
    return address


@router.get("/", response_model=List[Address])
async def get_addresses(
    user_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    address_type: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get addresses for the current user or specified entity."""
    
    query = select(Address)
    
    if user_id:
        if user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only access your own addresses"
            )
        query = query.where(Address.user_id == user_id)
    elif organization_id:
        # Check if user has access to organization
        org_member = session.exec(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == current_user.id
            )
        ).first()
        if not org_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No access to organization addresses"
            )
        query = query.where(Address.organization_id == organization_id)
    else:
        # Get user's own addresses
        query = query.where(Address.user_id == current_user.id)
    
    if address_type:
        query = query.where(Address.type == address_type)
    
    addresses = session.exec(query).all()
    return addresses


@router.get("/{address_id}", response_model=Address)
async def get_address(
    address_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a specific address by ID."""
    
    address = session.get(Address, address_id)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found"
        )
    
    # Check ownership
    if address.user_id and address.user_id != current_user.id:
        if address.organization_id:
            org_member = session.exec(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == address.organization_id,
                    OrganizationMember.user_id == current_user.id
                )
            ).first()
            if not org_member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No access to this address"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No access to this address"
            )
    
    return address


@router.put("/{address_id}", response_model=Address)
async def update_address(
    address_id: int,
    address_data: Address,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update an existing address."""
    
    address = session.get(Address, address_id)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found"
        )
    
    # Check ownership
    if address.user_id and address.user_id != current_user.id:
        if address.organization_id:
            org_member = session.exec(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == address.organization_id,
                    OrganizationMember.user_id == current_user.id,
                    OrganizationMember.role.in_(["admin", "owner"])
                )
            ).first()
            if not org_member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No permission to update this address"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to update this address"
            )
    
    # Update fields
    for key, value in address_data.dict(exclude_unset=True).items():
        if key != "id":  # Don't update ID
            setattr(address, key, value)
    
    session.add(address)
    session.commit()
    session.refresh(address)
    return address


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    address_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Delete an address."""
    
    address = session.get(Address, address_id)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found"
        )
    
    # Check ownership
    if address.user_id and address.user_id != current_user.id:
        if address.organization_id:
            org_member = session.exec(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == address.organization_id,
                    OrganizationMember.user_id == current_user.id,
                    OrganizationMember.role.in_(["admin", "owner"])
                )
            ).first()
            if not org_member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No permission to delete this address"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to delete this address"
            )
    
    session.delete(address)
    session.commit()


@router.post("/{address_id}/set-default", response_model=Address)
async def set_default_address(
    address_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Set an address as the default for its type."""
    
    address = session.get(Address, address_id)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found"
        )
    
    # Check ownership
    if address.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only set default for your own addresses"
        )
    
    # Remove default from other addresses of same type
    other_addresses = session.exec(
        select(Address).where(
            Address.user_id == current_user.id,
            Address.type == address.type,
            Address.id != address_id
        )
    ).all()
    
    for other_addr in other_addresses:
        other_addr.is_default = False
        session.add(other_addr)
    
    # Set this address as default
    address.is_default = True
    session.add(address)
    session.commit()
    session.refresh(address)
    
    return address
