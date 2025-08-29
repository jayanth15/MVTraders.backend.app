"""
Saved queries and data export API endpoints.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, text
from datetime import datetime, timedelta
import json
import csv
import io
import xlsxwriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.core.deps import get_current_user, get_session
from app.models.user import User
from app.models.analytics import (
    AnalyticsQuery, DataExport, ReportFormat, ReportStatus, ReportType
)

router = APIRouter()


@router.post("/queries", response_model=Dict[str, Any])
def save_query(
    query_name: str,
    query_description: str,
    query_type: ReportType,
    sql_query: str,
    parameters: Optional[Dict[str, Any]] = None,
    is_public: bool = False,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Save a new analytics query
    """
    # Validate SQL query (basic validation)
    if not sql_query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SQL query cannot be empty"
        )
    
    # Check for potentially dangerous SQL commands
    dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
    query_upper = sql_query.upper()
    
    for keyword in dangerous_keywords:
        if keyword in query_upper:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SQL query contains potentially dangerous keyword: {keyword}"
            )
    
    saved_query = AnalyticsQuery(
        query_name=query_name,
        query_description=query_description,
        query_type=query_type,
        sql_query=sql_query,
        parameters=parameters or {},
        is_public=is_public,
        owner_user_id=current_user.id
    )
    
    session.add(saved_query)
    session.commit()
    session.refresh(saved_query)
    
    return {
        "id": saved_query.id,
        "query_name": saved_query.query_name,
        "message": "Query saved successfully"
    }


