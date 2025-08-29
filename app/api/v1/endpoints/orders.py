"""
Order management endpoints for the marketplace.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, and_, or_
from app.database import get_session
from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from app.models.user import User
from app.models.vendor import Vendor
from app.models.organization import Organization, OrganizationMember
from app.models.product import Product
from app.models.address import Address
from app.core.deps import get_current_user
from datetime import datetime

router = APIRouter()


@router.post("/", response_model=Order, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new order with items."""
    
    # Extract order items from the request
    items_data = order_data.pop("items", [])
    if not items_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must contain at least one item"
        )
    
    # Validate vendor
    vendor = session.get(Vendor, order_data.get("vendor_id"))
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    # Validate addresses if provided
    if order_data.get("billing_address_id"):
        billing_address = session.get(Address, order_data["billing_address_id"])
        if not billing_address or billing_address.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid billing address"
            )
    
    if order_data.get("shipping_address_id"):
        shipping_address = session.get(Address, order_data["shipping_address_id"])
        if not shipping_address or shipping_address.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid shipping address"
            )
    
    # Create order
    order = Order(
        **order_data,
        customer_id=current_user.id,
        status=OrderStatus.PENDING,
        payment_status=PaymentStatus.PENDING
    )
    
    session.add(order)
    session.commit()
    session.refresh(order)
    
    # Create order items
    total_amount = 0
    for item_data in items_data:
        product = session.get(Product, item_data["product_id"])
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {item_data['product_id']} not found"
            )
        
        if product.vendor_id != vendor.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {product.name} does not belong to vendor {vendor.business_name}"
            )
        
        # Create product snapshot
        product_snapshot = {
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "description": product.description,
            "category": product.category,
            "sku": product.sku
        }
        
        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=item_data["quantity"],
            unit_price=product.price,
            product_snapshot=product_snapshot,
            customizations=item_data.get("customizations", {}),
            special_instructions=item_data.get("special_instructions")
        )
        
        session.add(order_item)
        total_amount += float(product.price) * item_data["quantity"]
    
    # Update order total
    order.total_amount = total_amount
    session.add(order)
    session.commit()
    session.refresh(order)
    
    return order


@router.get("/", response_model=List[Order])
async def get_orders(
    status: Optional[OrderStatus] = None,
    vendor_id: Optional[int] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get orders for the current user or vendor."""
    
    query = select(Order)
    
    # Check if user is a vendor
    vendor = session.exec(
        select(Vendor).where(Vendor.user_id == current_user.id)
    ).first()
    
    if vendor and vendor_id and vendor_id == vendor.id:
        # Vendor viewing their orders
        query = query.where(Order.vendor_id == vendor.id)
    else:
        # Customer viewing their orders
        query = query.where(Order.customer_id == current_user.id)
    
    if status:
        query = query.where(Order.status == status)
    
    query = query.offset(offset).limit(limit).order_by(Order.created_at.desc())
    orders = session.exec(query).all()
    
    return orders


@router.get("/{order_id}", response_model=Order)
async def get_order(
    order_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a specific order by ID."""
    
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check access permission
    vendor = session.exec(
        select(Vendor).where(Vendor.user_id == current_user.id)
    ).first()
    
    if order.customer_id != current_user.id and (not vendor or order.vendor_id != vendor.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this order"
        )
    
    return order


@router.put("/{order_id}/status", response_model=Order)
async def update_order_status(
    order_id: int,
    new_status: OrderStatus,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update order status (vendor only)."""
    
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if user is the vendor for this order
    vendor = session.exec(
        select(Vendor).where(
            Vendor.user_id == current_user.id,
            Vendor.id == order.vendor_id
        )
    ).first()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the vendor can update order status"
        )
    
    # Validate status transition
    valid_transitions = {
        OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
        OrderStatus.CONFIRMED: [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
        OrderStatus.PROCESSING: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
        OrderStatus.SHIPPED: [OrderStatus.DELIVERED, OrderStatus.RETURNED],
        OrderStatus.DELIVERED: [OrderStatus.RETURNED],
    }
    
    if new_status not in valid_transitions.get(order.status, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {order.status} to {new_status}"
        )
    
    order.status = new_status
    order.updated_at = datetime.utcnow()
    
    # Set timestamps for specific statuses
    if new_status == OrderStatus.CONFIRMED:
        order.confirmed_at = datetime.utcnow()
    elif new_status == OrderStatus.SHIPPED:
        order.shipped_at = datetime.utcnow()
    elif new_status == OrderStatus.DELIVERED:
        order.delivered_at = datetime.utcnow()
    
    session.add(order)
    session.commit()
    session.refresh(order)
    
    return order


@router.put("/{order_id}/payment-status", response_model=Order)
async def update_payment_status(
    order_id: int,
    new_status: PaymentStatus,
    transaction_id: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update payment status."""
    
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if user is customer or vendor for this order
    vendor = session.exec(
        select(Vendor).where(Vendor.user_id == current_user.id)
    ).first()
    
    if order.customer_id != current_user.id and (not vendor or order.vendor_id != vendor.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this order"
        )
    
    order.payment_status = new_status
    if transaction_id:
        order.payment_transaction_id = transaction_id
    
    session.add(order)
    session.commit()
    session.refresh(order)
    
    return order


@router.get("/{order_id}/items", response_model=List[OrderItem])
async def get_order_items(
    order_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get items for a specific order."""
    
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check access permission
    vendor = session.exec(
        select(Vendor).where(Vendor.user_id == current_user.id)
    ).first()
    
    if order.customer_id != current_user.id and (not vendor or order.vendor_id != vendor.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this order"
        )
    
    items = session.exec(
        select(OrderItem).where(OrderItem.order_id == order_id)
    ).all()
    
    return items


@router.post("/{order_id}/cancel", response_model=Order)
async def cancel_order(
    order_id: int,
    reason: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Cancel an order (customer or vendor)."""
    
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if user can cancel this order
    vendor = session.exec(
        select(Vendor).where(Vendor.user_id == current_user.id)
    ).first()
    
    if order.customer_id != current_user.id and (not vendor or order.vendor_id != vendor.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to cancel this order"
        )
    
    # Check if order can be cancelled
    if order.status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED, OrderStatus.RETURNED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order with status {order.status}"
        )
    
    order.status = OrderStatus.CANCELLED
    order.updated_at = datetime.utcnow()
    if reason:
        order.notes = f"Cancelled: {reason}"
    
    session.add(order)
    session.commit()
    session.refresh(order)
    
    return order
