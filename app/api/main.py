"""
Main API router
"""
from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.vendors import router as vendors_router
from app.api.organizations import router as organizations_router
from app.api.products import router as products_router

# Phase 4: Order Management & Workflows
from app.api.v1.endpoints.addresses import router as addresses_router
from app.api.v1.endpoints.orders import router as orders_router
from app.api.v1.endpoints.order_forms import router as order_forms_router

# Phase 6: Reviews & Rating System
from app.api.v1.endpoints.reviews import router as reviews_router
from app.api.v1.endpoints.review_moderation import router as review_moderation_router
from app.api.v1.endpoints.review_analytics import router as review_analytics_router

# Phase 7: Subscription & Billing System
from app.api.v1.endpoints.subscriptions import router as subscriptions_router
from app.api.v1.endpoints.billing import router as billing_router
from app.api.v1.endpoints.admin_subscriptions import router as admin_subscriptions_router
from app.api.v1.endpoints.usage_tracking import router as usage_tracking_router

# Phase 8: Analytics & Reporting Dashboard
from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.reporting import router as reporting_router
from app.api.v1.endpoints.queries import router as queries_router
from app.api.v1.endpoints.alerts import router as alerts_router

# Phase 9: Advanced Search & Discovery Engine
from app.api.v1.endpoints.search import router as search_router
from app.api.v1.endpoints.recommendations import router as recommendations_router


api_router = APIRouter()

# Include authentication routes
api_router.include_router(auth_router)

# Phase 3: Include business entity routes
api_router.include_router(vendors_router)
api_router.include_router(organizations_router)
api_router.include_router(products_router)

# Phase 4: Include order management routes
api_router.include_router(addresses_router, prefix="/addresses", tags=["addresses"])
api_router.include_router(orders_router, prefix="/orders", tags=["orders"])
api_router.include_router(order_forms_router, prefix="/order-forms", tags=["order-forms"])

# Phase 6: Include review and rating routes
api_router.include_router(reviews_router, prefix="/reviews", tags=["reviews"])
api_router.include_router(review_moderation_router, prefix="/admin/reviews", tags=["review-moderation"])
api_router.include_router(review_analytics_router, prefix="/analytics/reviews", tags=["review-analytics"])

# Phase 7: Include subscription and billing routes
api_router.include_router(subscriptions_router, prefix="/subscriptions", tags=["subscriptions"])
api_router.include_router(billing_router, prefix="/billing", tags=["billing"])
api_router.include_router(admin_subscriptions_router, prefix="/admin/subscriptions", tags=["admin-subscriptions"])
api_router.include_router(usage_tracking_router, prefix="/usage", tags=["usage-tracking"])

# Phase 8: Include analytics and reporting routes
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
api_router.include_router(reporting_router, prefix="/reports", tags=["reporting"])
api_router.include_router(queries_router, prefix="/queries", tags=["saved-queries"])
api_router.include_router(alerts_router, prefix="/alerts", tags=["alerts"])

# Phase 9: Include search and discovery routes
api_router.include_router(search_router, prefix="/search", tags=["search"])
api_router.include_router(recommendations_router, prefix="/recommendations", tags=["recommendations"])

# Health check endpoint
@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "MvTraders API is running"}
