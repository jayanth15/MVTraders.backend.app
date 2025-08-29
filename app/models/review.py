"""
Review and rating models for vendors and products.
"""

from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from datetime import datetime
from enum import Enum
import uuid

from app.models.base import TimestampModel


class ReviewType(str, Enum):
    """Type of review"""
    VENDOR = "vendor"
    PRODUCT = "product"


class ReviewStatus(str, Enum):
    """Review status for moderation"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"


class Review(SQLModel, table=True):
    """
    Review model for vendors and products
    """
    __tablename__ = "reviews"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Review identification
    review_type: ReviewType = Field(description="Type of review (vendor or product)")
    
    # References
    reviewer_id: int = Field(foreign_key="users.id", description="User who wrote the review")
    vendor_id: Optional[int] = Field(default=None, foreign_key="vendors.id", description="Vendor being reviewed")
    product_id: Optional[int] = Field(default=None, foreign_key="products.id", description="Product being reviewed")
    order_id: Optional[int] = Field(default=None, foreign_key="orders.id", description="Order this review is based on")
    
    # Review content
    rating: float = Field(ge=1.0, le=5.0, description="Rating from 1.0 to 5.0")
    title: str = Field(max_length=200, description="Review title")
    content: str = Field(max_length=2000, description="Review content")
    
    # Review metadata
    status: ReviewStatus = Field(default=ReviewStatus.PENDING, description="Review moderation status")
    is_verified_purchase: bool = Field(default=False, description="Whether review is from verified purchase")
    helpful_count: int = Field(default=0, description="Number of users who found this helpful")
    reported_count: int = Field(default=0, description="Number of times this review was reported")
    
    # Moderation
    moderated_by: Optional[int] = Field(default=None, foreign_key="users.id", description="Admin who moderated this review")
    moderated_at: Optional[datetime] = Field(default=None, description="When review was moderated")
    moderation_notes: Optional[str] = Field(default=None, max_length=500, description="Moderation notes")
    
    # Additional metadata
    review_metadata: Optional[dict] = Field(default_factory=dict, sa_column=Column(JSON), description="Additional review metadata")
    
    # Relationships
    reviewer: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "Review.reviewer_id"}
    )
    vendor: Optional["Vendor"] = Relationship()
    product: Optional["Product"] = Relationship()
    order: Optional["Order"] = Relationship()
    moderator: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "Review.moderated_by"}
    )
    
    # Review interactions
    review_votes: List["ReviewVote"] = Relationship(back_populates="review")
    review_reports: List["ReviewReport"] = Relationship(back_populates="review")
    
    def __str__(self):
        target = f"vendor {self.vendor_id}" if self.vendor_id else f"product {self.product_id}"
        return f"Review by user {self.reviewer_id} for {target} - {self.rating}/5"


class ReviewVote(SQLModel, table=True):
    """
    Review helpfulness votes
    """
    __tablename__ = "review_votes"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # References
    review_id: int = Field(foreign_key="reviews.id", description="Review being voted on")
    user_id: int = Field(foreign_key="users.id", description="User casting the vote")
    
    # Vote data
    is_helpful: bool = Field(description="Whether user found review helpful")
    
    # Relationships
    review: Optional["Review"] = Relationship(back_populates="review_votes")
    user: Optional["User"] = Relationship()
    
    class Config:
        # Ensure one vote per user per review
        table_args = (
            {"sqlite_unique": ["review_id", "user_id"]},
        )


class ReviewReport(SQLModel, table=True):
    """
    Review reports for inappropriate content
    """
    __tablename__ = "review_reports"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # References
    review_id: int = Field(foreign_key="reviews.id", description="Review being reported")
    reporter_id: int = Field(foreign_key="users.id", description="User reporting the review")
    
    # Report data
    reason: str = Field(max_length=100, description="Reason for reporting")
    description: Optional[str] = Field(default=None, max_length=500, description="Additional description")
    
    # Report status
    status: str = Field(default="pending", description="Report status (pending, reviewed, resolved)")
    resolved_by: Optional[int] = Field(default=None, foreign_key="users.id", description="Admin who resolved the report")
    resolved_at: Optional[datetime] = Field(default=None, description="When report was resolved")
    resolution_notes: Optional[str] = Field(default=None, max_length=500, description="Resolution notes")
    
    # Relationships
    review: Optional["Review"] = Relationship(back_populates="review_reports")
    reporter: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "ReviewReport.reporter_id"}
    )
    resolver: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "ReviewReport.resolved_by"}
    )


class ReviewSummary(SQLModel, table=True):
    """
    Aggregated review statistics for vendors and products
    """
    __tablename__ = "review_summaries"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Target identification
    target_type: ReviewType = Field(description="Type of target (vendor or product)")
    vendor_id: Optional[int] = Field(default=None, foreign_key="vendors.id", description="Vendor ID if vendor review")
    product_id: Optional[int] = Field(default=None, foreign_key="products.id", description="Product ID if product review")
    
    # Review statistics
    total_reviews: int = Field(default=0, description="Total number of reviews")
    average_rating: float = Field(default=0.0, description="Average rating")
    rating_distribution: dict = Field(default_factory=dict, sa_column=Column(JSON), description="Distribution of ratings (1-5 stars)")
    
    # Verified purchase statistics
    verified_reviews: int = Field(default=0, description="Number of verified purchase reviews")
    verified_average_rating: float = Field(default=0.0, description="Average rating from verified purchases")
    
    # Engagement statistics
    total_helpful_votes: int = Field(default=0, description="Total helpful votes across all reviews")
    total_reports: int = Field(default=0, description="Total reports across all reviews")
    
    # Timestamps
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last time summary was updated")
    
    # Relationships
    vendor: Optional["Vendor"] = Relationship()
    product: Optional["Product"] = Relationship()
    
    class Config:
        # Ensure one summary per target
        table_args = (
            {"sqlite_unique": ["target_type", "vendor_id", "product_id"]},
        )


class ReviewTemplate(SQLModel, table=True):
    """
    Review templates for guided reviews
    """
    __tablename__ = "review_templates"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Template identification
    name: str = Field(max_length=100, description="Template name")
    description: Optional[str] = Field(default=None, max_length=500, description="Template description")
    review_type: ReviewType = Field(description="Type of review this template is for")
    
    # Template content
    questions: List[dict] = Field(default_factory=list, sa_column=Column(JSON), description="List of review questions")
    rating_criteria: List[dict] = Field(default_factory=list, sa_column=Column(JSON), description="Rating criteria")
    
    # Template settings
    is_active: bool = Field(default=True, description="Whether template is active")
    is_default: bool = Field(default=False, description="Whether this is the default template")
    
    # Usage statistics
    usage_count: int = Field(default=0, description="Number of times template was used")
    
    def __str__(self):
        return f"Review Template: {self.name} ({self.review_type})"
