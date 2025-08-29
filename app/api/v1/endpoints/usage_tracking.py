"""
Usage tracking API endpoints for subscription features.
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
    UsageRecord, Subscription, SubscriptionPlan,
    SubscriptionStatus
)

router = APIRouter()


@router.get("/my-usage", response_model=List[Dict[str, Any]])
def get_my_usage(
    feature_name: Optional[str] = None,
    current_period_only: bool = True,
    current_user: User = Depends(get_current_user),
    vendor: Vendor = Depends(require_vendor),
    db: Session = Depends(get_session)
):
    """
    Get vendor's feature usage
    """
    # Get active subscription
    subscription = db.query(Subscription).filter(
        Subscription.vendor_id == vendor.id,
        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    # Build query
    query = db.query(UsageRecord).filter(UsageRecord.subscription_id == subscription.id)
    
    if feature_name:
        query = query.filter(UsageRecord.feature_name == feature_name)
    
    if current_period_only:
        query = query.filter(
            UsageRecord.period_start >= subscription.current_period_start,
            UsageRecord.period_end <= subscription.current_period_end
        )
    
    usage_records = query.order_by(desc(UsageRecord.created_at)).all()
    
    result = []
    for usage in usage_records:
        result.append({
            "id": usage.id,
            "feature_name": usage.feature_name,
            "usage_count": usage.usage_count,
            "usage_limit": usage.usage_limit,
            "usage_percentage": usage.usage_percentage(),
            "is_limit_exceeded": usage.is_limit_exceeded(),
            "period_start": usage.period_start.isoformat(),
            "period_end": usage.period_end.isoformat(),
            "usage_metadata": usage.usage_metadata,
            "created_at": usage.created_at.isoformat()
        })
    
    return result


@router.post("/track-usage", response_model=Dict[str, Any])
def track_feature_usage(
    feature_name: str,
    usage_increment: int = 1,
    usage_metadata: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    vendor: Vendor = Depends(require_vendor),
    db: Session = Depends(get_session)
):
    """
    Track usage of a subscription feature
    """
    # Get active subscription
    subscription = db.query(Subscription).filter(
        Subscription.vendor_id == vendor.id,
        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    # Get subscription plan to check limits
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == subscription.plan_id
    ).first()
    
    # Get or create usage record for current period
    usage_record = db.query(UsageRecord).filter(
        UsageRecord.subscription_id == subscription.id,
        UsageRecord.vendor_id == vendor.id,
        UsageRecord.feature_name == feature_name,
        UsageRecord.period_start >= subscription.current_period_start,
        UsageRecord.period_end <= subscription.current_period_end
    ).first()
    
    if not usage_record:
        # Determine usage limit based on plan features
        usage_limit = None
        if plan.features and feature_name in plan.features:
            usage_limit = plan.features[feature_name].get('limit')
        
        # Create new usage record
        usage_record = UsageRecord(
            subscription_id=subscription.id,
            vendor_id=vendor.id,
            feature_name=feature_name,
            usage_count=0,
            usage_limit=usage_limit,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            usage_metadata=usage_metadata or {}
        )
        db.add(usage_record)
    
    # Check if adding usage would exceed limit
    new_usage_count = usage_record.usage_count + usage_increment
    
    if usage_record.usage_limit and new_usage_count > usage_record.usage_limit:
        return {
            "success": False,
            "error": "Usage limit exceeded",
            "current_usage": usage_record.usage_count,
            "usage_limit": usage_record.usage_limit,
            "attempted_increment": usage_increment,
            "would_result_in": new_usage_count
        }
    
    # Update usage count
    usage_record.usage_count = new_usage_count
    usage_record.updated_at = datetime.utcnow()
    
    # Update metadata if provided
    if usage_metadata:
        if not usage_record.usage_metadata:
            usage_record.usage_metadata = {}
        usage_record.usage_metadata.update(usage_metadata)
    
    db.commit()
    db.refresh(usage_record)
    
    return {
        "success": True,
        "feature_name": usage_record.feature_name,
        "current_usage": usage_record.usage_count,
        "usage_limit": usage_record.usage_limit,
        "usage_percentage": usage_record.usage_percentage(),
        "increment_applied": usage_increment,
        "message": f"Usage tracked for {feature_name}"
    }


@router.get("/usage-summary", response_model=Dict[str, Any])
def get_usage_summary(
    current_user: User = Depends(get_current_user),
    vendor: Vendor = Depends(require_vendor),
    db: Session = Depends(get_session)
):
    """
    Get usage summary for vendor's current subscription
    """
    # Get active subscription
    subscription = db.query(Subscription).filter(
        Subscription.vendor_id == vendor.id,
        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    # Get subscription plan
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == subscription.plan_id
    ).first()
    
    # Get current period usage
    current_usage = db.query(UsageRecord).filter(
        UsageRecord.subscription_id == subscription.id,
        UsageRecord.period_start >= subscription.current_period_start,
        UsageRecord.period_end <= subscription.current_period_end
    ).all()
    
    # Calculate usage summary
    usage_by_feature = {}
    for usage in current_usage:
        usage_by_feature[usage.feature_name] = {
            "current_usage": usage.usage_count,
            "usage_limit": usage.usage_limit,
            "usage_percentage": usage.usage_percentage(),
            "is_limit_exceeded": usage.is_limit_exceeded()
        }
    
    # Add plan limits for features not yet used
    if plan.features:
        for feature_name, feature_config in plan.features.items():
            if feature_name not in usage_by_feature:
                limit = feature_config.get('limit') if isinstance(feature_config, dict) else None
                usage_by_feature[feature_name] = {
                    "current_usage": 0,
                    "usage_limit": limit,
                    "usage_percentage": 0.0,
                    "is_limit_exceeded": False
                }
    
    return {
        "subscription": {
            "id": subscription.id,
            "plan_name": plan.name,
            "status": subscription.status,
            "current_period_start": subscription.current_period_start.isoformat(),
            "current_period_end": subscription.current_period_end.isoformat()
        },
        "usage_by_feature": usage_by_feature,
        "period_info": {
            "start_date": subscription.current_period_start.isoformat(),
            "end_date": subscription.current_period_end.isoformat(),
            "days_remaining": (subscription.current_period_end - datetime.utcnow()).days
        }
    }


@router.get("/usage-history", response_model=List[Dict[str, Any]])
def get_usage_history(
    feature_name: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(default=10, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    vendor: Vendor = Depends(require_vendor),
    db: Session = Depends(get_session)
):
    """
    Get usage history for vendor
    """
    # Get vendor's subscriptions
    subscriptions = db.query(Subscription).filter(
        Subscription.vendor_id == vendor.id
    ).all()
    
    if not subscriptions:
        return []
    
    subscription_ids = [sub.id for sub in subscriptions]
    
    # Build query
    query = db.query(UsageRecord).filter(
        UsageRecord.subscription_id.in_(subscription_ids)
    )
    
    if feature_name:
        query = query.filter(UsageRecord.feature_name == feature_name)
    
    if start_date:
        query = query.filter(UsageRecord.period_start >= start_date)
    
    if end_date:
        query = query.filter(UsageRecord.period_end <= end_date)
    
    usage_records = query.order_by(desc(UsageRecord.created_at)).offset(offset).limit(limit).all()
    
    result = []
    for usage in usage_records:
        # Get subscription details
        subscription = next((sub for sub in subscriptions if sub.id == usage.subscription_id), None)
        plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.id == subscription.plan_id
        ).first() if subscription else None
        
        result.append({
            "id": usage.id,
            "feature_name": usage.feature_name,
            "usage_count": usage.usage_count,
            "usage_limit": usage.usage_limit,
            "usage_percentage": usage.usage_percentage(),
            "period_start": usage.period_start.isoformat(),
            "period_end": usage.period_end.isoformat(),
            "subscription": {
                "id": subscription.id,
                "plan_name": plan.name if plan else "Unknown",
                "status": subscription.status
            } if subscription else None,
            "usage_metadata": usage.usage_metadata,
            "created_at": usage.created_at.isoformat()
        })
    
    return result


# Admin endpoints
@router.get("/admin/usage-overview", response_model=Dict[str, Any])
def get_usage_overview_admin(
    feature_name: Optional[str] = None,
    plan_type: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_session)
):
    """
    Get usage overview across all vendors (Admin only)
    """
    # Build base query
    query = db.query(UsageRecord).join(Subscription).join(SubscriptionPlan)
    
    if feature_name:
        query = query.filter(UsageRecord.feature_name == feature_name)
    
    if plan_type:
        query = query.filter(SubscriptionPlan.plan_type == plan_type)
    
    # Get usage statistics
    usage_stats = query.with_entities(
        UsageRecord.feature_name,
        func.count(UsageRecord.id).label('total_records'),
        func.sum(UsageRecord.usage_count).label('total_usage'),
        func.avg(UsageRecord.usage_count).label('avg_usage'),
        func.count(
            case([(UsageRecord.usage_count >= UsageRecord.usage_limit, 1)], else_=None)
        ).label('limit_exceeded_count')
    ).group_by(UsageRecord.feature_name).all()
    
    # Get top users by feature
    top_users = db.query(
        UsageRecord.feature_name,
        Vendor.business_name,
        func.sum(UsageRecord.usage_count).label('total_usage')
    ).join(Subscription).join(Vendor).join(SubscriptionPlan).group_by(
        UsageRecord.feature_name, Vendor.id, Vendor.business_name
    ).order_by(desc(func.sum(UsageRecord.usage_count))).limit(10).all()
    
    return {
        "feature_statistics": [
            {
                "feature_name": feature_name,
                "total_records": total_records,
                "total_usage": total_usage or 0,
                "average_usage": float(avg_usage) if avg_usage else 0,
                "limit_exceeded_count": limit_exceeded_count or 0
            } for feature_name, total_records, total_usage, avg_usage, limit_exceeded_count in usage_stats
        ],
        "top_users": [
            {
                "feature_name": feature_name,
                "vendor_name": vendor_name,
                "total_usage": total_usage
            } for feature_name, vendor_name, total_usage in top_users
        ]
    }


@router.get("/admin/vendor-usage/{vendor_id}", response_model=Dict[str, Any])
def get_vendor_usage_admin(
    vendor_id: int,
    include_history: bool = False,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_session)
):
    """
    Get detailed usage information for a specific vendor (Admin only)
    """
    # Get vendor
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    # Get vendor's subscriptions
    subscriptions = db.query(Subscription).filter(
        Subscription.vendor_id == vendor_id
    ).order_by(desc(Subscription.created_at)).all()
    
    # Get current usage
    current_subscription = next(
        (sub for sub in subscriptions if sub.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
        None
    )
    
    current_usage = []
    if current_subscription:
        current_usage = db.query(UsageRecord).filter(
            UsageRecord.subscription_id == current_subscription.id,
            UsageRecord.period_start >= current_subscription.current_period_start,
            UsageRecord.period_end <= current_subscription.current_period_end
        ).all()
    
    # Get usage history if requested
    usage_history = []
    if include_history:
        subscription_ids = [sub.id for sub in subscriptions]
        usage_history = db.query(UsageRecord).filter(
            UsageRecord.subscription_id.in_(subscription_ids)
        ).order_by(desc(UsageRecord.created_at)).limit(50).all()
    
    return {
        "vendor": {
            "id": vendor.id,
            "business_name": vendor.business_name,
            "email": vendor.email
        },
        "current_subscription": {
            "id": current_subscription.id,
            "status": current_subscription.status,
            "plan_name": db.query(SubscriptionPlan).filter(
                SubscriptionPlan.id == current_subscription.plan_id
            ).first().name,
            "current_period_start": current_subscription.current_period_start.isoformat(),
            "current_period_end": current_subscription.current_period_end.isoformat()
        } if current_subscription else None,
        "current_usage": [
            {
                "feature_name": usage.feature_name,
                "usage_count": usage.usage_count,
                "usage_limit": usage.usage_limit,
                "usage_percentage": usage.usage_percentage(),
                "is_limit_exceeded": usage.is_limit_exceeded()
            } for usage in current_usage
        ],
        "usage_history": [
            {
                "feature_name": usage.feature_name,
                "usage_count": usage.usage_count,
                "usage_limit": usage.usage_limit,
                "period_start": usage.period_start.isoformat(),
                "period_end": usage.period_end.isoformat(),
                "created_at": usage.created_at.isoformat()
            } for usage in usage_history
        ] if include_history else []
    }