@router.get("/queries", response_model=List[Dict[str, Any]])
def get_saved_queries(
    query_type: Optional[ReportType] = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get saved analytics queries
    """
    query = session.query(AnalyticsQuery).filter(
        or_(
            AnalyticsQuery.owner_user_id == current_user.id,
            AnalyticsQuery.is_public == True
        )
    )
    
    if query_type:
        query = query.filter(AnalyticsQuery.query_type == query_type)
    
    queries = query.order_by(desc(AnalyticsQuery.created_at)).offset(offset).limit(limit).all()
    
    return [
        {
            "id": q.id,
            "query_name": q.query_name,
            "query_description": q.query_description,
            "query_type": q.query_type,
            "sql_query": q.sql_query,
            "parameters": q.parameters,
            "is_public": q.is_public,
            "execution_count": q.execution_count,
            "last_executed_at": q.last_executed_at.isoformat() if q.last_executed_at else None,
            "avg_execution_time_ms": q.avg_execution_time_ms,
            "created_at": q.created_at.isoformat(),
            "is_owner": q.owner_user_id == current_user.id
        } for q in queries
    ]


@router.get("/queries/{query_id}", response_model=Dict[str, Any])
def get_query_details(
    query_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get detailed query information
    """
    saved_query = session.query(AnalyticsQuery).filter(AnalyticsQuery.id == query_id).first()
    
    if not saved_query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found"
        )
    
    # Check access permissions
    if (not saved_query.is_public and 
        saved_query.owner_user_id != current_user.id and 
        current_user.user_type.value not in ["app_admin", "app_super_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this query"
        )
    
    return {
        "id": saved_query.id,
        "query_name": saved_query.query_name,
        "query_description": saved_query.query_description,
        "query_type": saved_query.query_type,
        "sql_query": saved_query.sql_query,
        "parameters": saved_query.parameters,
        "is_public": saved_query.is_public,
        "execution_count": saved_query.execution_count,
        "last_executed_at": saved_query.last_executed_at.isoformat() if saved_query.last_executed_at else None,
        "avg_execution_time_ms": saved_query.avg_execution_time_ms,
        "created_at": saved_query.created_at.isoformat(),
        "updated_at": saved_query.updated_at.isoformat(),
        "is_owner": saved_query.owner_user_id == current_user.id
    }


@router.post("/queries/{query_id}/execute", response_model=Dict[str, Any])
def execute_saved_query(
    query_id: int,
    parameters: Optional[Dict[str, Any]] = None,
    limit: int = Query(default=1000, le=10000),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Execute a saved analytics query
    """
    saved_query = session.query(AnalyticsQuery).filter(AnalyticsQuery.id == query_id).first()
    
    if not saved_query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found"
        )
    
    # Check access permissions
    if (not saved_query.is_public and 
        saved_query.owner_user_id != current_user.id and 
        current_user.user_type.value not in ["app_admin", "app_super_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this query"
        )
    
    try:
        start_time = datetime.utcnow()
        
        # Prepare SQL query with parameters
        sql_with_params = saved_query.sql_query
        query_params = parameters or saved_query.parameters or {}
        
        # Add LIMIT to prevent excessive data retrieval
        if "LIMIT" not in sql_with_params.upper():
            sql_with_params += f" LIMIT {limit}"
        
        # Execute the query
        result = session.execute(text(sql_with_params), query_params)
        columns = result.keys()
        rows = result.fetchall()
        
        # Convert rows to dictionaries
        data = [dict(zip(columns, row)) for row in rows]
        
        # Calculate execution time
        end_time = datetime.utcnow()
        execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Update query statistics
        saved_query.execution_count += 1
        saved_query.last_executed_at = end_time
        
        # Update average execution time
        if saved_query.avg_execution_time_ms:
            saved_query.avg_execution_time_ms = (
                (saved_query.avg_execution_time_ms * (saved_query.execution_count - 1) + execution_time_ms) / 
                saved_query.execution_count
            )
        else:
            saved_query.avg_execution_time_ms = execution_time_ms
        
        session.commit()
        
        return {
            "query_id": query_id,
            "execution_time_ms": execution_time_ms,
            "row_count": len(data),
            "columns": list(columns),
            "data": data,
            "truncated": len(rows) == limit,
            "executed_at": end_time.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}"
        )


@router.put("/queries/{query_id}", response_model=Dict[str, Any])
def update_saved_query(
    query_id: int,
    query_name: Optional[str] = None,
    query_description: Optional[str] = None,
    sql_query: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    is_public: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Update a saved query
    """
    saved_query = session.query(AnalyticsQuery).filter(AnalyticsQuery.id == query_id).first()
    
    if not saved_query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found"
        )
    
    # Check ownership
    if (saved_query.owner_user_id != current_user.id and 
        current_user.user_type.value not in ["app_admin", "app_super_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this query"
        )
    
    # Update fields
    if query_name is not None:
        saved_query.query_name = query_name
    if query_description is not None:
        saved_query.query_description = query_description
    if sql_query is not None:
        # Validate SQL query
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
        query_upper = sql_query.upper()
        
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"SQL query contains potentially dangerous keyword: {keyword}"
                )
        
        saved_query.sql_query = sql_query
    if parameters is not None:
        saved_query.parameters = parameters
    if is_public is not None:
        saved_query.is_public = is_public
    
    saved_query.updated_at = datetime.utcnow()
    session.commit()
    
    return {
        "id": saved_query.id,
        "message": "Query updated successfully"
    }


@router.delete("/queries/{query_id}", response_model=Dict[str, Any])
def delete_saved_query(
    query_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Delete a saved query
    """
    saved_query = session.query(AnalyticsQuery).filter(AnalyticsQuery.id == query_id).first()
    
    if not saved_query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found"
        )
    
    # Check ownership
    if (saved_query.owner_user_id != current_user.id and 
        current_user.user_type.value not in ["app_admin", "app_super_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this query"
        )
    
    session.delete(saved_query)
    session.commit()
    
    return {
        "message": "Query deleted successfully"
    }


@router.post("/exports", response_model=Dict[str, Any])
def create_data_export(
    export_name: str,
    data_source: str,
    format: ReportFormat,
    query_config: Dict[str, Any],
    filters: Optional[Dict[str, Any]] = None,
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Create a new data export job
    """
    export_job = DataExport(
        export_name=export_name,
        data_source=data_source,
        format=format,
        query_config=query_config,
        filters=filters or {},
        requested_by_user_id=current_user.id,
        status=ReportStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(hours=24)  # Exports expire after 24 hours
    )
    
    session.add(export_job)
    session.commit()
    session.refresh(export_job)
    
    # In a real implementation, you would queue this for background processing
    # For now, we'll simulate immediate processing
    try:
        start_time = datetime.utcnow()
        
        # Generate export data based on data source
        export_data = _generate_export_data(session, data_source, query_config, filters or {})
        
        # Convert data to specified format
        file_content, file_size = _convert_data_to_format(export_data, format, export_name)
        
        # Update export job with results
        end_time = datetime.utcnow()
        processing_time = int((end_time - start_time).total_seconds() * 1000)
        
        export_job.file_path = f"/exports/{export_job.id}/{export_name}.{format.value.lower()}"
        export_job.file_size_bytes = file_size
        export_job.record_count = len(export_data.get('records', []))
        export_job.status = ReportStatus.COMPLETED
        export_job.processing_time_ms = processing_time
        
        session.commit()
        
        return {
            "export_id": export_job.id,
            "status": export_job.status,
            "file_path": export_job.file_path,
            "file_size_bytes": export_job.file_size_bytes,
            "record_count": export_job.record_count,
            "processing_time_ms": processing_time,
            "expires_at": export_job.expires_at.isoformat(),
            "message": "Export job completed successfully"
        }
        
    except Exception as e:
        export_job.status = ReportStatus.FAILED
        export_job.error_message = str(e)
        session.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export job failed: {str(e)}"
        )


@router.get("/exports", response_model=List[Dict[str, Any]])
def get_data_exports(
    status: Optional[ReportStatus] = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get list of data export jobs
    """
    query = session.query(DataExport)
    
    # Filter by user's exports unless admin
    if current_user.user_type.value not in ["app_admin", "app_super_admin"]:
        query = query.filter(DataExport.requested_by_user_id == current_user.id)
    
    if status:
        query = query.filter(DataExport.status == status)
    
    exports = query.order_by(desc(DataExport.created_at)).offset(offset).limit(limit).all()
    
    return [
        {
            "id": export.id,
            "export_name": export.export_name,
            "data_source": export.data_source,
            "format": export.format,
            "status": export.status,
            "file_path": export.file_path,
            "file_size_bytes": export.file_size_bytes,
            "record_count": export.record_count,
            "processing_time_ms": export.processing_time_ms,
            "created_at": export.created_at.isoformat(),
            "expires_at": export.expires_at.isoformat() if export.expires_at else None,
            "is_expired": export.is_expired(),
            "error_message": export.error_message
        } for export in exports
    ]


@router.get("/exports/{export_id}", response_model=Dict[str, Any])
def get_export_details(
    export_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get detailed export information
    """
    export_job = session.query(DataExport).filter(DataExport.id == export_id).first()
    
    if not export_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found"
        )
    
    # Check access permissions
    if (current_user.user_type.value not in ["app_admin", "app_super_admin"] and 
        export_job.requested_by_user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this export"
        )
    
    if export_job.is_expired():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Export has expired"
        )
    
    return {
        "id": export_job.id,
        "export_name": export_job.export_name,
        "data_source": export_job.data_source,
        "format": export_job.format,
        "query_config": export_job.query_config,
        "filters": export_job.filters,
        "status": export_job.status,
        "file_path": export_job.file_path,
        "file_size_bytes": export_job.file_size_bytes,
        "record_count": export_job.record_count,
        "processing_time_ms": export_job.processing_time_ms,
        "created_at": export_job.created_at.isoformat(),
        "expires_at": export_job.expires_at.isoformat() if export_job.expires_at else None,
        "error_message": export_job.error_message
    }


