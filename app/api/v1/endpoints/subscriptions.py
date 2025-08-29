"""
Subscription management API endpoints.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime, timedelta

from app.core.deps import get_current_user, get_session, require_vendor, require_admin
from app.models.user import User
from app.models.vendor import Vendor
from app.models.subscription import (
    SubscriptionPlan, Subscription, Payment, 
    SubscriptionPlanType, SubscriptionStatus, BillingCycle
)

router = APIRouter()


@router.get("/plans", response_model=List[Dict[str, Any]])
def get_subscription_plans(
    plan_type: Optional[SubscriptionPlanType] = None,
    active_only: bool = True,
    include_features: bool = True,
    db: Session = Depends(get_session)
):
    """
    Get available subscription plans
    """
    query = db.query(SubscriptionPlan)
    
    if active_only:
        query = query.filter(SubscriptionPlan.is_active == True)
    
    if plan_type:
        query = query.filter(SubscriptionPlan.plan_type == plan_type)
    
    plans = query.order_by(SubscriptionPlan.sort_order, SubscriptionPlan.base_price).all()
    
    result = []
    for plan in plans:
        plan_data = {
            "id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "plan_type": plan.plan_type,
            "base_price": float(plan.base_price),
            "billing_cycle": plan.billing_cycle,
            "setup_fee": float(plan.setup_fee) if plan.setup_fee else None,
            "max_products": plan.max_products,
            "max_orders_per_month": plan.max_orders_per_month,
            "max_storage_mb": plan.max_storage_mb,
            "trial_days": plan.trial_days,
            "is_featured": plan.is_featured
        }
        
        if include_features:
            plan_data["features"] = plan.features
            
        result.append(plan_data)
    
    return result


@router.post("/subscribe/{plan_id}", response_model=Dict[str, Any])
def create_subscription(
    plan_id: int,
    billing_cycle: Optional[BillingCycle] = None,
    start_trial: bool = False,
    current_user: User = Depends(get_current_user),
    vendor: Vendor = Depends(require_vendor),
    db: Session = Depends(get_session)
):
    """
    Create a new subscription for a vendor
    """
    # Get the subscription plan
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == plan_id,
        SubscriptionPlan.is_active == True
    ).first()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found"
        )
    
    # Check if vendor already has an active subscription
    existing_subscription = db.query(Subscription).filter(
        Subscription.vendor_id == vendor.id,
        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
    ).first()
    
    if existing_subscription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor already has an active subscription"
        )
    
    # Use plan's billing cycle if not specified
    if not billing_cycle:
        billing_cycle = plan.billing_cycle
    
    # Calculate subscription period
    start_date = datetime.utcnow()
    
    if start_trial and plan.trial_days:
        status = SubscriptionStatus.TRIAL
        trial_end_date = start_date + timedelta(days=plan.trial_days)
        current_period_end = trial_end_date
    else:
        status = SubscriptionStatus.ACTIVE
        trial_end_date = None
        
        # Calculate period end based on billing cycle
        if billing_cycle == BillingCycle.MONTHLY:
            current_period_end = start_date + timedelta(days=30)
        elif billing_cycle == BillingCycle.QUARTERLY:
            current_period_end = start_date + timedelta(days=90)
        elif billing_cycle == BillingCycle.ANNUALLY:
            current_period_end = start_date + timedelta(days=365)
        else:  # LIFETIME
            current_period_end = start_date + timedelta(days=365 * 100)  # 100 years
    
    # Create subscription
    subscription = Subscription(
        vendor_id=vendor.id,
        plan_id=plan.id,
        status=status,
        start_date=start_date,
        trial_end_date=trial_end_date,
        current_period_start=start_date,
        current_period_end=current_period_end,
        next_billing_date=current_period_end if status == SubscriptionStatus.ACTIVE else trial_end_date,
        amount=plan.base_price,
        auto_renew=True
    )
    
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    
    return {
        "id": subscription.id,
        "plan_name": plan.name,
        "status": subscription.status,
        "start_date": subscription.start_date.isoformat(),
        "end_date": subscription.current_period_end.isoformat(),
        "trial_end_date": subscription.trial_end_date.isoformat() if subscription.trial_end_date else None,
        "amount": float(subscription.amount),
        "auto_renew": subscription.auto_renew,
        "message": "Subscription created successfully"
    }


@router.get("/my-subscription", response_model=Dict[str, Any])
def get_my_subscription(
    current_user: User = Depends(get_current_user),
    vendor: Vendor = Depends(require_vendor),
    db: Session = Depends(get_session)
):
    """
    Get current vendor's subscription details
    """
    subscription = db.query(Subscription).filter(
        Subscription.vendor_id == vendor.id
    ).order_by(desc(Subscription.created_at)).first()
    
    if not subscription:
        return {
            "subscription": None,
            "message": "No subscription found"
        }
    
    # Get plan details
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == subscription.plan_id
    ).first()
    
    return {
        "subscription": {
            "id": subscription.id,
            "status": subscription.status,
            "plan": {
                "id": plan.id,
                "name": plan.name,
                "plan_type": plan.plan_type,
                "features": plan.features
            },
            "start_date": subscription.start_date.isoformat(),
            "current_period_start": subscription.current_period_start.isoformat(),
            "current_period_end": subscription.current_period_end.isoformat(),
            "trial_end_date": subscription.trial_end_date.isoformat() if subscription.trial_end_date else None,
            "next_billing_date": subscription.next_billing_date.isoformat() if subscription.next_billing_date else None,
            "amount": float(subscription.amount),
            "currency": subscription.currency,
            "auto_renew": subscription.auto_renew,
            "is_active": subscription.is_active(),
            "is_trial": subscription.is_trial(),
            "days_remaining": subscription.days_remaining(),
            "cancelled_at": subscription.cancelled_at.isoformat() if subscription.cancelled_at else None,
            "cancellation_reason": subscription.cancellation_reason
        }
    }


@router.put("/my-subscription/cancel", response_model=Dict[str, Any])
def cancel_subscription(
    reason: Optional[str] = None,
    immediate: bool = False,
    current_user: User = Depends(get_current_user),
    vendor: Vendor = Depends(require_vendor),
    db: Session = Depends(get_session)
):
    """
    Cancel vendor's subscription
    """
    subscription = db.query(Subscription).filter(
        Subscription.vendor_id == vendor.id,
        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    # Update subscription
    subscription.cancelled_at = datetime.utcnow()
    subscription.cancellation_reason = reason
    subscription.auto_renew = False
    
    if immediate:
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.end_date = datetime.utcnow()
    else:
        # Cancel at period end
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.end_date = subscription.current_period_end
    
    db.commit()
    
    return {
        "message": "Subscription cancelled successfully",
        "cancelled_at": subscription.cancelled_at.isoformat(),
        "end_date": subscription.end_date.isoformat() if subscription.end_date else None,
        "immediate": immediate
    }


@router.put("/my-subscription/reactivate", response_model=Dict[str, Any])
def reactivate_subscription(
    current_user: User = Depends(get_current_user),
    vendor: Vendor = Depends(require_vendor),
    db: Session = Depends(get_session)
):
    """
    Reactivate a cancelled subscription
    """
    subscription = db.query(Subscription).filter(
        Subscription.vendor_id == vendor.id,
        Subscription.status == SubscriptionStatus.CANCELLED
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No cancelled subscription found"
        )
    
    # Check if we can reactivate (not expired)
    if subscription.end_date and subscription.end_date < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription has expired and cannot be reactivated"
        )
    
    # Reactivate subscription
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.cancelled_at = None
    subscription.cancellation_reason = None
    subscription.auto_renew = True
    subscription.end_date = None
    
    db.commit()
    
    return {
        "message": "Subscription reactivated successfully",
        "status": subscription.status,
        "auto_renew": subscription.auto_renew
    }


@router.put("/my-subscription/change-plan/{new_plan_id}", response_model=Dict[str, Any])
def change_subscription_plan(
    new_plan_id: int,
    immediate: bool = False,
    current_user: User = Depends(get_current_user),
    vendor: Vendor = Depends(require_vendor),
    db: Session = Depends(get_session)
):
    """
    Change subscription plan (upgrade/downgrade)
    """
    # Get current subscription
    current_subscription = db.query(Subscription).filter(
        Subscription.vendor_id == vendor.id,
        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
    ).first()
    
    if not current_subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    # Get new plan
    new_plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == new_plan_id,
        SubscriptionPlan.is_active == True
    ).first()
    
    if not new_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="New subscription plan not found"
        )
    
    # Get current plan for comparison
    current_plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == current_subscription.plan_id
    ).first()
    
    if immediate:
        # Immediate plan change
        current_subscription.plan_id = new_plan.id
        current_subscription.amount = new_plan.base_price
        # Note: In a real system, you'd handle prorating here
    else:
        # Change at next billing cycle
        current_subscription.subscription_metadata["scheduled_plan_change"] = {
            "new_plan_id": new_plan.id,
            "change_date": current_subscription.current_period_end.isoformat(),
            "current_plan_id": current_plan.id
        }
    
    db.commit()
    
    return {
        "message": "Plan change scheduled successfully" if not immediate else "Plan changed successfully",
        "current_plan": current_plan.name,
        "new_plan": new_plan.name,
        "effective_date": datetime.utcnow().isoformat() if immediate else current_subscription.current_period_end.isoformat(),
        "immediate": immediate
    }


@router.get("/billing-history", response_model=List[Dict[str, Any]])
def get_billing_history(
    limit: int = Query(default=10, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    vendor: Vendor = Depends(require_vendor),
    db: Session = Depends(get_session)
):
    """
    Get vendor's billing history
    """
    payments = db.query(Payment).filter(
        Payment.vendor_id == vendor.id
    ).order_by(desc(Payment.created_at)).offset(offset).limit(limit).all()
    
    result = []
    for payment in payments:
        result.append({
            "id": payment.id,
            "amount": float(payment.amount),
            "currency": payment.currency,
            "status": payment.status,
            "payment_method": payment.payment_method,
            "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
            "due_date": payment.due_date.isoformat() if payment.due_date else None,
            "billing_period_start": payment.billing_period_start.isoformat(),
            "billing_period_end": payment.billing_period_end.isoformat(),
            "transaction_id": payment.transaction_id,
            "failure_reason": payment.failure_reason,
            "created_at": payment.created_at.isoformat()
        })
    
    return result
