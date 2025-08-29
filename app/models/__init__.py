"""
Database models package
"""
from app.models.base import BaseModel, UUIDModel, TimestampModel, SoftDeleteModel
from app.models.user import User, UserType, UserRead, UserCreate, UserUpdate, UserLogin, PasswordChange

# Phase 3: Business entity models
from app.models.vendor import (
    Vendor, VendorRead, VendorCreate, VendorUpdate,
    SubscriptionPlan, SubscriptionStatus
)
from app.models.organization import (
    Organization, OrganizationMember, OrganizationRole, VerificationStatus
)
from app.models.product import (
    Product, ProductRead, ProductCreate, ProductUpdate, ProductApproval,
    ProductStatus, ProductCategory
)

# Phase 4: Order management models
from app.models.address import (
    Address, AddressRead, AddressCreate, AddressUpdate, AddressType
)
from app.models.order import (
    Order, OrderItem, OrderRead, OrderCreate, OrderUpdate,
    OrderItemRead, OrderItemCreate, OrderStatusUpdate, PaymentUpdate,
    OrderStatus, PaymentStatus, PaymentMethod
)
from app.models.order_form import (
    OrderForm, FormSubmission, OrderFormRead, OrderFormCreate, OrderFormUpdate,
    FormSubmissionRead, FormSubmissionCreate, FormSubmissionUpdate,
    FormFieldSchema, FormFieldOption, FormFieldValidation, OrderFormApproval,
    FieldType, ValidationRule
)

# Phase 6: Review and rating models
from app.models.review import (
    Review, ReviewVote, ReviewReport, ReviewSummary, ReviewTemplate,
    ReviewType, ReviewStatus
)

# Phase 7: Subscription and billing models
from app.models.subscription import (
    SubscriptionPlan as NewSubscriptionPlan, Subscription, Payment,
    UsageRecord, Invoice, BillingAddress,
    SubscriptionPlanType, BillingCycle, SubscriptionStatus as NewSubscriptionStatus,
    PaymentStatus as NewPaymentStatus, PaymentMethod as NewPaymentMethod
)

# Phase 8: Analytics and reporting models
from app.models.analytics import (
    AnalyticsReport, DashboardWidget, BusinessMetric, AnalyticsQuery,
    DataExport, AlertRule,
    ReportType, ReportFormat, ReportStatus, MetricType, TimeGranularity
)

# Phase 9: Advanced search and discovery models
from app.models.search import (
    SavedSearch, SearchFilter, SearchSuggestion, SearchLog, UserRecommendation,
    SearchAnalytics, RecommendationModel, SearchTrend, UserSearchProfile, SmartFilter,
    SearchQuery, SearchResult, SearchInteraction, SearchSession, RecommendationEvent,
    SearchType, SearchIntent, FilterType
)

__all__ = [
    # Base models
    "BaseModel",
    "UUIDModel", 
    "TimestampModel",
    "SoftDeleteModel",
    
    # User models
    "User",
    "UserType",
    "UserRead",
    "UserCreate", 
    "UserUpdate",
    "UserLogin",
    "PasswordChange",
    
    # Vendor models
    "Vendor",
    "VendorRead",
    "VendorCreate",
    "VendorUpdate",
    "SubscriptionPlan",
    "SubscriptionStatus",
    
    # Organization models
    "Organization",
    "OrganizationMember", 
    "OrganizationRole",
    "VerificationStatus",
    
    # Product models
    "Product",
    "ProductRead",
    "ProductCreate",
    "ProductUpdate",
    "ProductApproval",
    "ProductStatus",
    "ProductCategory",
    
    # Address models
    "Address",
    "AddressRead",
    "AddressCreate",
    "AddressUpdate",
    "AddressType",
    
    # Order models
    "Order",
    "OrderItem",
    "OrderRead",
    "OrderCreate",
    "OrderUpdate",
    "OrderItemRead",
    "OrderItemCreate",
    "OrderStatusUpdate",
    "PaymentUpdate",
    "OrderStatus",
    "PaymentStatus",
    "PaymentMethod",
    
    # Order form models
    "OrderForm",
    "FormSubmission",
    "OrderFormRead",
    "OrderFormCreate",
    "OrderFormUpdate",
    "FormSubmissionRead",
    "FormSubmissionCreate",
    "FormSubmissionUpdate",
    "FormFieldSchema",
    "FormFieldOption",
    "FormFieldValidation",
    "OrderFormApproval",
    "FieldType",
    "ValidationRule",
    
    # Review models
    "Review",
    "ReviewVote",
    "ReviewReport", 
    "ReviewSummary",
    "ReviewTemplate",
    "ReviewType",
    "ReviewStatus",
    
    # Subscription models
    "NewSubscriptionPlan",
    "Subscription",
    "Payment",
    "UsageRecord",
    "Invoice",
    "BillingAddress",
    "SubscriptionPlanType",
    "BillingCycle",
    "NewSubscriptionStatus",
    "NewPaymentStatus",
    "NewPaymentMethod",
    
    # Analytics models
    "AnalyticsReport",
    "DashboardWidget",
    "BusinessMetric",
    "AnalyticsQuery",
    "DataExport",
    "AlertRule",
    "ReportType",
    "ReportFormat",
    "ReportStatus",
    "MetricType",
    "TimeGranularity",
    
    # Search and discovery models
    "SavedSearch",
    "SearchFilter", 
    "SearchSuggestion",
    "SearchLog",
    "UserRecommendation",
    "SearchAnalytics",
    "RecommendationModel",
    "SearchTrend",
    "UserSearchProfile",
    "SmartFilter",
    "SearchQuery",
    "SearchResult", 
    "SearchInteraction",
    "SearchSession",
    "RecommendationEvent",
    "SearchType",
    "SearchIntent",
    "FilterType",
]
