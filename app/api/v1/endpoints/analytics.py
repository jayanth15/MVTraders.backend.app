"""
Analytics and reporting API endpoints.
"""

from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, text
from datetime import datetime, timedelta, date
from decimal import Decimal

from app.core.deps import get_current_user, get_session, require_admin
from app.models.user import User
from app.models.vendor import Vendor
from app.models.order import Order, OrderStatus
from app.models.product import Product
from app.models.subscription import Subscription, Payment
from app.models.review import Review
from app.models.analytics import (
    AnalyticsReport, DashboardWidget, BusinessMetric,
    ReportType, MetricType, TimeGranularity
)

router = APIRouter()


@router.get("/dashboard/overview", response_model=Dict[str, Any])
def get_dashboard_overview(
    period_days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get main dashboard overview with key metrics
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=period_days)
    
    # Total vendors
    total_vendors = session.query(func.count(Vendor.id)).scalar() or 0
    
    # Active vendors (with orders in period)
    active_vendors = session.query(func.count(func.distinct(Order.vendor_id))).filter(
        Order.created_at >= start_date
    ).scalar() or 0
    
    # Total orders
    total_orders = session.query(func.count(Order.id)).filter(
        Order.created_at >= start_date
    ).scalar() or 0
    
    # Total revenue
    total_revenue = session.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= start_date,
        Order.status.in_([OrderStatus.DELIVERED, OrderStatus.COMPLETED])
    ).scalar() or 0
    
    # Total products
    total_products = session.query(func.count(Product.id)).scalar() or 0
    
    # Total reviews
    total_reviews = session.query(func.count(Review.id)).filter(
        Review.created_at >= start_date
    ).scalar() or 0
    
    # Average order value
    avg_order_value = session.query(func.avg(Order.total_amount)).filter(
        Order.created_at >= start_date,
        Order.status.in_([OrderStatus.DELIVERED, OrderStatus.COMPLETED])
    ).scalar() or 0
    
    # Previous period comparison
    prev_start_date = start_date - timedelta(days=period_days)
    prev_end_date = start_date
    
    prev_orders = session.query(func.count(Order.id)).filter(
        Order.created_at >= prev_start_date,
        Order.created_at < prev_end_date
    ).scalar() or 0
    
    prev_revenue = session.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= prev_start_date,
        Order.created_at < prev_end_date,
        Order.status.in_([OrderStatus.DELIVERED, OrderStatus.COMPLETED])
    ).scalar() or 0
    
    # Calculate growth rates
    orders_growth = ((total_orders - prev_orders) / prev_orders * 100) if prev_orders > 0 else 0
    revenue_growth = ((float(total_revenue) - float(prev_revenue)) / float(prev_revenue) * 100) if prev_revenue > 0 else 0
    
    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": period_days
        },
        "key_metrics": {
            "total_vendors": total_vendors,
            "active_vendors": active_vendors,
            "total_orders": total_orders,
            "total_revenue": float(total_revenue),
            "total_products": total_products,
            "total_reviews": total_reviews,
            "avg_order_value": float(avg_order_value)
        },
        "growth_metrics": {
            "orders_growth_rate": round(orders_growth, 2),
            "revenue_growth_rate": round(revenue_growth, 2),
            "vendor_adoption_rate": round((active_vendors / total_vendors * 100) if total_vendors > 0 else 0, 2)
        },
        "performance_indicators": {
            "orders_per_vendor": round(total_orders / active_vendors if active_vendors > 0 else 0, 2),
            "revenue_per_vendor": round(float(total_revenue) / active_vendors if active_vendors > 0 else 0, 2),
            "products_per_vendor": round(total_products / total_vendors if total_vendors > 0 else 0, 2),
            "reviews_per_order": round(total_reviews / total_orders if total_orders > 0 else 0, 2)
        }
    }


