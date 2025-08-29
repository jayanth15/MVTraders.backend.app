"""
Admin subscription management API endpoints.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, case
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.deps import get_current_user, get_session, require_admin
from app.models.user import User
from app.models.vendor import Vendor
from app.models.subscription import (
    SubscriptionPlan, Subscription, Payment, Invoice, UsageRecord,
    SubscriptionPlanType, BillingCycle, SubscriptionStatus, PaymentStatus
)

router = APIRouter()


@router.post("/plans", response_model=Dict[str, Any])
def create_subscription_plan(
    name: str,
    description: Optional[str],
    plan_type: SubscriptionPlanType,
    base_price: float,
    billing_cycle: BillingCycle,
    features: Dict[str, Any],
    setup_fee: Optional[float] = None,
    max_products: Optional[int] = None,
    max_orders_per_month: Optional[int] = None,
    max_storage_mb: Optional[int] = None,
    trial_days: Optional[int] = None,
    is_featured: bool = False,
    sort_order: int = 0,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_session)
):
    """
    Create a new subscription plan (Admin only)
    """
    plan = SubscriptionPlan(
        name=name,
        description=description,
        plan_type=plan_type,
        base_price=Decimal(str(base_price)),
        billing_cycle=billing_cycle,
        features=features,
        setup_fee=Decimal(str(setup_fee)) if setup_fee else None,
        max_products=max_products,
        max_orders_per_month=max_orders_per_month,
        max_storage_mb=max_storage_mb,
        trial_days=trial_days,
        is_featured=is_featured,
        sort_order=sort_order
    )
    
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    return {
        "id": plan.id,
        "name": plan.name,
        "plan_type": plan.plan_type,
        "base_price": float(plan.base_price),
        "message": "Subscription plan created successfully"
    }


@router.put("/plans/{plan_id}", response_model=Dict[str, Any])
def update_subscription_plan(
    plan_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    base_price: Optional[float] = None,
    features: Optional[Dict[str, Any]] = None,
    setup_fee: Optional[float] = None,
    max_products: Optional[int] = None,
    max_orders_per_month: Optional[int] = None,
    max_storage_mb: Optional[int] = None,
    trial_days: Optional[int] = None,
    is_active: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    sort_order: Optional[int] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_session)
):
    """
    Update a subscription plan (Admin only)
    """
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found"
        )
    
    # Update fields if provided
    if name is not None:
        plan.name = name
    if description is not None:
        plan.description = description
    if base_price is not None:
        plan.base_price = Decimal(str(base_price))
    if features is not None:
        plan.features = features
    if setup_fee is not None:
        plan.setup_fee = Decimal(str(setup_fee))
    if max_products is not None:
        plan.max_products = max_products
    if max_orders_per_month is not None:
        plan.max_orders_per_month = max_orders_per_month
    if max_storage_mb is not None:
        plan.max_storage_mb = max_storage_mb
    if trial_days is not None:
        plan.trial_days = trial_days
    if is_active is not None:
        plan.is_active = is_active
    if is_featured is not None:
        plan.is_featured = is_featured
    if sort_order is not None:
        plan.sort_order = sort_order
    
    plan.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "id": plan.id,
        "message": "Subscription plan updated successfully"
    }


@router.get("/subscriptions", response_model=List[Dict[str, Any]])
def get_all_subscriptions(
    status: Optional[SubscriptionStatus] = None,
    plan_type: Optional[SubscriptionPlanType] = None,
    vendor_id: Optional[int] = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_session)
):
    """
    Get all subscriptions with filters (Admin only)
    """
    query = db.query(Subscription).join(SubscriptionPlan).join(Vendor)
    
    if status:
        query = query.filter(Subscription.status == status)
    
    if plan_type:
        query = query.filter(SubscriptionPlan.plan_type == plan_type)
    
    if vendor_id:
        query = query.filter(Subscription.vendor_id == vendor_id)
    
    subscriptions = query.order_by(desc(Subscription.created_at)).offset(offset).limit(limit).all()
    
    result = []
    for subscription in subscriptions:
        vendor = db.query(Vendor).filter(Vendor.id == subscription.vendor_id).first()
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == subscription.plan_id).first()
        
        result.append({
            "id": subscription.id,
            "vendor": {
                "id": vendor.id,
                "business_name": vendor.business_name,
                "email": vendor.email
            },
            "plan": {
                "id": plan.id,
                "name": plan.name,
                "plan_type": plan.plan_type
            },
            "status": subscription.status,
            "start_date": subscription.start_date.isoformat(),
            "current_period_start": subscription.current_period_start.isoformat(),
            "current_period_end": subscription.current_period_end.isoformat(),
            "next_billing_date": subscription.next_billing_date.isoformat() if subscription.next_billing_date else None,
            "amount": float(subscription.amount),
            "auto_renew": subscription.auto_renew,
            "is_active": subscription.is_active(),
            "days_remaining": subscription.days_remaining(),
            "created_at": subscription.created_at.isoformat()
        })
    
    return result


@router.get("/subscriptions/{subscription_id}", response_model=Dict[str, Any])
def get_subscription_details(
    subscription_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_session)
):
    """
    Get detailed subscription information (Admin only)
    """
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Get related data
    vendor = db.query(Vendor).filter(Vendor.id == subscription.vendor_id).first()
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == subscription.plan_id).first()
    
    # Get payment history
    payments = db.query(Payment).filter(
        Payment.subscription_id == subscription.id
    ).order_by(desc(Payment.created_at)).limit(5).all()
    
    # Get usage records
    usage_records = db.query(UsageRecord).filter(
        UsageRecord.subscription_id == subscription.id
    ).all()
    
    return {
        "id": subscription.id,
        "vendor": {
            "id": vendor.id,
            "business_name": vendor.business_name,
            "email": vendor.email,
            "phone": vendor.phone,
            "created_at": vendor.created_at.isoformat()
        },
        "plan": {
            "id": plan.id,
            "name": plan.name,
            "plan_type": plan.plan_type,
            "base_price": float(plan.base_price),
            "billing_cycle": plan.billing_cycle,
            "features": plan.features
        },
        "status": subscription.status,
        "start_date": subscription.start_date.isoformat(),
        "end_date": subscription.end_date.isoformat() if subscription.end_date else None,
        "trial_end_date": subscription.trial_end_date.isoformat() if subscription.trial_end_date else None,
        "current_period_start": subscription.current_period_start.isoformat(),
        "current_period_end": subscription.current_period_end.isoformat(),
        "next_billing_date": subscription.next_billing_date.isoformat() if subscription.next_billing_date else None,
        "amount": float(subscription.amount),
        "currency": subscription.currency,
        "auto_renew": subscription.auto_renew,
        "is_active": subscription.is_active(),
        "is_trial": subscription.is_trial(),
        "days_remaining": subscription.days_remaining(),
        "cancelled_at": subscription.cancelled_at.isoformat() if subscription.cancelled_at else None,
        "cancellation_reason": subscription.cancellation_reason,
        "subscription_metadata": subscription.subscription_metadata,
        "recent_payments": [
            {
                "id": payment.id,
                "amount": float(payment.amount),
                "status": payment.status,
                "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
                "transaction_id": payment.transaction_id
            } for payment in payments
        ],
        "usage_records": [
            {
                "feature_name": usage.feature_name,
                "usage_count": usage.usage_count,
                "usage_limit": usage.usage_limit,
                "usage_percentage": usage.usage_percentage()
            } for usage in usage_records
        ],
        "created_at": subscription.created_at.isoformat()
    }


@router.put("/subscriptions/{subscription_id}/status", response_model=Dict[str, Any])
def update_subscription_status(
    subscription_id: int,
    new_status: SubscriptionStatus,
    reason: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_session)
):
    """
    Update subscription status (Admin only)
    """
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    old_status = subscription.status
    subscription.status = new_status
    
    # Handle status-specific logic
    if new_status == SubscriptionStatus.CANCELLED:
        subscription.cancelled_at = datetime.utcnow()
        subscription.cancellation_reason = reason or "Admin action"
        subscription.auto_renew = False
    elif new_status == SubscriptionStatus.SUSPENDED:
        subscription.auto_renew = False
    elif new_status == SubscriptionStatus.ACTIVE:
        subscription.cancelled_at = None
        subscription.cancellation_reason = None
        subscription.auto_renew = True
    
    subscription.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "subscription_id": subscription.id,
        "old_status": old_status,
        "new_status": new_status,
        "reason": reason,
        "message": f"Subscription status updated from {old_status} to {new_status}"
    }


@router.get("/analytics/subscription-overview", response_model=Dict[str, Any])
def get_subscription_analytics(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_session)
):
    """
    Get subscription analytics overview (Admin only)
    """
    # Total subscriptions by status
    status_counts = db.query(
        Subscription.status,
        func.count(Subscription.id).label('count')
    ).group_by(Subscription.status).all()
    
    # Revenue by plan type
    revenue_by_plan = db.query(
        SubscriptionPlan.plan_type,
        func.sum(Payment.amount).label('total_revenue'),
        func.count(Payment.id).label('payment_count')
    ).join(Subscription).join(Payment).filter(
        Payment.status == PaymentStatus.COMPLETED
    ).group_by(SubscriptionPlan.plan_type).all()
    
    # Monthly recurring revenue (MRR)
    current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    mrr = db.query(func.sum(Subscription.amount)).filter(
        Subscription.status == SubscriptionStatus.ACTIVE,
        Subscription.current_period_start >= current_month
    ).scalar() or 0
    
    # Churn rate (cancelled subscriptions in last 30 days)
    last_30_days = datetime.utcnow() - timedelta(days=30)
    churned_count = db.query(func.count(Subscription.id)).filter(
        Subscription.status == SubscriptionStatus.CANCELLED,
        Subscription.cancelled_at >= last_30_days
    ).scalar() or 0
    
    total_active = db.query(func.count(Subscription.id)).filter(
        Subscription.status == SubscriptionStatus.ACTIVE
    ).scalar() or 0
    
    churn_rate = (churned_count / (total_active + churned_count)) * 100 if (total_active + churned_count) > 0 else 0
    
    # Top performing plans
    top_plans = db.query(
        SubscriptionPlan.name,
        func.count(Subscription.id).label('subscription_count'),
        func.sum(Payment.amount).label('total_revenue')
    ).join(Subscription).join(Payment).filter(
        Payment.status == PaymentStatus.COMPLETED
    ).group_by(SubscriptionPlan.id, SubscriptionPlan.name).order_by(
        desc(func.count(Subscription.id))
    ).limit(5).all()
    
    return {
        "overview": {
            "total_subscriptions": sum([count for _, count in status_counts]),
            "active_subscriptions": total_active,
            "monthly_recurring_revenue": float(mrr),
            "churn_rate": round(churn_rate, 2)
        },
        "status_breakdown": {
            status: count for status, count in status_counts
        },
        "revenue_by_plan_type": [
            {
                "plan_type": plan_type,
                "total_revenue": float(total_revenue),
                "payment_count": payment_count
            } for plan_type, total_revenue, payment_count in revenue_by_plan
        ],
        "top_plans": [
            {
                "plan_name": name,
                "subscription_count": subscription_count,
                "total_revenue": float(total_revenue)
            } for name, subscription_count, total_revenue in top_plans
        ]
    }


@router.get("/payments", response_model=List[Dict[str, Any]])
def get_all_payments(
    status: Optional[PaymentStatus] = None,
    vendor_id: Optional[int] = None,
    subscription_id: Optional[int] = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_session)
):
    """
    Get all payments with filters (Admin only)
    """
    query = db.query(Payment).join(Vendor)
    
    if status:
        query = query.filter(Payment.status == status)
    
    if vendor_id:
        query = query.filter(Payment.vendor_id == vendor_id)
    
    if subscription_id:
        query = query.filter(Payment.subscription_id == subscription_id)
    
    payments = query.order_by(desc(Payment.created_at)).offset(offset).limit(limit).all()
    
    result = []
    for payment in payments:
        vendor = db.query(Vendor).filter(Vendor.id == payment.vendor_id).first()
        
        result.append({
            "id": payment.id,
            "vendor": {
                "id": vendor.id,
                "business_name": vendor.business_name,
                "email": vendor.email
            },
            "subscription_id": payment.subscription_id,
            "amount": float(payment.amount),
            "currency": payment.currency,
            "status": payment.status,
            "payment_method": payment.payment_method,
            "transaction_id": payment.transaction_id,
            "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
            "due_date": payment.due_date.isoformat() if payment.due_date else None,
            "failure_reason": payment.failure_reason,
            "retry_count": payment.retry_count,
            "created_at": payment.created_at.isoformat()
        })
    
    return result


@router.get("/analytics/revenue", response_model=Dict[str, Any])
def get_revenue_analytics(
    period: str = Query(default="monthly", regex="^(daily|weekly|monthly|yearly)$"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_session)
):
    """
    Get revenue analytics (Admin only)
    """
    # Set default date range if not provided
    if not end_date:
        end_date = datetime.utcnow()
    
    if not start_date:
        if period == "daily":
            start_date = end_date - timedelta(days=30)
        elif period == "weekly":
            start_date = end_date - timedelta(weeks=12)
        elif period == "monthly":
            start_date = end_date - timedelta(days=365)
        else:  # yearly
            start_date = end_date - timedelta(days=365 * 3)
    
    # Revenue over time
    if period == "daily":
        date_trunc = func.date(Payment.payment_date)
    elif period == "weekly":
        date_trunc = func.date_trunc('week', Payment.payment_date)
    elif period == "monthly":
        date_trunc = func.date_trunc('month', Payment.payment_date)
    else:  # yearly
        date_trunc = func.date_trunc('year', Payment.payment_date)
    
    revenue_over_time = db.query(
        date_trunc.label('period'),
        func.sum(Payment.amount).label('revenue'),
        func.count(Payment.id).label('payment_count')
    ).filter(
        Payment.status == PaymentStatus.COMPLETED,
        Payment.payment_date >= start_date,
        Payment.payment_date <= end_date
    ).group_by(date_trunc).order_by(date_trunc).all()
    
    # Total revenue
    total_revenue = db.query(func.sum(Payment.amount)).filter(
        Payment.status == PaymentStatus.COMPLETED,
        Payment.payment_date >= start_date,
        Payment.payment_date <= end_date
    ).scalar() or 0
    
    # Payment method breakdown
    payment_method_breakdown = db.query(
        Payment.payment_method,
        func.sum(Payment.amount).label('revenue'),
        func.count(Payment.id).label('count')
    ).filter(
        Payment.status == PaymentStatus.COMPLETED,
        Payment.payment_date >= start_date,
        Payment.payment_date <= end_date
    ).group_by(Payment.payment_method).all()
    
    return {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_revenue": float(total_revenue),
        "revenue_over_time": [
            {
                "period": period_date.isoformat() if hasattr(period_date, 'isoformat') else str(period_date),
                "revenue": float(revenue),
                "payment_count": payment_count
            } for period_date, revenue, payment_count in revenue_over_time
        ],
        "payment_method_breakdown": [
            {
                "payment_method": method,
                "revenue": float(revenue),
                "count": count
            } for method, revenue, count in payment_method_breakdown
        ]
    }
