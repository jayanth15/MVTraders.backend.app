"""
Analytics and reporting models for business intelligence.
"""

from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from datetime import datetime, date
from enum import Enum
from decimal import Decimal

from app.models.base import TimestampModel


class ReportType(str, Enum):
    """Report types"""
    SALES = "sales"
    REVENUE = "revenue"
    VENDOR = "vendor"
    PRODUCT = "product"
    CUSTOMER = "customer"
    SUBSCRIPTION = "subscription"
    USAGE = "usage"
    PERFORMANCE = "performance"
    FINANCIAL = "financial"
    CUSTOM = "custom"


class ReportFormat(str, Enum):
    """Report output formats"""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    EXCEL = "excel"


class ReportStatus(str, Enum):
    """Report generation status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class MetricType(str, Enum):
    """Metric types for analytics"""
    COUNT = "count"
    SUM = "sum"
    AVERAGE = "average"
    PERCENTAGE = "percentage"
    RATIO = "ratio"
    GROWTH_RATE = "growth_rate"
    CONVERSION_RATE = "conversion_rate"


class TimeGranularity(str, Enum):
    """Time granularity for analytics"""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class AlertCondition(str, Enum):
    """Alert condition operators"""
    GREATER_THAN = ">"
    LESS_THAN = "<"
    EQUAL = "="
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    NOT_EQUAL = "!="


class AlertStatus(str, Enum):
    """Alert status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRIGGERED = "triggered"
    RESOLVED = "resolved"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnalyticsReport(SQLModel, table=True):
    """
    Generated analytics reports
    """
    __tablename__ = "analytics_reports"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Report identification
    report_name: str = Field(max_length=200, description="Report name")
    report_type: ReportType = Field(description="Type of report")
    report_description: Optional[str] = Field(default=None, max_length=500, description="Report description")
    
    # Report parameters
    date_range_start: datetime = Field(description="Report date range start")
    date_range_end: datetime = Field(description="Report date range end")
    filters: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON), description="Report filters")
    
    # Report generation
    generated_by_user_id: int = Field(foreign_key="users.id", description="User who generated the report")
    status: ReportStatus = Field(default=ReportStatus.PENDING, description="Report generation status")
    
    # Report output
    format: ReportFormat = Field(description="Report output format")
    file_path: Optional[str] = Field(default=None, max_length=500, description="Generated file path")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    
    # Report data
    report_data: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON), description="Report data")
    summary_metrics: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON), description="Summary metrics")
    
    # Report metadata
    execution_time_ms: Optional[int] = Field(default=None, description="Report generation time in milliseconds")
    record_count: Optional[int] = Field(default=None, description="Number of records in report")
    
    # Expiration
    expires_at: Optional[datetime] = Field(default=None, description="Report expiration date")
    
    # Relationships
    generated_by: Optional["User"] = Relationship()
    
    def is_expired(self) -> bool:
        """Check if report has expired"""
        if not self.expires_at:
            return False
        return self.expires_at < datetime.utcnow()
    
    def __str__(self):
        return f"Report: {self.report_name} ({self.report_type}) - {self.status}"


class DashboardWidget(SQLModel, table=True):
    """
    Dashboard widgets for analytics display
    """
    __tablename__ = "dashboard_widgets"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Widget identification
    widget_name: str = Field(max_length=200, description="Widget name")
    widget_title: str = Field(max_length=200, description="Widget display title")
    widget_description: Optional[str] = Field(default=None, max_length=500, description="Widget description")
    
    # Widget configuration
    widget_type: str = Field(max_length=50, description="Widget type (chart, table, metric, etc.)")
    chart_type: Optional[str] = Field(default=None, max_length=50, description="Chart type for chart widgets")
    
    # Data source
    data_source: str = Field(max_length=100, description="Data source for widget")
    query_config: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON), description="Query configuration")
    
    # Widget layout
    position_x: int = Field(default=0, description="Widget X position on dashboard")
    position_y: int = Field(default=0, description="Widget Y position on dashboard")
    width: int = Field(default=4, description="Widget width")
    height: int = Field(default=4, description="Widget height")
    
    # Widget settings
    refresh_interval_minutes: int = Field(default=30, description="Auto-refresh interval in minutes")
    is_active: bool = Field(default=True, description="Whether widget is active")
    is_public: bool = Field(default=False, description="Whether widget is publicly accessible")
    
    # Widget data
    cached_data: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON), description="Cached widget data")
    last_updated: Optional[datetime] = Field(default=None, description="Last data update")
    
    # Access control
    owner_user_id: int = Field(foreign_key="users.id", description="Widget owner")
    
    # Relationships
    owner: Optional["User"] = Relationship()
    
    def needs_refresh(self) -> bool:
        """Check if widget data needs refresh"""
        if not self.last_updated:
            return True
        
        refresh_threshold = datetime.utcnow() - timedelta(minutes=self.refresh_interval_minutes)
        return self.last_updated < refresh_threshold
    
    def __str__(self):
        return f"Widget: {self.widget_title} ({self.widget_type})"