# Helper functions for data export
def _generate_export_data(session: Session, data_source: str, query_config: Dict[str, Any], filters: Dict[str, Any]) -> Dict[str, Any]:
    """Generate data for export based on data source"""
    if data_source == "orders":
        from app.models.order import Order
        orders = session.query(Order).all()
        return {
            "records": [
                {
                    "id": order.id,
                    "vendor_id": order.vendor_id,
                    "customer_phone": order.customer_phone,
                    "total_amount": float(order.total_amount),
                    "status": order.status.value,
                    "created_at": order.created_at.isoformat()
                } for order in orders
            ]
        }
    elif data_source == "products":
        from app.models.product import Product
        products = session.query(Product).all()
        return {
            "records": [
                {
                    "id": product.id,
                    "name": product.name,
                    "category": product.category,
                    "price": float(product.price),
                    "vendor_id": product.vendor_id,
                    "status": product.status.value,
                    "created_at": product.created_at.isoformat()
                } for product in products
            ]
        }
    elif data_source == "vendors":
        from app.models.vendor import Vendor
        vendors = session.query(Vendor).all()
        return {
            "records": [
                {
                    "id": vendor.id,
                    "business_name": vendor.business_name,
                    "email": vendor.email,
                    "phone": vendor.phone,
                    "subscription_status": vendor.subscription_status.value if vendor.subscription_status else None,
                    "created_at": vendor.created_at.isoformat()
                } for vendor in vendors
            ]
        }
    else:
        return {"records": []}


def _convert_data_to_format(data: Dict[str, Any], format: ReportFormat, filename: str) -> tuple[bytes, int]:
    """Convert data to specified export format"""
    records = data.get('records', [])
    
    if format == ReportFormat.JSON:
        content = json.dumps(data, indent=2).encode('utf-8')
        return content, len(content)
    
    elif format == ReportFormat.CSV:
        if not records:
            return b"", 0
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
        content = output.getvalue().encode('utf-8')
        return content, len(content)
    
    elif format == ReportFormat.EXCEL:
        if not records:
            return b"", 0
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()
        
        # Write headers
        headers = list(records[0].keys())
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)
        
        # Write data
        for row, record in enumerate(records, 1):
            for col, header in enumerate(headers):
                worksheet.write(row, col, record.get(header, ''))
        
        workbook.close()
        content = output.getvalue()
        return content, len(content)
    
    elif format == ReportFormat.PDF:
        output = io.BytesIO()
        p = canvas.Canvas(output, pagesize=letter)
        
        # Simple PDF generation (in a real app, you'd use more sophisticated formatting)
        y = 750
        p.drawString(100, y, f"Data Export: {filename}")
        y -= 30
        
        for i, record in enumerate(records[:50]):  # Limit to first 50 records for PDF
            p.drawString(100, y, f"Record {i+1}: {str(record)[:80]}...")
            y -= 20
            if y < 50:
                p.showPage()
                y = 750
        
        p.save()
        content = output.getvalue()
        return content, len(content)
    
    else:
        raise ValueError(f"Unsupported export format: {format}")
