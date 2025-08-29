# Phase 9: Advanced Search & Discovery Engine Models
"""
Search and Discovery Engine Models

This module contains all models related to the advanced search functionality,
including saved searches, search filters, recommendations, and analytics.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from sqlmodel import Field, Relationship, Column, JSON
from pydantic import validator
from enum import Enum

from app.models.base import BaseModel


class SearchType(str, Enum):
    """Search types"""
    PRODUCT = "product"
    VENDOR = "vendor"
    SERVICE = "service"
    ALL = "all"


class SearchIntent(str, Enum):
    """Search intent classification"""
    BROWSE = "browse"
    PURCHASE = "purchase"
    COMPARE = "compare"
    RESEARCH = "research"


class FilterType(str, Enum):
    """Filter types"""
    RANGE = "range"
    SELECT = "select"
    BOOLEAN = "boolean"
    TEXT = "text"


class SavedSearch(BaseModel, table=True):
    """Model for user's saved search queries and filters."""
    __tablename__ = "saved_searches"

    name: str = Field(max_length=255)
    user_id: int = Field(foreign_key="users.id", index=True)
    search_query: Optional[str] = Field(default=None, max_length=500)
    filters: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))  # JSON field for flexible filters
    is_alert: bool = Field(default=False)  # Whether to send notifications
    alert_frequency: Optional[str] = Field(default=None, max_length=50)  # daily, weekly, instant
    last_executed: Optional[datetime] = Field(default=None)
    results_count: int = Field(default=0)

    # Relationships
    user: Optional["User"] = Relationship()
    search_logs: List["SearchLog"] = Relationship(back_populates="saved_search")


class SearchFilter(BaseModel, table=True):
    """Model for predefined search filters and categories."""
    __tablename__ = "search_filters"

    name: str = Field(max_length=255, unique=True)
    category: str = Field(max_length=100, index=True)
    filter_type: str = Field(max_length=50)  # range, select, boolean, text
    options: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))  # JSON for filter options
    is_active: bool = Field(default=True)
    sort_order: int = Field(default=0)
    description: Optional[str] = Field(default=None, max_length=500)


class SearchSuggestion(BaseModel, table=True):
    """Model for search autocomplete suggestions."""
    __tablename__ = "search_suggestions"

    term: str = Field(max_length=255, unique=True, index=True)
    category: str = Field(max_length=100, index=True)
    search_count: int = Field(default=1)
    last_searched: datetime = Field(default_factory=datetime.utcnow)
    is_trending: bool = Field(default=False)
    relevance_score: float = Field(default=1.0)


class SearchLog(BaseModel, table=True):
    """Model for tracking all search activities and analytics."""
    __tablename__ = "search_logs"

    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    search_query: str = Field(max_length=500, index=True)
    filters_applied: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))  # JSON field
    results_count: int = Field(default=0)
    response_time_ms: Optional[int] = Field(default=None)
    clicked_result_id: Optional[int] = Field(default=None)
    clicked_result_type: Optional[str] = Field(default=None, max_length=50)
    session_id: Optional[str] = Field(default=None, max_length=255)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    saved_search_id: Optional[int] = Field(default=None, foreign_key="saved_searches.id")

    # Relationships
    user: Optional["User"] = Relationship()
    saved_search: Optional[SavedSearch] = Relationship(back_populates="search_logs")


