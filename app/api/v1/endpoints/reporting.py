"""
Reporting and dashboard management API endpoints.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime, timedelta
import json
import asyncio

from app.core.deps import get_current_user, get_session, require_admin
from app.models.user import User
from app.models.analytics import (
    AnalyticsReport, DashboardWidget, BusinessMetric, AnalyticsQuery, DataExport,
    ReportType, ReportFormat, ReportStatus, MetricType, TimeGranularity
)

router = APIRouter()


@router.post("/reports/generate", response_model=Dict[str, Any])
def generate_report(
    report_name: str,
    report_type: ReportType,
    date_range_start: datetime,
    date_range_end: datetime,
    filters: Optional[Dict[str, Any]] = None,
    format: ReportFormat = ReportFormat.JSON,
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Generate a new analytics report
    """
    # Create report record
    report = AnalyticsReport(
        report_name=report_name,
        report_type=report_type,
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        filters=filters or {},
        generated_by_user_id=current_user.id,
        format=format,
        status=ReportStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(days=7)  # Reports expire after 7 days
    )
    
    session.add(report)
    session.commit()
    session.refresh(report)
    
    # In a real implementation, you would queue this for background processing
    # For now, we'll simulate immediate processing
    try:
        start_time = datetime.utcnow()
        
        # Generate report data based on type
        if report_type == ReportType.SALES:
            report_data = _generate_sales_report(session, date_range_start, date_range_end, filters or {})
        elif report_type == ReportType.REVENUE:
            report_data = _generate_revenue_report(session, date_range_start, date_range_end, filters or {})
        elif report_type == ReportType.VENDOR:
            report_data = _generate_vendor_report(session, date_range_start, date_range_end, filters or {})
        elif report_type == ReportType.PRODUCT:
            report_data = _generate_product_report(session, date_range_start, date_range_end, filters or {})
        else:
            report_data = {"message": "Report type not implemented yet"}
        
        # Update report with generated data
        end_time = datetime.utcnow()
        execution_time = int((end_time - start_time).total_seconds() * 1000)
        
        report.report_data = report_data
        report.summary_metrics = _calculate_summary_metrics(report_data)
        report.status = ReportStatus.COMPLETED
        report.execution_time_ms = execution_time
        report.record_count = len(report_data.get('records', []))
        
        session.commit()
        
        return {
            "report_id": report.id,
            "status": report.status,
            "execution_time_ms": execution_time,
            "record_count": report.record_count,
            "message": "Report generated successfully"
        }
        
    except Exception as e:
        report.status = ReportStatus.FAILED
        report.report_data = {"error": str(e)}
        session.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}"
        )


@router.get("/reports", response_model=List[Dict[str, Any]])
def get_reports(
    report_type: Optional[ReportType] = None,
    status: Optional[ReportStatus] = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get list of analytics reports
    """
    query = session.query(AnalyticsReport)
    
    # Filter by user's reports unless admin
    if current_user.user_type.value not in ["app_admin", "app_super_admin"]:
        query = query.filter(AnalyticsReport.generated_by_user_id == current_user.id)
    
    if report_type:
        query = query.filter(AnalyticsReport.report_type == report_type)
    
    if status:
        query = query.filter(AnalyticsReport.status == status)
    
    reports = query.order_by(desc(AnalyticsReport.created_at)).offset(offset).limit(limit).all()
    
    return [
        {
            "id": report.id,
            "report_name": report.report_name,
            "report_type": report.report_type,
            "status": report.status,
            "date_range_start": report.date_range_start.isoformat(),
            "date_range_end": report.date_range_end.isoformat(),
            "format": report.format,
            "record_count": report.record_count,
            "execution_time_ms": report.execution_time_ms,
            "created_at": report.created_at.isoformat(),
            "expires_at": report.expires_at.isoformat() if report.expires_at else None,
            "is_expired": report.is_expired()
        } for report in reports
    ]


@router.get("/reports/{report_id}", response_model=Dict[str, Any])
def get_report_details(
    report_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get detailed report data
    """
    report = session.query(AnalyticsReport).filter(AnalyticsReport.id == report_id).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    # Check access permissions
    if (current_user.user_type.value not in ["app_admin", "app_super_admin"] and 
        report.generated_by_user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this report"
        )
    
    if report.is_expired():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Report has expired"
        )
    
    return {
        "id": report.id,
        "report_name": report.report_name,
        "report_type": report.report_type,
        "report_description": report.report_description,
        "status": report.status,
        "date_range_start": report.date_range_start.isoformat(),
        "date_range_end": report.date_range_end.isoformat(),
        "filters": report.filters,
        "format": report.format,
        "report_data": report.report_data,
        "summary_metrics": report.summary_metrics,
        "record_count": report.record_count,
        "execution_time_ms": report.execution_time_ms,
        "created_at": report.created_at.isoformat(),
        "expires_at": report.expires_at.isoformat() if report.expires_at else None
    }


