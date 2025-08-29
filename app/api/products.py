"""
Product management API endpoints
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.deps import get_session, get_current_user, get_admin_user
from app.models import (
    User, Vendor, Product, ProductRead, ProductCreate, ProductUpdate, ProductApproval,
    ProductStatus, ProductCategory
)

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new product"""
    
    # Check if vendor exists and user owns it
    vendor = db.exec(select(Vendor).where(Vendor.id == product_data.vendor_id)).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    # Only vendor owner or admin can create products
    if (vendor.user_id != current_user.id and 
        current_user.user_type not in ["admin", "super_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create products for this vendor"
        )
    
    # Create product
    product = Product(
        **product_data.model_dump(),
        status=ProductStatus.DRAFT,
        is_approved=False
    )
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    return product


@router.get("/", response_model=List[ProductRead])
async def list_products(
    skip: int = 0,
    limit: int = 100,
    vendor_id: Optional[UUID] = None,
    category: Optional[ProductCategory] = None,
    status: Optional[ProductStatus] = None,
    is_approved: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_session)
):
    """List products with filtering (Public endpoint with limited info)"""
    
    query = select(Product)
    
    # Apply filters
    if vendor_id:
        query = query.where(Product.vendor_id == vendor_id)
    if category:
        query = query.where(Product.category == category)
    if status:
        query = query.where(Product.status == status)
    if is_approved is not None:
        query = query.where(Product.is_approved == is_approved)
    if is_featured is not None:
        query = query.where(Product.is_featured == is_featured)
    if min_price is not None:
        query = query.where(Product.price >= min_price)
    if max_price is not None:
        query = query.where(Product.price <= max_price)
    if search:
        query = query.where(Product.name.ilike(f"%{search}%"))
    
    # For public access, only show active and approved products
    query = query.where(
        Product.status == ProductStatus.ACTIVE,
        Product.is_approved == True
    )
    
    products = db.exec(query.offset(skip).limit(limit)).all()
    return products


@router.get("/admin", response_model=List[ProductRead])
async def list_all_products_admin(
    skip: int = 0,
    limit: int = 100,
    vendor_id: Optional[UUID] = None,
    category: Optional[ProductCategory] = None,
    status: Optional[ProductStatus] = None,
    is_approved: Optional[bool] = None,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_admin_user)
):
    """List all products (Admin only - includes drafts and unapproved)"""
    
    query = select(Product)
    
    if vendor_id:
        query = query.where(Product.vendor_id == vendor_id)
    if category:
        query = query.where(Product.category == category)
    if status:
        query = query.where(Product.status == status)
    if is_approved is not None:
        query = query.where(Product.is_approved == is_approved)
    
    products = db.exec(query.offset(skip).limit(limit)).all()
    return products


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: UUID,
    db: Session = Depends(get_session)
):
    """Get product by ID (Public endpoint)"""
    
    product = db.exec(select(Product).where(Product.id == product_id)).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # For public access, only show active and approved products
    if product.status != ProductStatus.ACTIVE or not product.is_approved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not available"
        )
    
    return product


@router.get("/vendor/{vendor_id}", response_model=List[ProductRead])
async def get_vendor_products(
    vendor_id: UUID,
    skip: int = 0,
    limit: int = 100,
    status: Optional[ProductStatus] = None,
    category: Optional[ProductCategory] = None,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get products for a specific vendor"""
    
    # Check if vendor exists
    vendor = db.exec(select(Vendor).where(Vendor.id == vendor_id)).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    query = select(Product).where(Product.vendor_id == vendor_id)
    
    # If not vendor owner or admin, only show active and approved products
    if (vendor.user_id != current_user.id and 
        current_user.user_type not in ["admin", "super_admin"]):
        query = query.where(
            Product.status == ProductStatus.ACTIVE,
            Product.is_approved == True
        )
    
    if status:
        query = query.where(Product.status == status)
    if category:
        query = query.where(Product.category == category)
    
    products = db.exec(query.offset(skip).limit(limit)).all()
    return products


@router.put("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: UUID,
    product_data: ProductUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update product"""
    
    product = db.exec(select(Product).where(Product.id == product_id)).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check vendor ownership
    vendor = db.exec(select(Vendor).where(Vendor.id == product.vendor_id)).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    # Only vendor owner or admin can update
    if (vendor.user_id != current_user.id and 
        current_user.user_type not in ["admin", "super_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this product"
        )
    
    # Update product fields
    update_data = product_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    # If product was modified and approved, reset approval
    if product.is_approved and current_user.user_type not in ["admin", "super_admin"]:
        product.is_approved = False
        product.approved_by = None
        product.approved_at = None
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    return product


@router.delete("/{product_id}")
async def delete_product(
    product_id: UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Delete product (soft delete by changing status)"""
    
    product = db.exec(select(Product).where(Product.id == product_id)).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check vendor ownership
    vendor = db.exec(select(Vendor).where(Vendor.id == product.vendor_id)).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    # Only vendor owner or admin can delete
    if (vendor.user_id != current_user.id and 
        current_user.user_type not in ["admin", "super_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this product"
        )
    
    # Soft delete by changing status
    product.status = ProductStatus.DISCONTINUED
    
    db.add(product)
    db.commit()
    
    return {"message": "Product deleted successfully", "product_id": product_id}


@router.post("/{product_id}/approve", response_model=ProductRead)
async def approve_product(
    product_id: UUID,
    approval_data: ProductApproval,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_admin_user)
):
    """Approve or reject product (Admin only)"""
    
    product = db.exec(select(Product).where(Product.id == product_id)).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    product.is_approved = approval_data.is_approved
    product.approved_by = current_user.id
    product.approved_at = product.updated_at
    
    # If approved, set status to active
    if approval_data.is_approved:
        product.status = ProductStatus.ACTIVE
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    status_msg = "approved" if approval_data.is_approved else "rejected"
    return {"message": f"Product {status_msg} successfully", "product": product}


@router.post("/{product_id}/feature")
async def toggle_product_feature(
    product_id: UUID,
    is_featured: bool,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_admin_user)
):
    """Toggle product featured status (Admin only)"""
    
    product = db.exec(select(Product).where(Product.id == product_id)).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    product.is_featured = is_featured
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    status_msg = "featured" if is_featured else "unfeatured"
    return {"message": f"Product {status_msg} successfully", "product_id": product_id}


@router.get("/categories/list")
async def list_product_categories():
    """Get list of all product categories"""
    return {
        "categories": [
            {"value": category.value, "label": category.value.replace("_", " ").title()}
            for category in ProductCategory
        ]
    }


@router.get("/featured", response_model=List[ProductRead])
async def get_featured_products(
    limit: int = 10,
    category: Optional[ProductCategory] = None,
    db: Session = Depends(get_session)
):
    """Get featured products"""
    
    query = select(Product).where(
        Product.is_featured == True,
        Product.status == ProductStatus.ACTIVE,
        Product.is_approved == True
    )
    
    if category:
        query = query.where(Product.category == category)
    
    products = db.exec(query.limit(limit)).all()
    return products
