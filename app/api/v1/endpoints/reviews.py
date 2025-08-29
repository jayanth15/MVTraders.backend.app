"""
Review management endpoints for vendors and products.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, and_, or_, func
from app.database import get_session
from app.models.review import Review, ReviewVote, ReviewReport, ReviewSummary, ReviewType, ReviewStatus
from app.models.user import User
from app.models.vendor import Vendor
from app.models.product import Product
from app.models.order import Order
from app.core.deps import get_current_user
from datetime import datetime
import json

router = APIRouter()


@router.post("/", response_model=Review, status_code=status.HTTP_201_CREATED)
async def create_review(
    review_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new review for a vendor or product."""
    
    review_type = review_data.get("review_type")
    if not review_type or review_type not in [ReviewType.VENDOR, ReviewType.PRODUCT]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Review type must be 'vendor' or 'product'"
        )
    
    # Validate targets
    vendor_id = review_data.get("vendor_id")
    product_id = review_data.get("product_id")
    
    if review_type == ReviewType.VENDOR:
        if not vendor_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vendor ID is required for vendor reviews"
            )
        vendor = session.get(Vendor, vendor_id)
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found"
            )
    
    elif review_type == ReviewType.PRODUCT:
        if not product_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product ID is required for product reviews"
            )
        product = session.get(Product, product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
    
    # Check if user already reviewed this target
    existing_review = session.exec(
        select(Review).where(
            Review.reviewer_id == current_user.id,
            Review.review_type == review_type,
            Review.vendor_id == vendor_id if vendor_id else True,
            Review.product_id == product_id if product_id else True
        )
    ).first()
    
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this item"
        )
    
    # Validate order if provided (for verified purchase)
    order_id = review_data.get("order_id")
    is_verified_purchase = False
    
    if order_id:
        order = session.get(Order, order_id)
        if not order or order.customer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid order or order does not belong to you"
            )
        
        # Check if order contains the product/vendor being reviewed
        if review_type == ReviewType.VENDOR and order.vendor_id == vendor_id:
            is_verified_purchase = True
        elif review_type == ReviewType.PRODUCT:
            # Check if order contains this product
            from app.models.order import OrderItem
            order_item = session.exec(
                select(OrderItem).where(
                    OrderItem.order_id == order_id,
                    OrderItem.product_id == product_id
                )
            ).first()
            if order_item:
                is_verified_purchase = True
    
    # Create review
    review = Review(
        review_type=review_type,
        reviewer_id=current_user.id,
        vendor_id=vendor_id,
        product_id=product_id,
        order_id=order_id,
        rating=review_data["rating"],
        title=review_data["title"],
        content=review_data["content"],
        is_verified_purchase=is_verified_purchase,
        status=ReviewStatus.PENDING,
        review_metadata=review_data.get("review_metadata", {})
    )
    
    session.add(review)
    session.commit()
    session.refresh(review)
    
    # Update review summary
    await update_review_summary(session, review_type, vendor_id, product_id)
    
    return review


@router.get("/", response_model=List[Review])
async def get_reviews(
    review_type: Optional[ReviewType] = None,
    vendor_id: Optional[int] = None,
    product_id: Optional[int] = None,
    status: Optional[ReviewStatus] = None,
    verified_only: bool = False,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session)
):
    """Get reviews with filtering options."""
    
    query = select(Review)
    
    if review_type:
        query = query.where(Review.review_type == review_type)
    
    if vendor_id:
        query = query.where(Review.vendor_id == vendor_id)
    
    if product_id:
        query = query.where(Review.product_id == product_id)
    
    if status:
        query = query.where(Review.status == status)
    else:
        # Default to approved reviews for public viewing
        query = query.where(Review.status == ReviewStatus.APPROVED)
    
    if verified_only:
        query = query.where(Review.is_verified_purchase == True)
    
    query = query.offset(offset).limit(limit).order_by(Review.created_at.desc())
    reviews = session.exec(query).all()
    
    return reviews


@router.get("/{review_id}", response_model=Review)
async def get_review(
    review_id: int,
    session: Session = Depends(get_session)
):
    """Get a specific review by ID."""
    
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    return review


@router.put("/{review_id}", response_model=Review)
async def update_review(
    review_id: int,
    review_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update a review (reviewer only)."""
    
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    if review.reviewer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update your own reviews"
        )
    
    # Update allowed fields
    allowed_fields = ["rating", "title", "content", "review_metadata"]
    for field in allowed_fields:
        if field in review_data:
            setattr(review, field, review_data[field])
    
    review.updated_at = datetime.utcnow()
    review.status = ReviewStatus.PENDING  # Reset to pending for re-moderation
    
    session.add(review)
    session.commit()
    session.refresh(review)
    
    # Update review summary
    await update_review_summary(session, review.review_type, review.vendor_id, review.product_id)
    
    return review


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Delete a review."""
    
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    # Check if user can delete this review (reviewer or admin)
    if review.reviewer_id != current_user.id and current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only delete your own reviews"
        )
    
    session.delete(review)
    session.commit()
    
    # Update review summary
    await update_review_summary(session, review.review_type, review.vendor_id, review.product_id)