@router.get("/dashboard/widgets", response_model=List[Dict[str, Any]])
def get_dashboard_widgets(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get dashboard widgets for current user
    """
    widgets = session.query(DashboardWidget).filter(
        or_(
            DashboardWidget.owner_user_id == current_user.id,
            DashboardWidget.is_public == True
        ),
        DashboardWidget.is_active == True
    ).order_by(DashboardWidget.position_y, DashboardWidget.position_x).all()
    
    return [
        {
            "id": widget.id,
            "widget_name": widget.widget_name,
            "widget_title": widget.widget_title,
            "widget_description": widget.widget_description,
            "widget_type": widget.widget_type,
            "chart_type": widget.chart_type,
            "position": {
                "x": widget.position_x,
                "y": widget.position_y,
                "width": widget.width,
                "height": widget.height
            },
            "refresh_interval_minutes": widget.refresh_interval_minutes,
            "cached_data": widget.cached_data,
            "last_updated": widget.last_updated.isoformat() if widget.last_updated else None,
            "needs_refresh": widget.needs_refresh(),
            "is_owner": widget.owner_user_id == current_user.id
        } for widget in widgets
    ]


@router.post("/dashboard/widgets", response_model=Dict[str, Any])
def create_dashboard_widget(
    widget_name: str,
    widget_title: str,
    widget_type: str,
    data_source: str,
    query_config: Dict[str, Any],
    widget_description: Optional[str] = None,
    chart_type: Optional[str] = None,
    position_x: int = 0,
    position_y: int = 0,
    width: int = 4,
    height: int = 4,
    refresh_interval_minutes: int = 30,
    is_public: bool = False,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Create a new dashboard widget
    """
    widget = DashboardWidget(
        widget_name=widget_name,
        widget_title=widget_title,
        widget_description=widget_description,
        widget_type=widget_type,
        chart_type=chart_type,
        data_source=data_source,
        query_config=query_config,
        position_x=position_x,
        position_y=position_y,
        width=width,
        height=height,
        refresh_interval_minutes=refresh_interval_minutes,
        is_public=is_public,
        owner_user_id=current_user.id
    )
    
    session.add(widget)
    session.commit()
    session.refresh(widget)
    
    return {
        "id": widget.id,
        "widget_name": widget.widget_name,
        "message": "Dashboard widget created successfully"
    }


@router.put("/dashboard/widgets/{widget_id}", response_model=Dict[str, Any])
def update_dashboard_widget(
    widget_id: int,
    widget_title: Optional[str] = None,
    widget_description: Optional[str] = None,
    position_x: Optional[int] = None,
    position_y: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    refresh_interval_minutes: Optional[int] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Update dashboard widget
    """
    widget = session.query(DashboardWidget).filter(DashboardWidget.id == widget_id).first()
    
    if not widget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found"
        )
    
    # Check ownership
    if widget.owner_user_id != current_user.id and current_user.user_type.value not in ["app_admin", "app_super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this widget"
        )
    
    # Update fields
    if widget_title is not None:
        widget.widget_title = widget_title
    if widget_description is not None:
        widget.widget_description = widget_description
    if position_x is not None:
        widget.position_x = position_x
    if position_y is not None:
        widget.position_y = position_y
    if width is not None:
        widget.width = width
    if height is not None:
        widget.height = height
    if refresh_interval_minutes is not None:
        widget.refresh_interval_minutes = refresh_interval_minutes
    if is_active is not None:
        widget.is_active = is_active
    
    widget.updated_at = datetime.utcnow()
    session.commit()
    
    return {
        "id": widget.id,
        "message": "Widget updated successfully"
    }


@router.delete("/dashboard/widgets/{widget_id}", response_model=Dict[str, Any])
def delete_dashboard_widget(
    widget_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Delete dashboard widget
    """
    widget = session.query(DashboardWidget).filter(DashboardWidget.id == widget_id).first()
    
    if not widget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found"
        )
    
    # Check ownership
    if widget.owner_user_id != current_user.id and current_user.user_type.value not in ["app_admin", "app_super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this widget"
        )
    
    session.delete(widget)
    session.commit()
    
    return {
        "message": "Widget deleted successfully"
    }


@router.get("/metrics/business", response_model=List[Dict[str, Any]])
def get_business_metrics(
    category: Optional[str] = None,
    metric_type: Optional[MetricType] = None,
    granularity: TimeGranularity = TimeGranularity.DAY,
    period_days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get business metrics
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=period_days)
    
    query = session.query(BusinessMetric).filter(
        BusinessMetric.period_start >= start_date,
        BusinessMetric.granularity == granularity
    )
    
    if category:
        query = query.filter(BusinessMetric.category == category)
    
    if metric_type:
        query = query.filter(BusinessMetric.metric_type == metric_type)
    
    metrics = query.order_by(desc(BusinessMetric.period_start)).all()
    
    return [
        {
            "id": metric.id,
            "metric_name": metric.metric_name,
            "metric_type": metric.metric_type,
            "category": metric.category,
            "value": float(metric.value),
            "previous_value": float(metric.previous_value) if metric.previous_value else None,
            "growth_rate": float(metric.growth_rate) if metric.growth_rate else None,
            "target_value": float(metric.target_value) if metric.target_value else None,
            "variance": float(metric.variance) if metric.variance else None,
            "unit": metric.unit,
            "period_start": metric.period_start.isoformat(),
            "period_end": metric.period_end.isoformat(),
            "granularity": metric.granularity,
            "dimensions": metric.dimensions
        } for metric in metrics
    ]


# Helper functions for report generation
def _generate_sales_report(session: Session, start_date: datetime, end_date: datetime, filters: Dict[str, Any]) -> Dict[str, Any]:
    """Generate sales report data"""
    from app.models.order import Order, OrderStatus
    
    query = session.query(Order).filter(
        Order.created_at >= start_date,
        Order.created_at <= end_date
    )
    
    if filters.get('vendor_id'):
        query = query.filter(Order.vendor_id == filters['vendor_id'])
    
    if filters.get('status'):
        query = query.filter(Order.status == filters['status'])
    
    orders = query.all()
    
    return {
        "records": [
            {
                "order_id": order.id,
                "vendor_id": order.vendor_id,
                "customer_phone": order.customer_phone,
                "total_amount": float(order.total_amount),
                "status": order.status.value,
                "payment_method": order.payment_method.value if order.payment_method else None,
                "created_at": order.created_at.isoformat()
            } for order in orders
        ],
        "metadata": {
            "total_orders": len(orders),
            "total_revenue": sum([float(order.total_amount) for order in orders]),
            "avg_order_value": sum([float(order.total_amount) for order in orders]) / len(orders) if orders else 0
        }
    }


def _generate_revenue_report(session: Session, start_date: datetime, end_date: datetime, filters: Dict[str, Any]) -> Dict[str, Any]:
    """Generate revenue report data"""
    from app.models.order import Order, OrderStatus
    from app.models.vendor import Vendor
    
    revenue_data = session.query(
        Vendor.business_name,
        func.sum(Order.total_amount).label('revenue'),
        func.count(Order.id).label('order_count')
    ).join(Order).filter(
        Order.created_at >= start_date,
        Order.created_at <= end_date,
        Order.status.in_([OrderStatus.DELIVERED, OrderStatus.COMPLETED])
    ).group_by(Vendor.business_name).all()
    
    return {
        "records": [
            {
                "vendor_name": item.business_name,
                "revenue": float(item.revenue),
                "order_count": item.order_count,
                "avg_order_value": float(item.revenue) / item.order_count
            } for item in revenue_data
        ],
        "metadata": {
            "total_vendors": len(revenue_data),
            "total_revenue": sum([float(item.revenue) for item in revenue_data])
        }
    }


def _generate_vendor_report(session: Session, start_date: datetime, end_date: datetime, filters: Dict[str, Any]) -> Dict[str, Any]:
    """Generate vendor report data"""
    from app.models.vendor import Vendor
    from app.models.order import Order
    from app.models.product import Product
    
    vendors = session.query(Vendor).all()
    
    return {
        "records": [
            {
                "vendor_id": vendor.id,
                "business_name": vendor.business_name,
                "email": vendor.email,
                "phone": vendor.phone,
                "subscription_status": vendor.subscription_status.value if vendor.subscription_status else None,
                "created_at": vendor.created_at.isoformat()
            } for vendor in vendors
        ],
        "metadata": {
            "total_vendors": len(vendors)
        }
    }


def _generate_product_report(session: Session, start_date: datetime, end_date: datetime, filters: Dict[str, Any]) -> Dict[str, Any]:
    """Generate product report data"""
    from app.models.product import Product
    
    query = session.query(Product)
    
    if filters.get('category'):
        query = query.filter(Product.category == filters['category'])
    
    products = query.all()
    
    return {
        "records": [
            {
                "product_id": product.id,
                "name": product.name,
                "category": product.category,
                "price": float(product.price),
                "vendor_id": product.vendor_id,
                "status": product.status.value,
                "created_at": product.created_at.isoformat()
            } for product in products
        ],
        "metadata": {
            "total_products": len(products)
        }
    }


def _calculate_summary_metrics(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate summary metrics for report"""
    records = report_data.get('records', [])
    metadata = report_data.get('metadata', {})
    
    return {
        "record_count": len(records),
        "generated_at": datetime.utcnow().isoformat(),
        **metadata
    }