@router.get("/sales/trends", response_model=Dict[str, Any])
def get_sales_trends(
    period_days: int = Query(default=30, ge=7, le=365),
    granularity: TimeGranularity = Query(default=TimeGranularity.DAY),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get sales trends over time
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=period_days)
    
    # Determine SQL date truncation based on granularity
    if granularity == TimeGranularity.HOUR:
        date_trunc = func.date_trunc('hour', Order.created_at)
    elif granularity == TimeGranularity.DAY:
        date_trunc = func.date_trunc('day', Order.created_at)
    elif granularity == TimeGranularity.WEEK:
        date_trunc = func.date_trunc('week', Order.created_at)
    elif granularity == TimeGranularity.MONTH:
        date_trunc = func.date_trunc('month', Order.created_at)
    else:
        date_trunc = func.date_trunc('day', Order.created_at)
    
    # Sales trends query
    sales_trends = session.query(
        date_trunc.label('period'),
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('revenue'),
        func.avg(Order.total_amount).label('avg_order_value'),
        func.count(func.distinct(Order.vendor_id)).label('active_vendors')
    ).filter(
        Order.created_at >= start_date,
        Order.status.in_([OrderStatus.DELIVERED, OrderStatus.COMPLETED])
    ).group_by(date_trunc).order_by(date_trunc).all()
    
    # Order status distribution
    status_distribution = session.query(
        Order.status,
        func.count(Order.id).label('count')
    ).filter(
        Order.created_at >= start_date
    ).group_by(Order.status).all()
    
    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "granularity": granularity
        },
        "trends": [
            {
                "period": trend.period.isoformat() if hasattr(trend.period, 'isoformat') else str(trend.period),
                "order_count": trend.order_count,
                "revenue": float(trend.revenue or 0),
                "avg_order_value": float(trend.avg_order_value or 0),
                "active_vendors": trend.active_vendors
            } for trend in sales_trends
        ],
        "status_distribution": [
            {
                "status": status.value,
                "count": count,
                "percentage": round((count / sum([s.count for s in status_distribution]) * 100), 2)
            } for status, count in status_distribution
        ],
        "summary": {
            "total_orders": sum([trend.order_count for trend in sales_trends]),
            "total_revenue": sum([float(trend.revenue or 0) for trend in sales_trends]),
            "avg_daily_orders": round(sum([trend.order_count for trend in sales_trends]) / period_days, 2),
            "avg_daily_revenue": round(sum([float(trend.revenue or 0) for trend in sales_trends]) / period_days, 2)
        }
    }


@router.get("/vendors/performance", response_model=Dict[str, Any])
def get_vendor_performance(
    period_days: int = Query(default=30, ge=7, le=365),
    limit: int = Query(default=10, ge=1, le=50),
    sort_by: str = Query(default="revenue", regex="^(revenue|orders|avg_order_value|rating)$"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get vendor performance analytics
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=period_days)
    
    # Vendor performance query
    vendor_performance = session.query(
        Vendor.id,
        Vendor.business_name,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('revenue'),
        func.avg(Order.total_amount).label('avg_order_value'),
        func.count(Product.id).label('product_count')
    ).outerjoin(Order, and_(
        Order.vendor_id == Vendor.id,
        Order.created_at >= start_date,
        Order.status.in_([OrderStatus.DELIVERED, OrderStatus.COMPLETED])
    )).outerjoin(Product).group_by(
        Vendor.id, Vendor.business_name
    ).order_by(
        desc(func.sum(Order.total_amount)) if sort_by == "revenue" else
        desc(func.count(Order.id)) if sort_by == "orders" else
        desc(func.avg(Order.total_amount))
    ).limit(limit).all()
    
    # Get review ratings for vendors
    vendor_ratings = {}
    for vendor_id, _, _, _, _, _ in vendor_performance:
        avg_rating = session.query(func.avg(Review.rating)).filter(
            Review.vendor_id == vendor_id,
            Review.created_at >= start_date
        ).scalar()
        vendor_ratings[vendor_id] = float(avg_rating) if avg_rating else 0
    
    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": period_days
        },
        "top_vendors": [
            {
                "vendor_id": vendor.id,
                "business_name": vendor.business_name,
                "order_count": vendor.order_count or 0,
                "revenue": float(vendor.revenue or 0),
                "avg_order_value": float(vendor.avg_order_value or 0),
                "product_count": vendor.product_count or 0,
                "avg_rating": vendor_ratings.get(vendor.id, 0),
                "revenue_per_product": round(float(vendor.revenue or 0) / (vendor.product_count or 1), 2)
            } for vendor in vendor_performance
        ],
        "summary": {
            "total_vendors_analyzed": len(vendor_performance),
            "top_revenue": float(vendor_performance[0].revenue or 0) if vendor_performance else 0,
            "avg_revenue_per_vendor": round(
                sum([float(v.revenue or 0) for v in vendor_performance]) / len(vendor_performance), 2
            ) if vendor_performance else 0
        }
    }


