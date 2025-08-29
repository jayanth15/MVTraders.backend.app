"""
Alert and notification API endpoints for analytics.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, text
from datetime import datetime, timedelta
import json

from app.core.deps import get_current_user, get_session, require_admin
from app.models.user import User
from app.models.analytics import (
    AlertRule, AlertCondition, AlertStatus, AlertSeverity, MetricType
)

router = APIRouter()


@router.post("/alerts", response_model=Dict[str, Any])
def create_alert_rule(
    rule_name: str,
    rule_description: str,
    metric_name: str,
    condition: AlertCondition,
    threshold_value: float,
    severity: AlertSeverity,
    comparison_operator: str = ">=",
    time_window_minutes: int = 60,
    notification_channels: Optional[List[str]] = None,
    is_active: bool = True,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Create a new alert rule
    """
    # Validate comparison operator
    valid_operators = [">=", "<=", ">", "<", "==", "!="]
    if comparison_operator not in valid_operators:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid comparison operator. Must be one of: {valid_operators}"
        )
    
    alert_rule = AlertRule(
        rule_name=rule_name,
        rule_description=rule_description,
        metric_name=metric_name,
        condition=condition,
        threshold_value=threshold_value,
        comparison_operator=comparison_operator,
        time_window_minutes=time_window_minutes,
        severity=severity,
        notification_channels=notification_channels or ["email"],
        is_active=is_active,
        owner_user_id=current_user.id
    )
    
    session.add(alert_rule)
    session.commit()
    session.refresh(alert_rule)
    
    return {
        "id": alert_rule.id,
        "rule_name": alert_rule.rule_name,
        "message": "Alert rule created successfully"
    }


@router.get("/alerts", response_model=List[Dict[str, Any]])
def get_alert_rules(
    is_active: Optional[bool] = None,
    severity: Optional[AlertSeverity] = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get alert rules
    """
    query = session.query(AlertRule)
    
    # Filter by user's alert rules unless admin
    if current_user.user_type.value not in ["app_admin", "app_super_admin"]:
        query = query.filter(AlertRule.owner_user_id == current_user.id)
    
    if is_active is not None:
        query = query.filter(AlertRule.is_active == is_active)
    
    if severity:
        query = query.filter(AlertRule.severity == severity)
    
    alert_rules = query.order_by(desc(AlertRule.created_at)).offset(offset).limit(limit).all()
    
    return [
        {
            "id": rule.id,
            "rule_name": rule.rule_name,
            "rule_description": rule.rule_description,
            "metric_name": rule.metric_name,
            "condition": rule.condition,
            "threshold_value": float(rule.threshold_value),
            "comparison_operator": rule.comparison_operator,
            "time_window_minutes": rule.time_window_minutes,
            "severity": rule.severity,
            "notification_channels": rule.notification_channels,
            "is_active": rule.is_active,
            "trigger_count": rule.trigger_count,
            "last_triggered_at": rule.last_triggered_at.isoformat() if rule.last_triggered_at else None,
            "last_checked_at": rule.last_checked_at.isoformat() if rule.last_checked_at else None,
            "created_at": rule.created_at.isoformat(),
            "is_owner": rule.owner_user_id == current_user.id
        } for rule in alert_rules
    ]


@router.get("/alerts/{alert_id}", response_model=Dict[str, Any])
def get_alert_rule_details(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get detailed alert rule information
    """
    alert_rule = session.query(AlertRule).filter(AlertRule.id == alert_id).first()
    
    if not alert_rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )
    
    # Check access permissions
    if (current_user.user_type.value not in ["app_admin", "app_super_admin"] and 
        alert_rule.owner_user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this alert rule"
        )
    
    return {
        "id": alert_rule.id,
        "rule_name": alert_rule.rule_name,
        "rule_description": alert_rule.rule_description,
        "metric_name": alert_rule.metric_name,
        "condition": alert_rule.condition,
        "threshold_value": float(alert_rule.threshold_value),
        "comparison_operator": alert_rule.comparison_operator,
        "time_window_minutes": alert_rule.time_window_minutes,
        "severity": alert_rule.severity,
        "notification_channels": alert_rule.notification_channels,
        "is_active": alert_rule.is_active,
        "trigger_count": alert_rule.trigger_count,
        "last_triggered_at": alert_rule.last_triggered_at.isoformat() if alert_rule.last_triggered_at else None,
        "last_checked_at": alert_rule.last_checked_at.isoformat() if alert_rule.last_checked_at else None,
        "created_at": alert_rule.created_at.isoformat(),
        "updated_at": alert_rule.updated_at.isoformat()
    }


