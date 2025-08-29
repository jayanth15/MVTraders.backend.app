"""
Billing management API endpoints.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.deps import get_current_user, get_session, require_vendor, require_admin
from app.models.user import User
from app.models.vendor import Vendor
from app.models.subscription import (
    Payment, Invoice, BillingAddress, Subscription,
    PaymentStatus, PaymentMethod
)

router = APIRouter()


@router.post("/payments", response_model=Dict[str, Any])
def create_payment(
    subscription_id: int,
    payment_method: PaymentMethod,
    payment_method_details: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    vendor: Vendor = Depends(require_vendor),
    db: Session = Depends(get_session)
):
    """
    Create a payment for a subscription
    """
    # Get subscription
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.vendor_id == vendor.id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Create payment
    payment = Payment(
        subscription_id=subscription.id,
        vendor_id=vendor.id,
        amount=subscription.amount,
        currency=subscription.currency,
        status=PaymentStatus.PENDING,
        payment_method=payment_method,
        payment_method_details=payment_method_details,
        due_date=subscription.next_billing_date,
        billing_period_start=subscription.current_period_start,
        billing_period_end=subscription.current_period_end
    )
    
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    # In a real system, you would integrate with payment gateway here
    # For now, we'll simulate immediate success
    payment.status = PaymentStatus.COMPLETED
    payment.payment_date = datetime.utcnow()
    payment.transaction_id = f"TXN{payment.id}_{int(datetime.utcnow().timestamp())}"
    
    # Update subscription billing cycle
    if subscription.billing_cycle == "monthly":
        subscription.current_period_start = subscription.current_period_end
        subscription.current_period_end = subscription.current_period_end + timedelta(days=30)
        subscription.next_billing_date = subscription.current_period_end
    elif subscription.billing_cycle == "quarterly":
        subscription.current_period_start = subscription.current_period_end
        subscription.current_period_end = subscription.current_period_end + timedelta(days=90)
        subscription.next_billing_date = subscription.current_period_end
    elif subscription.billing_cycle == "annually":
        subscription.current_period_start = subscription.current_period_end
        subscription.current_period_end = subscription.current_period_end + timedelta(days=365)
        subscription.next_billing_date = subscription.current_period_end
    
    db.commit()
    
    return {
        "payment_id": payment.id,
        "status": payment.status,
        "amount": float(payment.amount),
        "transaction_id": payment.transaction_id,
        "payment_date": payment.payment_date.isoformat(),
        "message": "Payment processed successfully"
    }


@router.get("/payments/{payment_id}", response_model=Dict[str, Any])
def get_payment_details(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    vendor: Vendor = Depends(require_vendor),
    db: Session = Depends(get_session)
):
    """
    Get payment details
    """
    payment = db.query(Payment).filter(
        Payment.id == payment_id,
        Payment.vendor_id == vendor.id
    ).first()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    return {
        "id": payment.id,
        "amount": float(payment.amount),
        "currency": payment.currency,
        "status": payment.status,
        "payment_method": payment.payment_method,
        "payment_method_details": payment.payment_method_details,
        "transaction_id": payment.transaction_id,
        "external_payment_id": payment.external_payment_id,
        "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
        "due_date": payment.due_date.isoformat() if payment.due_date else None,
        "billing_period_start": payment.billing_period_start.isoformat(),
        "billing_period_end": payment.billing_period_end.isoformat(),
        "failure_reason": payment.failure_reason,
        "retry_count": payment.retry_count,
        "created_at": payment.created_at.isoformat()
    }


@router.put("/payments/{payment_id}/retry", response_model=Dict[str, Any])
def retry_failed_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    vendor: Vendor = Depends(require_vendor),
    db: Session = Depends(get_session)
):
    """
    Retry a failed payment
    """
    payment = db.query(Payment).filter(
        Payment.id == payment_id,
        Payment.vendor_id == vendor.id,
        Payment.status == PaymentStatus.FAILED
    ).first()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failed payment not found"
        )
    
    # Check retry limit
    if payment.retry_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum retry attempts exceeded"
        )
    
    # Update payment status and retry count
    payment.status = PaymentStatus.PENDING
    payment.retry_count += 1
    payment.failure_reason = None
    
    # In a real system, you would retry with payment gateway here
    # For simulation, we'll make it succeed on second retry
    if payment.retry_count >= 2:
        payment.status = PaymentStatus.COMPLETED
        payment.payment_date = datetime.utcnow()
        payment.transaction_id = f"TXN{payment.id}_RETRY_{int(datetime.utcnow().timestamp())}"
    
    db.commit()
    
    return {
        "payment_id": payment.id,
        "status": payment.status,
        "retry_count": payment.retry_count,
        "message": "Payment retry initiated"
    }


@router.get("/invoices", response_model=List[Dict[str, Any]])
def get_invoices(
    limit: int = Query(default=10, le=100),
    offset: int = Query(default=0, ge=0),
    paid_only: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    vendor: Vendor = Depends(require_vendor),
    db: Session = Depends(get_session)
):
    """
    Get vendor's invoices
    """
    query = db.query(Invoice).filter(Invoice.vendor_id == vendor.id)
    
    if paid_only is not None:
        query = query.filter(Invoice.is_paid == paid_only)
    
    invoices = query.order_by(desc(Invoice.created_at)).offset(offset).limit(limit).all()
    
    result = []
    for invoice in invoices:
        result.append({
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "subtotal": float(invoice.subtotal),
            "tax_amount": float(invoice.tax_amount),
            "discount_amount": float(invoice.discount_amount),
            "total_amount": float(invoice.total_amount),
            "invoice_date": invoice.invoice_date.isoformat(),
            "due_date": invoice.due_date.isoformat(),
            "is_paid": invoice.is_paid,
            "paid_date": invoice.paid_date.isoformat() if invoice.paid_date else None,
            "line_items": invoice.line_items,
            "created_at": invoice.created_at.isoformat()
        })
    
    return result


@router.get("/invoices/{invoice_id}", response_model=Dict[str, Any])
def get_invoice_details(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    vendor: Vendor = Depends(require_vendor),
    db: Session = Depends(get_session)
):
    """
    Get detailed invoice information
    """
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.vendor_id == vendor.id
    ).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Get associated payment
    payment = db.query(Payment).filter(Payment.id == invoice.payment_id).first()
    
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "subtotal": float(invoice.subtotal),
        "tax_amount": float(invoice.tax_amount),
        "discount_amount": float(invoice.discount_amount),
        "total_amount": float(invoice.total_amount),
        "invoice_date": invoice.invoice_date.isoformat(),
        "due_date": invoice.due_date.isoformat(),
        "is_paid": invoice.is_paid,
        "paid_date": invoice.paid_date.isoformat() if invoice.paid_date else None,
        "line_items": invoice.line_items,
        "invoice_metadata": invoice.invoice_metadata,
        "payment": {
            "id": payment.id,
            "status": payment.status,
            "payment_method": payment.payment_method,
            "transaction_id": payment.transaction_id
        } if payment else None,
        "created_at": invoice.created_at.isoformat()
    }


@router.get("/billing-addresses", response_model=List[Dict[str, Any]])
def get_billing_addresses(
    current_user: User = Depends(get_current_user),
    vendor: Vendor = Depends(require_vendor),
    db: Session = Depends(get_session)
):
    """
    Get vendor's billing addresses
    """
    addresses = db.query(BillingAddress).filter(
        BillingAddress.vendor_id == vendor.id
    ).all()
    
    result = []
    for address in addresses:
        result.append({
            "id": address.id,
            "company_name": address.company_name,
            "contact_person": address.contact_person,
            "email": address.email,
            "phone": address.phone,
            "address_line_1": address.address_line_1,
            "address_line_2": address.address_line_2,
            "city": address.city,
            "state": address.state,
            "postal_code": address.postal_code,
            "country": address.country,
            "gstin": address.gstin,
            "pan": address.pan,
            "is_default": address.is_default,
            "created_at": address.created_at.isoformat()
        })
    
    return result


@router.post("/billing-addresses", response_model=Dict[str, Any])
def create_billing_address(
    company_name: str,
    contact_person: str,
    email: str,
    phone: str,
    address_line_1: str,
    city: str,
    state: str,
    postal_code: str,
    address_line_2: Optional[str] = None,
    country: str = "India",
    gstin: Optional[str] = None,
    pan: Optional[str] = None,
    set_as_default: bool = False,
    current_user: User = Depends(get_current_user),
    vendor: Vendor = Depends(require_vendor),
    db: Session = Depends(get_session)
):
    """
    Create a new billing address
    """
    # If setting as default, unset other default addresses
    if set_as_default:
        db.query(BillingAddress).filter(
            BillingAddress.vendor_id == vendor.id,
            BillingAddress.is_default == True
        ).update({"is_default": False})
    
    # Create new billing address
    billing_address = BillingAddress(
        vendor_id=vendor.id,
        company_name=company_name,
        contact_person=contact_person,
        email=email,
        phone=phone,
        address_line_1=address_line_1,
        address_line_2=address_line_2,
        city=city,
        state=state,
        postal_code=postal_code,
        country=country,
        gstin=gstin,
        pan=pan,
        is_default=set_as_default
    )
    
    db.add(billing_address)
    db.commit()
    db.refresh(billing_address)
    
    return {
        "id": billing_address.id,
        "message": "Billing address created successfully",
        "is_default": billing_address.is_default
    }


@router.put("/billing-addresses/{address_id}", response_model=Dict[str, Any])
def update_billing_address(
    address_id: int,
    company_name: Optional[str] = None,
    contact_person: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    address_line_1: Optional[str] = None,
    address_line_2: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    country: Optional[str] = None,
    gstin: Optional[str] = None,
    pan: Optional[str] = None,
    set_as_default: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    vendor: Vendor = Depends(require_vendor),
    db: Session = Depends(get_session)
):
    """
    Update a billing address
    """
    billing_address = db.query(BillingAddress).filter(
        BillingAddress.id == address_id,
        BillingAddress.vendor_id == vendor.id
    ).first()
    
    if not billing_address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing address not found"
        )
    
    # Update fields if provided
    if company_name is not None:
        billing_address.company_name = company_name
    if contact_person is not None:
        billing_address.contact_person = contact_person
    if email is not None:
        billing_address.email = email
    if phone is not None:
        billing_address.phone = phone
    if address_line_1 is not None:
        billing_address.address_line_1 = address_line_1
    if address_line_2 is not None:
        billing_address.address_line_2 = address_line_2
    if city is not None:
        billing_address.city = city
    if state is not None:
        billing_address.state = state
    if postal_code is not None:
        billing_address.postal_code = postal_code
    if country is not None:
        billing_address.country = country
    if gstin is not None:
        billing_address.gstin = gstin
    if pan is not None:
        billing_address.pan = pan
    
    # Handle default setting
    if set_as_default is not None and set_as_default:
        # Unset other default addresses
        db.query(BillingAddress).filter(
            BillingAddress.vendor_id == vendor.id,
            BillingAddress.is_default == True,
            BillingAddress.id != address_id
        ).update({"is_default": False})
        
        billing_address.is_default = True
    elif set_as_default is False:
        billing_address.is_default = False
    
    billing_address.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "id": billing_address.id,
        "message": "Billing address updated successfully",
        "is_default": billing_address.is_default
    }


@router.delete("/billing-addresses/{address_id}", response_model=Dict[str, Any])
def delete_billing_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    vendor: Vendor = Depends(require_vendor),
    db: Session = Depends(get_session)
):
    """
    Delete a billing address
    """
    billing_address = db.query(BillingAddress).filter(
        BillingAddress.id == address_id,
        BillingAddress.vendor_id == vendor.id
    ).first()
    
    if not billing_address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing address not found"
        )
    
    # Check if this is the only address
    address_count = db.query(BillingAddress).filter(
        BillingAddress.vendor_id == vendor.id
    ).count()
    
    if address_count == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the only billing address"
        )
    
    db.delete(billing_address)
    db.commit()
    
    return {
        "message": "Billing address deleted successfully"
    }
