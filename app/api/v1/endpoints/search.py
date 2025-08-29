"""
Phase 9: Advanced Search & Discovery API Endpoints
Comprehensive search, faceted filtering, and AI-powered recommendations.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime, timedelta
import json

from app.core.deps import get_current_user, get_session
from app.models.user import User
from app.models.search import (
    SavedSearch, SearchLog, SearchSuggestion, UserRecommendation, SearchFilter,
    SearchAnalytics, SearchTrend, UserSearchProfile, SmartFilter, SearchQuery,
    SearchResult, SearchInteraction, SearchSession, SearchType, SearchIntent, FilterType
)
from app.services.search_service import SearchService, RecommendationService, SearchRequest

router = APIRouter()


@router.get("/search", response_model=Dict[str, Any])
async def advanced_search(
    q: str = Query(..., description="Search query"),
    type: SearchType = Query(default=SearchType.PRODUCT, description="Search type"),
    category: Optional[str] = Query(default=None, description="Product category filter"),
    vendor_id: Optional[str] = Query(default=None, description="Vendor ID filter"),
    price_min: Optional[float] = Query(default=None, description="Minimum price filter"),
    price_max: Optional[float] = Query(default=None, description="Maximum price filter"),
    sort_by: str = Query(default="relevance", description="Sort order"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Results per page"),
    session_id: Optional[str] = Query(default=None, description="Search session ID"),
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Advanced search with AI-powered results and faceted filtering
    """
    # Build search request
    filters = {}
    if category:
        filters['category'] = category
    if vendor_id:
        filters['vendor_id'] = vendor_id
    if price_min is not None:
        filters['price_min'] = price_min
    if price_max is not None:
        filters['price_max'] = price_max
    
    search_request = SearchRequest(
        query=q,
        search_type=type,
        filters=filters,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
        user_id=current_user.id if current_user else None,
        session_id=session_id
    )
    
    # Execute search
    search_service = SearchService(session)
    try:
        response = await search_service.search(search_request)
        
        return {
            "query": q,
            "search_type": type,
            "results": response.results,
            "pagination": {
                "page": response.page,
                "page_size": response.page_size,
                "total_results": response.total_results,
                "total_pages": (response.total_results + response.page_size - 1) // response.page_size
            },
            "facets": response.facets,
            "suggestions": response.suggestions,
            "metadata": {
                "query_id": response.query_id,
                "execution_time_ms": response.execution_time_ms,
                "search_intent": response.search_intent,
                "filters_applied": filters
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/search/autocomplete", response_model=Dict[str, Any])
async def search_autocomplete(
    q: str = Query(..., description="Partial search query"),
    type: SearchType = Query(default=SearchType.PRODUCT, description="Search type"),
    limit: int = Query(default=10, ge=1, le=20, description="Number of suggestions"),
    session: Session = Depends(get_session)
):
    """
    Search autocomplete suggestions
    """
    if len(q) < 2:
        return {"suggestions": [], "query": q}
    
    suggestions = []
    
    if type == SearchType.PRODUCT:
        from app.models.product import Product, ProductStatus
        
        # Product name suggestions
        product_suggestions = session.query(Product.name).filter(
            Product.name.ilike(f'%{q}%'),
            Product.status == ProductStatus.APPROVED
        ).distinct().limit(limit).all()
        
        suggestions.extend([p.name for p in product_suggestions])
        
        # Category suggestions
        category_suggestions = session.query(Product.category).filter(
            Product.category.ilike(f'%{q}%'),
            Product.status == ProductStatus.APPROVED
        ).distinct().limit(5).all()
        
        suggestions.extend([c.category for c in category_suggestions])
    
    elif type == SearchType.VENDOR:
        from app.models.vendor import Vendor
        
        vendor_suggestions = session.query(Vendor.business_name).filter(
            Vendor.business_name.ilike(f'%{q}%')
        ).distinct().limit(limit).all()
        
        suggestions.extend([v.business_name for v in vendor_suggestions])
    
    # Remove duplicates and limit results
    unique_suggestions = list(set(suggestions))[:limit]
    
    return {
        "suggestions": unique_suggestions,
        "query": q,
        "type": type
    }


@router.get("/search/trending", response_model=Dict[str, Any])
async def get_trending_searches(
    period_days: int = Query(default=7, ge=1, le=30, description="Trending period in days"),
    limit: int = Query(default=10, ge=1, le=50, description="Number of trending items"),
    type: SearchType = Query(default=SearchType.PRODUCT, description="Search type"),
    session: Session = Depends(get_session)
):
    """
    Get trending search queries and topics
    """
    start_date = datetime.utcnow() - timedelta(days=period_days)
    
    # Get trending search queries
    trending_queries = session.query(
        SearchQuery.normalized_query,
        func.count(SearchQuery.id).label('search_count'),
        func.avg(SearchQuery.total_results).label('avg_results')
    ).filter(
        SearchQuery.created_at >= start_date,
        SearchQuery.search_type == type,
        SearchQuery.normalized_query.isnot(None)
    ).group_by(
        SearchQuery.normalized_query
    ).having(
        func.count(SearchQuery.id) >= 2
    ).order_by(
        desc('search_count')
    ).limit(limit).all()
    
    trending_items = []
    for query in trending_queries:
        trending_items.append({
            "query": query.normalized_query,
            "search_count": query.search_count,
            "avg_results": int(query.avg_results) if query.avg_results else 0,
            "trend_score": query.search_count * 10  # Simple trending score
        })
    
    return {
        "trending_searches": trending_items,
        "period_days": period_days,
        "search_type": type,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/search/facets", response_model=Dict[str, Any])
async def get_search_facets(
    type: SearchType = Query(default=SearchType.PRODUCT, description="Search type"),
    session: Session = Depends(get_session)
):
    """
    Get available search facets for filtering
    """
    facets = {}
    
    if type == SearchType.PRODUCT:
        from app.models.product import Product, ProductStatus
        
        # Category facet
        categories = session.query(
            Product.category,
            func.count(Product.id).label('count')
        ).filter(
            Product.status == ProductStatus.APPROVED,
            Product.category.isnot(None)
        ).group_by(Product.category).order_by(desc('count')).all()
        
        facets['categories'] = [
            {
                "value": cat.category,
                "display_name": cat.category,
                "count": cat.count
            } for cat in categories
        ]
        
        # Price range facet
        price_stats = session.query(
            func.min(Product.price).label('min_price'),
            func.max(Product.price).label('max_price'),
            func.avg(Product.price).label('avg_price')
        ).filter(Product.status == ProductStatus.APPROVED).first()
        
        facets['price_ranges'] = [
            {"min": 0, "max": 50, "display": "Under $50"},
            {"min": 50, "max": 100, "display": "$50 - $100"},
            {"min": 100, "max": 200, "display": "$100 - $200"},
            {"min": 200, "max": None, "display": "Over $200"}
        ]
        
        facets['price_stats'] = {
            "min_price": float(price_stats.min_price) if price_stats.min_price else 0,
            "max_price": float(price_stats.max_price) if price_stats.max_price else 0,
            "avg_price": float(price_stats.avg_price) if price_stats.avg_price else 0
        }
        
        # Vendor facet (top vendors by product count)
        from app.models.vendor import Vendor
        
        vendors = session.query(
            Vendor.id,
            Vendor.business_name,
            func.count(Product.id).label('product_count')
        ).join(Product).filter(
            Product.status == ProductStatus.APPROVED
        ).group_by(
            Vendor.id, Vendor.business_name
        ).order_by(desc('product_count')).limit(20).all()
        
        facets['vendors'] = [
            {
                "value": vendor.id,
                "display_name": vendor.business_name,
                "count": vendor.product_count
            } for vendor in vendors
        ]
    
    return {
        "facets": facets,
        "search_type": type,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.post("/search/interaction", response_model=Dict[str, Any])
async def track_search_interaction(
    query_id: int,
    result_id: Optional[int] = None,
    interaction_type: str = "click",
    interaction_data: Optional[Dict[str, Any]] = None,
    page_url: Optional[str] = None,
    duration_seconds: Optional[int] = None,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Track user interactions with search results
    """
    # Verify query exists
    search_query = session.query(SearchQuery).filter(SearchQuery.id == query_id).first()
    if not search_query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search query not found"
        )
    
    # Verify result exists if provided
    search_result = None
    if result_id:
        search_result = session.query(SearchResult).filter(
            SearchResult.id == result_id,
            SearchResult.query_id == query_id
        ).first()
        if not search_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Search result not found"
            )
    
    # Create interaction record
    interaction = SearchInteraction(
        query_id=query_id,
        result_id=result_id,
        user_id=current_user.id if current_user else None,
        interaction_type=interaction_type,
        interaction_data=interaction_data or {},
        page_url=page_url,
        duration_seconds=duration_seconds
    )
    
    session.add(interaction)
    
    # Update search result if applicable
    if search_result:
        if interaction_type == "click":
            search_result.clicked = True
            search_result.click_timestamp = datetime.utcnow()
        elif interaction_type == "view":
            search_result.viewed = True
            if duration_seconds:
                search_result.view_duration_seconds = duration_seconds
    
    # Update search query statistics
    if interaction_type == "click":
        search_query.results_clicked += 1
    
    session.commit()
    
    return {
        "message": "Interaction tracked successfully",
        "interaction_id": interaction.id,
        "query_id": query_id,
        "result_id": result_id
    }


@router.get("/search/analytics", response_model=Dict[str, Any])
async def get_search_analytics(
    period_days: int = Query(default=7, ge=1, le=90, description="Analytics period"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get search analytics and insights
    """
    start_date = datetime.utcnow() - timedelta(days=period_days)
    
    # Basic search statistics
    total_searches = session.query(SearchQuery).filter(
        SearchQuery.created_at >= start_date
    ).count()
    
    unique_users = session.query(SearchQuery.user_id).filter(
        SearchQuery.created_at >= start_date,
        SearchQuery.user_id.isnot(None)
    ).distinct().count()
    
    avg_results = session.query(func.avg(SearchQuery.total_results)).filter(
        SearchQuery.created_at >= start_date
    ).scalar()
    
    # Search performance metrics
    avg_execution_time = session.query(func.avg(SearchQuery.execution_time_ms)).filter(
        SearchQuery.created_at >= start_date,
        SearchQuery.execution_time_ms.isnot(None)
    ).scalar()
    
    # Click-through rates
    searches_with_clicks = session.query(SearchQuery).filter(
        SearchQuery.created_at >= start_date,
        SearchQuery.results_clicked > 0
    ).count()
    
    ctr = (searches_with_clicks / total_searches * 100) if total_searches > 0 else 0
    
    # Zero-result searches
    zero_result_searches = session.query(SearchQuery).filter(
        SearchQuery.created_at >= start_date,
        SearchQuery.total_results == 0
    ).count()
    
    zero_result_rate = (zero_result_searches / total_searches * 100) if total_searches > 0 else 0
    
    # Top search queries
    top_queries = session.query(
        SearchQuery.normalized_query,
        func.count(SearchQuery.id).label('count')
    ).filter(
        SearchQuery.created_at >= start_date,
        SearchQuery.normalized_query.isnot(None)
    ).group_by(
        SearchQuery.normalized_query
    ).order_by(desc('count')).limit(10).all()
    
    return {
        "period_days": period_days,
        "summary": {
            "total_searches": total_searches,
            "unique_users": unique_users,
            "avg_results_per_search": round(avg_results, 1) if avg_results else 0,
            "avg_execution_time_ms": round(avg_execution_time, 1) if avg_execution_time else 0,
            "click_through_rate": round(ctr, 2),
            "zero_result_rate": round(zero_result_rate, 2)
        },
        "top_queries": [
            {
                "query": query.normalized_query,
                "search_count": query.count
            } for query in top_queries
        ],
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/search/sessions/{session_id}", response_model=Dict[str, Any])
async def get_search_session(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get detailed search session information
    """
    search_session = session.query(SearchSession).filter(
        SearchSession.session_id == session_id
    ).first()
    
    if not search_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search session not found"
        )
    
    # Get session queries
    queries = session.query(SearchQuery).filter(
        SearchQuery.session_id == session_id
    ).order_by(SearchQuery.created_at).all()
    
    # Format session data
    session_data = {
        "session_id": search_session.session_id,
        "user_id": search_session.user_id,
        "session_start": search_session.session_start.isoformat(),
        "session_end": search_session.session_end.isoformat() if search_session.session_end else None,
        "duration_seconds": search_session.get_session_duration(),
        "total_searches": search_session.total_searches,
        "total_results_viewed": search_session.total_results_viewed,
        "total_clicks": search_session.total_clicks,
        "conversion_count": search_session.conversion_count,
        "conversion_rate": search_session.get_conversion_rate(),
        "device_type": search_session.device_type,
        "queries": []
    }
    
    # Add query details
    for query in queries:
        query_data = {
            "id": query.id,
            "query_text": query.query_text,
            "search_type": query.search_type,
            "search_intent": query.search_intent,
            "total_results": query.total_results,
            "results_clicked": query.results_clicked,
            "execution_time_ms": query.execution_time_ms,
            "created_at": query.created_at.isoformat(),
            "effectiveness": query.get_search_effectiveness()
        }
        session_data["queries"].append(query_data)
    
    return session_data