@router.put("/alerts/{alert_id}", response_model=Dict[str, Any])
def update_alert_rule(
    alert_id: int,
    rule_name: Optional[str] = None,
    rule_description: Optional[str] = None,
    threshold_value: Optional[float] = None,
    comparison_operator: Optional[str] = None,
    time_window_minutes: Optional[int] = None,
    severity: Optional[AlertSeverity] = None,
    notification_channels: Optional[List[str]] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Update alert rule
    """
    alert_rule = session.query(AlertRule).filter(AlertRule.id == alert_id).first()
    
    if not alert_rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )
    
    # Check ownership
    if (alert_rule.owner_user_id != current_user.id and 
        current_user.user_type.value not in ["app_admin", "app_super_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this alert rule"
        )
    
    # Update fields
    if rule_name is not None:
        alert_rule.rule_name = rule_name
    if rule_description is not None:
        alert_rule.rule_description = rule_description
    if threshold_value is not None:
        alert_rule.threshold_value = threshold_value
    if comparison_operator is not None:
        valid_operators = [">=", "<=", ">", "<", "==", "!="]
        if comparison_operator not in valid_operators:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid comparison operator. Must be one of: {valid_operators}"
            )
        alert_rule.comparison_operator = comparison_operator
    if time_window_minutes is not None:
        alert_rule.time_window_minutes = time_window_minutes
    if severity is not None:
        alert_rule.severity = severity
    if notification_channels is not None:
        alert_rule.notification_channels = notification_channels
    if is_active is not None:
        alert_rule.is_active = is_active
    
    alert_rule.updated_at = datetime.utcnow()
    session.commit()
    
    return {
        "id": alert_rule.id,
        "message": "Alert rule updated successfully"
    }


@router.delete("/alerts/{alert_id}", response_model=Dict[str, Any])
def delete_alert_rule(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Delete alert rule
    """
    alert_rule = session.query(AlertRule).filter(AlertRule.id == alert_id).first()
    
    if not alert_rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )
    
    # Check ownership
    if (alert_rule.owner_user_id != current_user.id and 
        current_user.user_type.value not in ["app_admin", "app_super_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this alert rule"
        )
    
    session.delete(alert_rule)
    session.commit()
    
    return {
        "message": "Alert rule deleted successfully"
    }


@router.post("/alerts/test/{alert_id}", response_model=Dict[str, Any])
def test_alert_rule(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Test an alert rule against current data
    """
    alert_rule = session.query(AlertRule).filter(AlertRule.id == alert_id).first()
    
    if not alert_rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )
    
    # Check access permissions
    if (current_user.user_type.value not in ["app_admin", "app_super_admin"] and 
        alert_rule.owner_user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this alert rule"
        )
    
    try:
        # Get current metric value
        current_value = _get_metric_value(session, alert_rule.metric_name, alert_rule.time_window_minutes)
        
        # Check if alert condition is met
        is_triggered = _evaluate_alert_condition(
            current_value, 
            alert_rule.threshold_value, 
            alert_rule.comparison_operator
        )
        
        # Update last checked time
        alert_rule.last_checked_at = datetime.utcnow()
        session.commit()
        
        return {
            "alert_id": alert_rule.id,
            "current_value": current_value,
            "threshold_value": float(alert_rule.threshold_value),
            "comparison_operator": alert_rule.comparison_operator,
            "is_triggered": is_triggered,
            "would_notify": is_triggered and alert_rule.is_active,
            "notification_channels": alert_rule.notification_channels if is_triggered else [],
            "severity": alert_rule.severity if is_triggered else None,
            "tested_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Alert test failed: {str(e)}"
        )


@router.post("/alerts/check-all", response_model=Dict[str, Any])
def check_all_alert_rules(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """
    Check all active alert rules (admin only)
    """
    active_rules = session.query(AlertRule).filter(AlertRule.is_active == True).all()
    
    triggered_alerts = []
    processed_count = 0
    
    for rule in active_rules:
        try:
            # Get current metric value
            current_value = _get_metric_value(session, rule.metric_name, rule.time_window_minutes)
            
            # Check if alert condition is met
            is_triggered = _evaluate_alert_condition(
                current_value, 
                rule.threshold_value, 
                rule.comparison_operator
            )
            
            # Update last checked time
            rule.last_checked_at = datetime.utcnow()
            
            if is_triggered:
                # Update trigger count and last triggered time
                rule.trigger_count += 1
                rule.last_triggered_at = datetime.utcnow()
                
                triggered_alerts.append({
                    "alert_id": rule.id,
                    "rule_name": rule.rule_name,
                    "metric_name": rule.metric_name,
                    "current_value": current_value,
                    "threshold_value": float(rule.threshold_value),
                    "severity": rule.severity,
                    "notification_channels": rule.notification_channels
                })
                
                # In a real implementation, you would send notifications here
                # background_tasks.add_task(send_alert_notification, rule, current_value)
            
            processed_count += 1
            
        except Exception as e:
            # Log error but continue processing other rules
            print(f"Error checking alert rule {rule.id}: {str(e)}")
    
    session.commit()
    
    return {
        "processed_count": processed_count,
        "triggered_count": len(triggered_alerts),
        "triggered_alerts": triggered_alerts,
        "checked_at": datetime.utcnow().isoformat()
    }


@router.get("/notifications/history", response_model=List[Dict[str, Any]])
def get_notification_history(
    alert_id: Optional[int] = None,
    severity: Optional[AlertSeverity] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get notification history (mock implementation)
    """
    # In a real implementation, you would have a notifications table
    # For now, we'll return alert trigger history from AlertRule model
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = session.query(AlertRule).filter(
        AlertRule.last_triggered_at >= start_date,
        AlertRule.trigger_count > 0
    )
    
    # Filter by user's alert rules unless admin
    if current_user.user_type.value not in ["app_admin", "app_super_admin"]:
        query = query.filter(AlertRule.owner_user_id == current_user.id)
    
    if alert_id:
        query = query.filter(AlertRule.id == alert_id)
    
    if severity:
        query = query.filter(AlertRule.severity == severity)
    
    rules = query.order_by(desc(AlertRule.last_triggered_at)).offset(offset).limit(limit).all()
    
    return [
        {
            "id": f"notif_{rule.id}_{rule.trigger_count}",
            "alert_id": rule.id,
            "rule_name": rule.rule_name,
            "metric_name": rule.metric_name,
            "severity": rule.severity,
            "triggered_at": rule.last_triggered_at.isoformat() if rule.last_triggered_at else None,
            "notification_channels": rule.notification_channels,
            "message": f"Alert '{rule.rule_name}' triggered for metric '{rule.metric_name}'",
            "status": "sent",  # Mock status
            "trigger_count": rule.trigger_count
        } for rule in rules
    ]


# Helper functions
def _get_metric_value(session: Session, metric_name: str, time_window_minutes: int) -> float:
    """Get current value for a metric"""
    # This is a simplified implementation
    # In a real system, you would query the actual metric data based on metric_name
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=time_window_minutes)
    
    # Mock metric calculations based on metric name
    if metric_name == "total_sales":
        from app.models.order import Order, OrderStatus
        total = session.query(func.sum(Order.total_amount)).filter(
            Order.created_at >= start_time,
            Order.status.in_([OrderStatus.DELIVERED, OrderStatus.COMPLETED])
        ).scalar()
        return float(total or 0)
    
    elif metric_name == "order_count":
        from app.models.order import Order
        count = session.query(func.count(Order.id)).filter(
            Order.created_at >= start_time
        ).scalar()
        return float(count or 0)
    
    elif metric_name == "vendor_count":
        from app.models.vendor import Vendor
        count = session.query(func.count(Vendor.id)).filter(
            Vendor.created_at >= start_time
        ).scalar()
        return float(count or 0)
    
    elif metric_name == "product_count":
        from app.models.product import Product
        count = session.query(func.count(Product.id)).filter(
            Product.created_at >= start_time
        ).scalar()
        return float(count or 0)
    
    elif metric_name == "avg_order_value":
        from app.models.order import Order, OrderStatus
        avg = session.query(func.avg(Order.total_amount)).filter(
            Order.created_at >= start_time,
            Order.status.in_([OrderStatus.DELIVERED, OrderStatus.COMPLETED])
        ).scalar()
        return float(avg or 0)
    
    else:
        # Default to returning a random value for unknown metrics
        import random
        return random.uniform(0, 100)


def _evaluate_alert_condition(current_value: float, threshold_value: float, operator: str) -> bool:
    """Evaluate if alert condition is met"""
    if operator == ">=":
        return current_value >= threshold_value
    elif operator == "<=":
        return current_value <= threshold_value
    elif operator == ">":
        return current_value > threshold_value
    elif operator == "<":
        return current_value < threshold_value
    elif operator == "==":
        return current_value == threshold_value
    elif operator == "!=":
        return current_value != threshold_value
    else:
        return False


async def send_alert_notification(alert_rule: AlertRule, current_value: float):
    """Send alert notification (mock implementation)"""
    # In a real implementation, you would send notifications via:
    # - Email
    # - SMS
    # - Slack
    # - Discord
    # - Webhook
    # etc.
    
    print(f"ALERT: {alert_rule.rule_name}")
    print(f"Metric: {alert_rule.metric_name}")
    print(f"Current Value: {current_value}")
    print(f"Threshold: {alert_rule.threshold_value}")
    print(f"Severity: {alert_rule.severity}")
    print(f"Channels: {alert_rule.notification_channels}")
    print("---")