class BusinessMetric(SQLModel, table=True):
    """
    Business metrics tracking
    """
    __tablename__ = "business_metrics"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Metric identification
    metric_name: str = Field(max_length=200, description="Metric name")
    metric_type: MetricType = Field(description="Type of metric")
    category: str = Field(max_length=100, description="Metric category")
    
    # Metric value
    value: Decimal = Field(description="Metric value")
    previous_value: Optional[Decimal] = Field(default=None, description="Previous period value")
    
    # Time period
    period_start: datetime = Field(description="Metric period start")
    period_end: datetime = Field(description="Metric period end")
    granularity: TimeGranularity = Field(description="Time granularity")
    
    # Metric metadata
    unit: Optional[str] = Field(default=None, max_length=50, description="Metric unit (%, $, count, etc.)")
    dimensions: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON), description="Metric dimensions")
    
    # Calculations
    growth_rate: Optional[Decimal] = Field(default=None, description="Growth rate vs previous period")
    target_value: Optional[Decimal] = Field(default=None, description="Target value for metric")
    variance: Optional[Decimal] = Field(default=None, description="Variance from target")
    
    def calculate_growth_rate(self) -> Optional[Decimal]:
        """Calculate growth rate vs previous value"""
        if not self.previous_value or self.previous_value == 0:
            return None
        
        growth = ((self.value - self.previous_value) / self.previous_value) * 100
        return Decimal(str(round(float(growth), 4)))
    
    def calculate_variance(self) -> Optional[Decimal]:
        """Calculate variance from target"""
        if not self.target_value:
            return None
        
        variance = ((self.value - self.target_value) / self.target_value) * 100
        return Decimal(str(round(float(variance), 4)))
    
    def __str__(self):
        return f"Metric: {self.metric_name} = {self.value} {self.unit or ''}"


class AnalyticsQuery(SQLModel, table=True):
    """
    Saved analytics queries for reuse
    """
    __tablename__ = "analytics_queries"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Query identification
    query_name: str = Field(max_length=200, description="Query name")
    query_description: Optional[str] = Field(default=None, max_length=500, description="Query description")
    
    # Query definition
    query_sql: str = Field(description="SQL query")
    query_parameters: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON), description="Query parameters")
    
    # Query metadata
    data_sources: List[str] = Field(default_factory=list, sa_column=Column(JSON), description="Data sources used")
    expected_columns: List[str] = Field(default_factory=list, sa_column=Column(JSON), description="Expected result columns")
    
    # Access control
    created_by_user_id: int = Field(foreign_key="users.id", description="Query creator")
    is_public: bool = Field(default=False, description="Whether query is publicly accessible")
    
    # Usage tracking
    usage_count: int = Field(default=0, description="Number of times query has been executed")
    last_executed: Optional[datetime] = Field(default=None, description="Last execution timestamp")
    
    # Relationships
    created_by: Optional["User"] = Relationship()
    
    def __str__(self):
        return f"Query: {self.query_name}"


class DataExport(SQLModel, table=True):
    """
    Data export jobs and history
    """
    __tablename__ = "data_exports"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Export identification
    export_name: str = Field(max_length=200, description="Export name")
    export_type: str = Field(max_length=100, description="Type of data being exported")
    
    # Export parameters
    filters: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON), description="Export filters")
    columns: List[str] = Field(default_factory=list, sa_column=Column(JSON), description="Columns to export")
    
    # Export settings
    format: ReportFormat = Field(description="Export format")
    include_headers: bool = Field(default=True, description="Include column headers")
    
    # Export status
    status: ReportStatus = Field(default=ReportStatus.PENDING, description="Export status")
    file_path: Optional[str] = Field(default=None, max_length=500, description="Generated file path")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    record_count: Optional[int] = Field(default=None, description="Number of records exported")
    
    # Export metadata
    requested_by_user_id: int = Field(foreign_key="users.id", description="User who requested export")
    execution_time_ms: Optional[int] = Field(default=None, description="Export execution time")
    error_message: Optional[str] = Field(default=None, max_length=500, description="Error message if failed")
    
    # Expiration
    expires_at: Optional[datetime] = Field(default=None, description="Export file expiration")
    
    # Relationships
    requested_by: Optional["User"] = Relationship()
    
    def is_expired(self) -> bool:
        """Check if export has expired"""
        if not self.expires_at:
            return False
        return self.expires_at < datetime.utcnow()
    
    def __str__(self):
        return f"Export: {self.export_name} ({self.export_type}) - {self.status}"


class AlertRule(SQLModel, table=True):
    """
    Analytics alert rules for automated notifications
    """
    __tablename__ = "alert_rules"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Alert identification
    alert_name: str = Field(max_length=200, description="Alert rule name")
    alert_description: Optional[str] = Field(default=None, max_length=500, description="Alert description")
    
    # Alert conditions
    metric_name: str = Field(max_length=200, description="Metric to monitor")
    condition_operator: str = Field(max_length=20, description="Condition operator (>, <, =, etc.)")
    threshold_value: Decimal = Field(description="Threshold value")
    
    # Alert settings
    is_active: bool = Field(default=True, description="Whether alert is active")
    check_interval_minutes: int = Field(default=60, description="Check interval in minutes")
    
    # Notification settings
    notification_channels: List[str] = Field(default_factory=list, sa_column=Column(JSON), description="Notification channels")
    notification_message: Optional[str] = Field(default=None, max_length=500, description="Custom notification message")
    
    # Alert metadata
    created_by_user_id: int = Field(foreign_key="users.id", description="Alert creator")
    last_triggered: Optional[datetime] = Field(default=None, description="Last time alert was triggered")
    trigger_count: int = Field(default=0, description="Number of times alert has been triggered")
    
    # Relationships
    created_by: Optional["User"] = Relationship()
    
    def __str__(self):
        return f"Alert: {self.alert_name} ({self.metric_name} {self.condition_operator} {self.threshold_value})"
