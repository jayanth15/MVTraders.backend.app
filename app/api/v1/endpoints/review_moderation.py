"""
Review moderation endpoints for administrators.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, and_, or_, func
from app.database import get_session
from app.models.review import Review, ReviewReport, ReviewSummary, ReviewStatus
from app.models.user import User
from app.core.deps import get_current_user, require_admin
from datetime import datetime

router = APIRouter()


@router.get("/pending", response_model=List[Review])
async def get_pending_reviews(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Get pending reviews for moderation (admin only)."""
    
    reviews = session.exec(
        select(Review)
        .where(Review.status == ReviewStatus.PENDING)
        .offset(offset)
        .limit(limit)
        .order_by(Review.created_at.asc())
    ).all()
    
    return reviews


@router.put("/{review_id}/moderate", response_model=Review)
async def moderate_review(
    review_id: int,
    moderation_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Moderate a review (admin only)."""
    
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    new_status = moderation_data.get("status")
    if new_status not in [ReviewStatus.APPROVED, ReviewStatus.REJECTED, ReviewStatus.FLAGGED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be 'approved', 'rejected', or 'flagged'"
        )
    
    review.status = new_status
    review.moderated_by = current_user.id
    review.moderated_at = datetime.utcnow()
    review.moderation_notes = moderation_data.get("notes")
    
    session.add(review)
    session.commit()
    session.refresh(review)
    
    # Update review summary if approved
    if new_status == ReviewStatus.APPROVED:
        from app.api.v1.endpoints.reviews import update_review_summary
        await update_review_summary(session, review.review_type, review.vendor_id, review.product_id)
    
    return review


@router.get("/reports", response_model=List[ReviewReport])
async def get_review_reports(
    status: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Get review reports (admin only)."""
    
    query = select(ReviewReport)
    
    if status:
        query = query.where(ReviewReport.status == status)
    
    reports = session.exec(
        query.offset(offset).limit(limit).order_by(ReviewReport.created_at.desc())
    ).all()
    
    return reports


@router.put("/reports/{report_id}/resolve", response_model=ReviewReport)
async def resolve_review_report(
    report_id: int,
    resolution_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Resolve a review report (admin only)."""
    
    report = session.get(ReviewReport, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    report.status = "resolved"
    report.resolved_by = current_user.id
    report.resolved_at = datetime.utcnow()
    report.resolution_notes = resolution_data.get("notes")
    
    session.add(report)
    session.commit()
    session.refresh(report)
    
    return report


@router.get("/statistics", response_model=dict)
async def get_moderation_statistics(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Get review moderation statistics (admin only)."""
    
    # Count reviews by status
    pending_count = session.exec(
        select(func.count(Review.id)).where(Review.status == ReviewStatus.PENDING)
    ).first() or 0
    
    approved_count = session.exec(
        select(func.count(Review.id)).where(Review.status == ReviewStatus.APPROVED)
    ).first() or 0
    
    rejected_count = session.exec(
        select(func.count(Review.id)).where(Review.status == ReviewStatus.REJECTED)
    ).first() or 0
    
    flagged_count = session.exec(
        select(func.count(Review.id)).where(Review.status == ReviewStatus.FLAGGED)
    ).first() or 0
    
    # Count reports by status
    pending_reports = session.exec(
        select(func.count(ReviewReport.id)).where(ReviewReport.status == "pending")
    ).first() or 0
    
    resolved_reports = session.exec(
        select(func.count(ReviewReport.id)).where(ReviewReport.status == "resolved")
    ).first() or 0
    
    return {
        "reviews": {
            "pending": pending_count,
            "approved": approved_count,
            "rejected": rejected_count,
            "flagged": flagged_count,
            "total": pending_count + approved_count + rejected_count + flagged_count
        },
        "reports": {
            "pending": pending_reports,
            "resolved": resolved_reports,
            "total": pending_reports + resolved_reports
        }
    }


@router.get("/summaries", response_model=List[ReviewSummary])
async def get_review_summaries(
    target_type: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Get review summaries (admin only)."""
    
    query = select(ReviewSummary)
    
    if target_type:
        query = query.where(ReviewSummary.target_type == target_type)
    
    summaries = session.exec(
        query.offset(offset).limit(limit).order_by(ReviewSummary.last_updated.desc())
    ).all()
    
    return summaries


@router.post("/summaries/refresh", response_model=dict)
async def refresh_review_summaries(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """Refresh all review summaries (admin only)."""
    
    from app.api.v1.endpoints.reviews import update_review_summary
    from app.models.review import ReviewType
    from app.models.vendor import Vendor
    from app.models.product import Product
    
    # Refresh vendor summaries
    vendors = session.exec(select(Vendor)).all()
    for vendor in vendors:
        await update_review_summary(session, ReviewType.VENDOR, vendor.id, None)
    
    # Refresh product summaries
    products = session.exec(select(Product)).all()
    for product in products:
        await update_review_summary(session, ReviewType.PRODUCT, None, product.id)
    
    return {"message": "Review summaries refreshed successfully"}