@router.get("/products/analytics", response_model=Dict[str, Any])
def get_product_analytics(
    period_days: int = Query(default=30, ge=7, le=365),
    category: Optional[str] = None,
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get product analytics and performance
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=period_days)
    
    # Base query for product performance
    query = session.query(
        Product.id,
        Product.name,
        Product.category,
        Product.price,
        func.count(func.distinct(Order.id)).label('order_count'),
        func.sum(Order.total_amount).label('revenue'),
        func.count(Review.id).label('review_count'),
        func.avg(Review.rating).label('avg_rating')
    ).outerjoin(Order, and_(
        Order.created_at >= start_date,
        Order.status.in_([OrderStatus.DELIVERED, OrderStatus.COMPLETED])
    )).outerjoin(Review, and_(
        Review.product_id == Product.id,
        Review.created_at >= start_date
    ))
    
    if category:
        query = query.filter(Product.category == category)
    
    top_products = query.group_by(
        Product.id, Product.name, Product.category, Product.price
    ).order_by(desc(func.count(Order.id))).limit(limit).all()
    
    # Category performance
    category_performance = session.query(
        Product.category,
        func.count(func.distinct(Product.id)).label('product_count'),
        func.count(func.distinct(Order.id)).label('order_count'),
        func.sum(Order.total_amount).label('revenue'),
        func.avg(Review.rating).label('avg_rating')
    ).outerjoin(Order, and_(
        Order.created_at >= start_date,
        Order.status.in_([OrderStatus.DELIVERED, OrderStatus.COMPLETED])
    )).outerjoin(Review, and_(
        Review.product_id == Product.id,
        Review.created_at >= start_date
    )).group_by(Product.category).order_by(desc(func.sum(Order.total_amount))).all()
    
    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": period_days
        },
        "top_products": [
            {
                "product_id": product.id,
                "name": product.name,
                "category": product.category,
                "price": float(product.price),
                "order_count": product.order_count or 0,
                "revenue": float(product.revenue or 0),
                "review_count": product.review_count or 0,
                "avg_rating": round(float(product.avg_rating or 0), 2),
                "revenue_per_order": round(
                    float(product.revenue or 0) / (product.order_count or 1), 2
                )
            } for product in top_products
        ],
        "category_performance": [
            {
                "category": category.category,
                "product_count": category.product_count or 0,
                "order_count": category.order_count or 0,
                "revenue": float(category.revenue or 0),
                "avg_rating": round(float(category.avg_rating or 0), 2),
                "revenue_per_product": round(
                    float(category.revenue or 0) / (category.product_count or 1), 2
                )
            } for category in category_performance
        ],
        "summary": {
            "total_products_analyzed": len(top_products),
            "total_categories": len(category_performance),
            "top_category": category_performance[0].category if category_performance else None,
            "avg_orders_per_product": round(
                sum([p.order_count or 0 for p in top_products]) / len(top_products), 2
            ) if top_products else 0
        }
    }