class SearchQuery(BaseModel, table=True):
    """Model for individual search queries (for compatibility with existing endpoints)."""
    __tablename__ = "search_queries"

    query_text: str = Field(max_length=500, index=True)
    normalized_query: Optional[str] = Field(default=None, max_length=500, index=True)
    search_type: SearchType = Field(default=SearchType.PRODUCT, index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    session_id: Optional[str] = Field(default=None, max_length=255)
    total_results: int = Field(default=0)
    response_time_ms: Optional[int] = Field(default=None)
    filters_applied: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # Relationships  
    user: Optional["User"] = Relationship()


class SearchResult(BaseModel, table=True):
    """Model for search result items."""
    __tablename__ = "search_results"

    query_id: int = Field(foreign_key="search_queries.id", index=True)
    result_type: str = Field(max_length=50, index=True)  # product, vendor, etc.
    result_id: int = Field(index=True)  # ID of the actual item
    title: str = Field(max_length=500)
    description: Optional[str] = Field(default=None, max_length=1000)
    relevance_score: float = Field(default=0.0)
    position: int = Field(default=0)  # Position in search results
    result_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # Relationships
    query: Optional[SearchQuery] = Relationship()


class SearchInteraction(BaseModel, table=True):
    """Model for tracking user interactions with search results."""
    __tablename__ = "search_interactions"

    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    query_id: int = Field(foreign_key="search_queries.id", index=True)
    result_id: Optional[int] = Field(default=None, foreign_key="search_results.id", index=True)
    interaction_type: str = Field(max_length=50)  # click, view, bookmark, etc.
    session_id: Optional[str] = Field(default=None, max_length=255)
    interaction_data: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # Relationships
    user: Optional["User"] = Relationship()
    query: Optional[SearchQuery] = Relationship()
    result: Optional[SearchResult] = Relationship()


class SearchSession(BaseModel, table=True):
    """Model for tracking search sessions."""
    __tablename__ = "search_sessions"

    session_id: str = Field(max_length=255, unique=True, index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = Field(default=None)
    total_queries: int = Field(default=0)
    total_results_clicked: int = Field(default=0)
    session_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # Relationships
    user: Optional["User"] = Relationship()


class RecommendationEvent(BaseModel, table=True):
    """Model for tracking recommendation events and interactions."""
    __tablename__ = "recommendation_events"

    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    recommendation_id: int = Field(foreign_key="user_recommendations.id", index=True)
    event_type: str = Field(max_length=50, index=True)  # view, click, purchase, dismiss
    event_data: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    session_id: Optional[str] = Field(default=None, max_length=255)

    # Relationships
    user: Optional["User"] = Relationship()
    recommendation: Optional["UserRecommendation"] = Relationship()


class UserRecommendation(BaseModel, table=True):
    """Model for personalized user recommendations."""
    __tablename__ = "user_recommendations"

    user_id: int = Field(foreign_key="users.id", index=True)
    item_type: str = Field(max_length=50, index=True)  # product, service, supplier, etc.
    item_id: int = Field(index=True)
    recommendation_type: str = Field(max_length=50)  # viewed, purchased, similar, trending
    score: float = Field(default=0.0)
    reason: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    expires_at: Optional[datetime] = Field(default=None)
    clicked: bool = Field(default=False)
    clicked_at: Optional[datetime] = Field(default=None)

    # Relationships
    user: Optional["User"] = Relationship()


class SearchAnalytics(BaseModel, table=True):
    """Model for aggregated search analytics and metrics."""
    __tablename__ = "search_analytics"

    date: datetime = Field(index=True)
    metric_type: str = Field(max_length=50, index=True)  # daily_searches, popular_terms, etc.
    metric_name: str = Field(max_length=255, index=True)
    metric_value: float = Field(default=0.0)
    additional_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))  # JSON field for extra metrics

    class Config:
        indexes = [
            ("date", "metric_type"),
            ("metric_type", "metric_name"),
        ]


class RecommendationModel(BaseModel, table=True):
    """Model for storing ML recommendation model metadata."""
    __tablename__ = "recommendation_models"

    name: str = Field(max_length=255, unique=True)
    type: str = Field(max_length=100)  # collaborative, content-based, hybrid
    algorithm: str = Field(max_length=100)  # knn, matrix_factorization, deep_learning
    version: str = Field(max_length=50)
    parameters: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))  # JSON field for model params
    training_data_size: Optional[int] = Field(default=None)
    accuracy_score: Optional[float] = Field(default=None)
    last_trained: Optional[datetime] = Field(default=None)
    is_active: bool = Field(default=True)
    performance_metrics: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))  # JSON field


class SearchTrend(BaseModel, table=True):
    """Model for tracking search trends and popularity."""
    __tablename__ = "search_trends"

    search_term: str = Field(max_length=255, index=True)
    category: str = Field(max_length=100, index=True)
    date: datetime = Field(index=True)
    search_count: int = Field(default=1)
    unique_users: int = Field(default=1)
    trend_score: float = Field(default=0.0)  # Calculated trending score
    is_emerging: bool = Field(default=False)
    growth_rate: Optional[float] = Field(default=None)  # Percentage growth

    class Config:
        indexes = [
            ("date", "category"),
            ("search_term", "date"),
            ("trend_score",),
        ]


class UserSearchProfile(BaseModel, table=True):
    """Model for user search behavior profiles and preferences."""
    __tablename__ = "user_search_profiles"

    user_id: int = Field(foreign_key="users.id", unique=True, index=True)
    search_frequency: float = Field(default=0.0)  # Searches per day
    preferred_categories: List[str] = Field(default_factory=list, sa_column=Column(JSON))  # JSON array
    search_patterns: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))  # JSON field
    last_search_date: Optional[datetime] = Field(default=None)
    total_searches: int = Field(default=0)
    successful_searches: int = Field(default=0)  # Searches that led to clicks
    average_session_time: Optional[float] = Field(default=None)  # In minutes
    preferred_filters: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))  # JSON field

    # Relationships
    user: Optional["User"] = Relationship()

    @validator('preferred_categories', pre=True)
    def validate_categories(cls, v):
        if isinstance(v, str):
            return [v]
        return v or []


class SmartFilter(BaseModel, table=True):
    """Model for AI-powered smart filters and dynamic search refinements."""
    __tablename__ = "smart_filters"

    name: str = Field(max_length=255)
    filter_logic: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))  # JSON field for complex logic
    target_audience: str = Field(max_length=100)  # all, new_users, power_users, etc.
    effectiveness_score: float = Field(default=0.0)
    usage_count: int = Field(default=0)
    success_rate: float = Field(default=0.0)  # Percentage of searches improved
    is_auto_generated: bool = Field(default=False)
    created_by_model: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
    a_b_test_group: Optional[str] = Field(default=None, max_length=50)
