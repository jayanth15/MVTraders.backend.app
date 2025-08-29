"""
Review analytics endpoints for vendors and administrators.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, and_, or_, func
from app.database import get_session
from app.models.review import Review, ReviewSummary, ReviewType, ReviewStatus
from app.models.vendor import Vendor
from app.models.product import Product
from app.models.user import User
from app.core.deps import get_current_user
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/vendor/{vendor_id}/summary", response_model=ReviewSummary)
async def get_vendor_review_summary(
    vendor_id: int,
    session: Session = Depends(get_session)
):
    """Get review summary for a vendor."""
    
    vendor = session.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    summary = session.exec(
        select(ReviewSummary).where(
            ReviewSummary.target_type == ReviewType.VENDOR,
            ReviewSummary.vendor_id == vendor_id
        )
    ).first()
    
    if not summary:
        # Create empty summary if none exists
        summary = ReviewSummary(
            target_type=ReviewType.VENDOR,
            vendor_id=vendor_id,
            total_reviews=0,
            average_rating=0.0,
            rating_distribution={"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        )
    
    return summary


@router.get("/product/{product_id}/summary", response_model=ReviewSummary)
async def get_product_review_summary(
    product_id: int,
    session: Session = Depends(get_session)
):
    """Get review summary for a product."""
    
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    summary = session.exec(
        select(ReviewSummary).where(
            ReviewSummary.target_type == ReviewType.PRODUCT,
            ReviewSummary.product_id == product_id
        )
    ).first()
    
    if not summary:
        # Create empty summary if none exists
        summary = ReviewSummary(
            target_type=ReviewType.PRODUCT,
            product_id=product_id,
            total_reviews=0,
            average_rating=0.0,
            rating_distribution={"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        )
    
    return summary


@router.get("/vendor/{vendor_id}/analytics", response_model=dict)
async def get_vendor_review_analytics(
    vendor_id: int,
    days: int = Query(default=30, ge=1, le=365),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get detailed review analytics for a vendor (vendor owner or admin only)."""
    
    vendor = session.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    # Check permission
    if vendor.user_id != current_user.id and current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to vendor analytics"
        )
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get reviews in date range
    reviews = session.exec(
        select(Review).where(
            Review.vendor_id == vendor_id,
            Review.status == ReviewStatus.APPROVED,
            Review.created_at >= start_date,
            Review.created_at <= end_date
        )
    ).all()
    
    # Calculate analytics
    total_reviews = len(reviews)
    if total_reviews == 0:
        return {
            "period_days": days,
            "total_reviews": 0,
            "average_rating": 0.0,
            "rating_trend": [],
            "verified_percentage": 0.0,
            "engagement_metrics": {
                "total_helpful_votes": 0,
                "total_reports": 0,
                "average_helpful_votes_per_review": 0.0
            }
        }
    
    average_rating = sum(r.rating for r in reviews) / total_reviews
    verified_reviews = [r for r in reviews if r.is_verified_purchase]
    verified_percentage = (len(verified_reviews) / total_reviews) * 100
    
    # Rating trend (weekly)
    rating_trend = []
    for week in range(min(days // 7, 4)):
        week_start = end_date - timedelta(days=(week + 1) * 7)
        week_end = end_date - timedelta(days=week * 7)
        
        week_reviews = [r for r in reviews if week_start <= r.created_at < week_end]
        if week_reviews:
            week_avg = sum(r.rating for r in week_reviews) / len(week_reviews)
            rating_trend.append({
                "week": f"Week {week + 1}",
                "average_rating": round(week_avg, 2),
                "review_count": len(week_reviews)
            })
    
    # Engagement metrics
    total_helpful_votes = sum(r.helpful_count for r in reviews)
    total_reports = sum(r.reported_count for r in reviews)
    
    return {
        "period_days": days,
        "total_reviews": total_reviews,
        "average_rating": round(average_rating, 2),
        "rating_trend": rating_trend,
        "verified_percentage": round(verified_percentage, 1),
        "engagement_metrics": {
            "total_helpful_votes": total_helpful_votes,
            "total_reports": total_reports,
            "average_helpful_votes_per_review": round(total_helpful_votes / total_reviews, 2) if total_reviews > 0 else 0.0
        }
    }


@router.get("/product/{product_id}/analytics", response_model=dict)
async def get_product_review_analytics(
    product_id: int,
    days: int = Query(default=30, ge=1, le=365),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get detailed review analytics for a product (vendor owner or admin only)."""
    
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check permission - product owner or admin
    vendor = session.get(Vendor, product.vendor_id)
    if vendor.user_id != current_user.id and current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to product analytics"
        )
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get reviews in date range
    reviews = session.exec(
        select(Review).where(
            Review.product_id == product_id,
            Review.status == ReviewStatus.APPROVED,
            Review.created_at >= start_date,
            Review.created_at <= end_date
        )
    ).all()
    
    # Calculate analytics
    total_reviews = len(reviews)
    if total_reviews == 0:
        return {
            "period_days": days,
            "total_reviews": 0,
            "average_rating": 0.0,
            "rating_distribution": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
            "verified_percentage": 0.0,
            "recent_reviews": []
        }
    
    average_rating = sum(r.rating for r in reviews) / total_reviews
    verified_reviews = [r for r in reviews if r.is_verified_purchase]
    verified_percentage = (len(verified_reviews) / total_reviews) * 100
    
    # Rating distribution
    distribution = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    for review in reviews:
        star_rating = str(int(review.rating))
        distribution[star_rating] += 1
    
    # Recent reviews (last 5)
    recent_reviews = sorted(reviews, key=lambda r: r.created_at, reverse=True)[:5]
    recent_review_data = [
        {
            "id": r.id,
            "rating": r.rating,
            "title": r.title,
            "content": r.content[:100] + "..." if len(r.content) > 100 else r.content,
            "is_verified_purchase": r.is_verified_purchase,
            "created_at": r.created_at,
            "helpful_count": r.helpful_count
        }
        for r in recent_reviews
    ]
    
    return {
        "period_days": days,
        "total_reviews": total_reviews,
        "average_rating": round(average_rating, 2),
        "rating_distribution": distribution,
        "verified_percentage": round(verified_percentage, 1),
        "recent_reviews": recent_review_data
    }


@router.get("/top-rated", response_model=dict)
async def get_top_rated_items(
    item_type: str = Query(description="Type: 'vendors' or 'products'"),
    limit: int = Query(default=10, le=50),
    min_reviews: int = Query(default=5, ge=1),
    session: Session = Depends(get_session)
):
    """Get top-rated vendors or products."""
    
    if item_type not in ["vendors", "products"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item type must be 'vendors' or 'products'"
        )
    
    target_type = ReviewType.VENDOR if item_type == "vendors" else ReviewType.PRODUCT
    
    # Get summaries with minimum review count
    summaries = session.exec(
        select(ReviewSummary)
        .where(
            ReviewSummary.target_type == target_type,
            ReviewSummary.total_reviews >= min_reviews
        )
        .order_by(ReviewSummary.average_rating.desc(), ReviewSummary.total_reviews.desc())
        .limit(limit)
    ).all()
    
    results = []
    for summary in summaries:
        if item_type == "vendors":
            vendor = session.get(Vendor, summary.vendor_id)
            if vendor:
                results.append({
                    "id": vendor.id,
                    "name": vendor.business_name,
                    "average_rating": summary.average_rating,
                    "total_reviews": summary.total_reviews,
                    "verified_reviews": summary.verified_reviews
                })
        else:
            product = session.get(Product, summary.product_id)
            if product:
                results.append({
                    "id": product.id,
                    "name": product.name,
                    "average_rating": summary.average_rating,
                    "total_reviews": summary.total_reviews,
                    "verified_reviews": summary.verified_reviews
                })
    
    return {
        "item_type": item_type,
        "min_reviews": min_reviews,
        "results": results
    }