@router.get("/revenue/breakdown", response_model=Dict[str, Any])
def get_revenue_breakdown(
    period_days: int = Query(default=30, ge=7, le=365),
    breakdown_by: str = Query(default="category", regex="^(category|vendor|payment_method|day)$"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get revenue breakdown by different dimensions
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=period_days)
    
    if breakdown_by == "category":
        # Revenue by product category
        breakdown_data = session.query(
            Product.category.label('dimension'),
            func.sum(Order.total_amount).label('revenue'),
            func.count(Order.id).label('order_count')
        ).join(Product).filter(
            Order.created_at >= start_date,
            Order.status.in_([OrderStatus.DELIVERED, OrderStatus.COMPLETED])
        ).group_by(Product.category).order_by(desc(func.sum(Order.total_amount))).all()
        
    elif breakdown_by == "vendor":
        # Revenue by vendor
        breakdown_data = session.query(
            Vendor.business_name.label('dimension'),
            func.sum(Order.total_amount).label('revenue'),
            func.count(Order.id).label('order_count')
        ).join(Vendor).filter(
            Order.created_at >= start_date,
            Order.status.in_([OrderStatus.DELIVERED, OrderStatus.COMPLETED])
        ).group_by(Vendor.business_name).order_by(desc(func.sum(Order.total_amount))).limit(20).all()
        
    elif breakdown_by == "payment_method":
        # Revenue by payment method
        breakdown_data = session.query(
            Order.payment_method.label('dimension'),
            func.sum(Order.total_amount).label('revenue'),
            func.count(Order.id).label('order_count')
        ).filter(
            Order.created_at >= start_date,
            Order.status.in_([OrderStatus.DELIVERED, OrderStatus.COMPLETED])
        ).group_by(Order.payment_method).order_by(desc(func.sum(Order.total_amount))).all()
        
    else:  # day
        # Revenue by day
        breakdown_data = session.query(
            func.date(Order.created_at).label('dimension'),
            func.sum(Order.total_amount).label('revenue'),
            func.count(Order.id).label('order_count')
        ).filter(
            Order.created_at >= start_date,
            Order.status.in_([OrderStatus.DELIVERED, OrderStatus.COMPLETED])
        ).group_by(func.date(Order.created_at)).order_by(func.date(Order.created_at)).all()
    
    total_revenue = sum([float(item.revenue or 0) for item in breakdown_data])
    
    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "breakdown_by": breakdown_by
        },
        "breakdown": [
            {
                "dimension": str(item.dimension),
                "revenue": float(item.revenue or 0),
                "order_count": item.order_count or 0,
                "percentage": round((float(item.revenue or 0) / total_revenue * 100), 2) if total_revenue > 0 else 0,
                "avg_order_value": round(float(item.revenue or 0) / (item.order_count or 1), 2)
            } for item in breakdown_data
        ],
        "summary": {
            "total_revenue": total_revenue,
            "total_orders": sum([item.order_count or 0 for item in breakdown_data]),
            "top_dimension": str(breakdown_data[0].dimension) if breakdown_data else None,
            "top_revenue": float(breakdown_data[0].revenue or 0) if breakdown_data else 0
        }
    }


@router.get("/customer/insights", response_model=Dict[str, Any])
def get_customer_insights(
    period_days: int = Query(default=30, ge=7, le=365),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get customer behavior insights
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=period_days)
    
    # Customer order patterns
    customer_patterns = session.query(
        Order.customer_phone,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('total_spent'),
        func.avg(Order.total_amount).label('avg_order_value'),
        func.min(Order.created_at).label('first_order'),
        func.max(Order.created_at).label('last_order')
    ).filter(
        Order.created_at >= start_date,
        Order.status.in_([OrderStatus.DELIVERED, OrderStatus.COMPLETED])
    ).group_by(Order.customer_phone).having(
        func.count(Order.id) > 0
    ).order_by(desc(func.sum(Order.total_amount))).limit(100).all()
    
    # Customer segmentation
    repeat_customers = sum([1 for c in customer_patterns if c.order_count > 1])
    total_customers = len(customer_patterns)
    
    # Order frequency analysis
    order_frequency = session.query(
        func.count(Order.id).label('orders_per_customer'),
        func.count(func.distinct(Order.customer_phone)).label('customer_count')
    ).filter(
        Order.created_at >= start_date,
        Order.status.in_([OrderStatus.DELIVERED, OrderStatus.COMPLETED])
    ).group_by(Order.customer_phone).all()
    
    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": period_days
        },
        "customer_metrics": {
            "total_customers": total_customers,
            "repeat_customers": repeat_customers,
            "repeat_customer_rate": round((repeat_customers / total_customers * 100), 2) if total_customers > 0 else 0,
            "avg_orders_per_customer": round(
                sum([c.order_count for c in customer_patterns]) / total_customers, 2
            ) if total_customers > 0 else 0,
            "avg_customer_value": round(
                sum([float(c.total_spent) for c in customer_patterns]) / total_customers, 2
            ) if total_customers > 0 else 0
        },
        "top_customers": [
            {
                "customer_phone": customer.customer_phone,
                "order_count": customer.order_count,
                "total_spent": float(customer.total_spent),
                "avg_order_value": round(float(customer.avg_order_value), 2),
                "customer_lifetime_days": (customer.last_order - customer.first_order).days + 1,
                "customer_type": "Repeat" if customer.order_count > 1 else "New"
            } for customer in customer_patterns[:20]
        ],
        "insights": {
            "high_value_customers": len([c for c in customer_patterns if float(c.total_spent) > 10000]),
            "frequent_customers": len([c for c in customer_patterns if c.order_count >= 5]),
            "avg_days_between_orders": round(
                sum([(c.last_order - c.first_order).days / (c.order_count - 1) 
                     for c in customer_patterns if c.order_count > 1]) / 
                max(1, len([c for c in customer_patterns if c.order_count > 1])), 2
            ) if customer_patterns else 0
        }
    }