@router.post("/{review_id}/vote", response_model=ReviewVote, status_code=status.HTTP_201_CREATED)
async def vote_on_review(
    review_id: int,
    vote_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Vote on review helpfulness."""
    
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    # Check if user already voted on this review
    existing_vote = session.exec(
        select(ReviewVote).where(
            ReviewVote.review_id == review_id,
            ReviewVote.user_id == current_user.id
        )
    ).first()
    
    if existing_vote:
        # Update existing vote
        existing_vote.is_helpful = vote_data["is_helpful"]
        existing_vote.updated_at = datetime.utcnow()
        session.add(existing_vote)
        session.commit()
        session.refresh(existing_vote)
        vote = existing_vote
    else:
        # Create new vote
        vote = ReviewVote(
            review_id=review_id,
            user_id=current_user.id,
            is_helpful=vote_data["is_helpful"]
        )
        session.add(vote)
        session.commit()
        session.refresh(vote)
    
    # Update helpful count on review
    helpful_count = session.exec(
        select(func.count(ReviewVote.id)).where(
            ReviewVote.review_id == review_id,
            ReviewVote.is_helpful == True
        )
    ).first() or 0
    
    review.helpful_count = helpful_count
    session.add(review)
    session.commit()
    
    return vote


@router.post("/{review_id}/report", response_model=ReviewReport, status_code=status.HTTP_201_CREATED)
async def report_review(
    review_id: int,
    report_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Report a review for inappropriate content."""
    
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    # Check if user already reported this review
    existing_report = session.exec(
        select(ReviewReport).where(
            ReviewReport.review_id == review_id,
            ReviewReport.reporter_id == current_user.id
        )
    ).first()
    
    if existing_report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reported this review"
        )
    
    # Create report
    report = ReviewReport(
        review_id=review_id,
        reporter_id=current_user.id,
        reason=report_data["reason"],
        description=report_data.get("description")
    )
    
    session.add(report)
    session.commit()
    session.refresh(report)
    
    # Update reported count on review
    reported_count = session.exec(
        select(func.count(ReviewReport.id)).where(ReviewReport.review_id == review_id)
    ).first() or 0
    
    review.reported_count = reported_count
    session.add(review)
    session.commit()
    
    return report


async def update_review_summary(session: Session, review_type: ReviewType, vendor_id: Optional[int], product_id: Optional[int]):
    """Update review summary statistics."""
    
    # Get existing summary or create new one
    summary = session.exec(
        select(ReviewSummary).where(
            ReviewSummary.target_type == review_type,
            ReviewSummary.vendor_id == vendor_id if vendor_id else True,
            ReviewSummary.product_id == product_id if product_id else True
        )
    ).first()
    
    if not summary:
        summary = ReviewSummary(
            target_type=review_type,
            vendor_id=vendor_id,
            product_id=product_id
        )
    
    # Calculate statistics
    reviews_query = select(Review).where(
        Review.review_type == review_type,
        Review.status == ReviewStatus.APPROVED
    )
    
    if vendor_id:
        reviews_query = reviews_query.where(Review.vendor_id == vendor_id)
    if product_id:
        reviews_query = reviews_query.where(Review.product_id == product_id)
    
    reviews = session.exec(reviews_query).all()
    
    if reviews:
        summary.total_reviews = len(reviews)
        summary.average_rating = sum(r.rating for r in reviews) / len(reviews)
        
        # Rating distribution
        distribution = {str(i): 0 for i in range(1, 6)}
        for review in reviews:
            star_rating = str(int(review.rating))
            distribution[star_rating] += 1
        summary.rating_distribution = distribution
        
        # Verified purchase statistics
        verified_reviews = [r for r in reviews if r.is_verified_purchase]
        summary.verified_reviews = len(verified_reviews)
        if verified_reviews:
            summary.verified_average_rating = sum(r.rating for r in verified_reviews) / len(verified_reviews)
        
        # Engagement statistics
        summary.total_helpful_votes = sum(r.helpful_count for r in reviews)
        summary.total_reports = sum(r.reported_count for r in reviews)
    
    summary.last_updated = datetime.utcnow()
    session.add(summary)
    session.commit()
