"""
Phase 9: AI-Powered Recommendations API Endpoints
Intelligent product recommendations and discovery features.
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
    RecommendationModel, UserRecommendation, SearchLog,
    SearchAnalytics, SearchSession, RecommendationEvent
)
from app.services.search_service import RecommendationService

router = APIRouter()


@router.get("/recommendations", response_model=Dict[str, Any])
async def get_personalized_recommendations(
    context: str = Query(default="homepage", description="Recommendation context"),
    context_id: Optional[str] = Query(default=None, description="Context-specific ID"),
    limit: int = Query(default=10, ge=1, le=50, description="Number of recommendations"),
    session_id: Optional[str] = Query(default=None, description="Search session ID"),
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get AI-powered personalized product recommendations
    """
    recommendation_service = RecommendationService(session)
    
    try:
        recommendations = await recommendation_service.get_recommendations(
            user_id=current_user.id if current_user else None,
            context_type=context,
            context_id=context_id,
            limit=limit
        )
        
        # Track recommendation impression
        if recommendations and current_user:
            await _track_recommendation_event(
                session, recommendations, current_user.id, "impression", session_id
            )
        
        return {
            "context": context,
            "context_id": context_id,
            "user_id": current_user.id if current_user else None,
            "recommendations": recommendations,
            "count": len(recommendations),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}"
        )


@router.get("/recommendations/trending", response_model=Dict[str, Any])
async def get_trending_recommendations(
    category: Optional[str] = Query(default=None, description="Product category"),
    location: Optional[str] = Query(default=None, description="Location for local trends"),
    period_days: int = Query(default=7, ge=1, le=30, description="Trending period"),
    limit: int = Query(default=20, ge=1, le=50, description="Number of recommendations"),
    session: Session = Depends(get_session)
):
    """
    Get trending products and recommendations
    """
    from app.models.product import Product, ProductStatus
    from app.models.order import Order, OrderItem
    
    start_date = datetime.utcnow() - timedelta(days=period_days)
    
    # Base query for trending products
    trending_query = session.query(
        Product,
        func.count(OrderItem.id).label('order_count'),
        func.sum(OrderItem.quantity).label('total_quantity'),
        func.avg(OrderItem.price).label('avg_price')
    ).join(OrderItem).join(Order).filter(
        Order.created_at >= start_date,
        Product.status == ProductStatus.APPROVED
    )
    
    # Apply category filter
    if category:
        trending_query = trending_query.filter(Product.category == category)
    
    # Group and order by popularity
    trending_products = trending_query.group_by(Product.id).order_by(
        desc('order_count'), desc('total_quantity')
    ).limit(limit).all()
    
    # Format recommendations
    recommendations = []
    for product_data in trending_products:
        product = product_data.Product
        order_count = product_data.order_count
        total_quantity = product_data.total_quantity
        
        # Get vendor info
        from app.models.vendor import Vendor
        vendor = session.query(Vendor).filter(Vendor.id == product.vendor_id).first()
        
        # Calculate trending score
        trending_score = (order_count * 10) + (total_quantity * 5)
        
        recommendations.append({
            "id": product.id,
            "title": product.name,
            "description": product.description,
            "price": float(product.price),
            "currency": "USD",
            "category": product.category,
            "vendor": {
                "id": vendor.id if vendor else None,
                "name": vendor.business_name if vendor else "Unknown"
            },
            "image_url": getattr(product, 'image_url', None),
            "url": f"/products/{product.id}",
            "recommendation_type": "trending",
            "trending_score": trending_score,
            "popularity_metrics": {
                "order_count": order_count,
                "total_quantity": total_quantity,
                "avg_price": float(product_data.avg_price) if product_data.avg_price else None
            },
            "reason": f"Trending in {category}" if category else "Trending now"
        })
    
    return {
        "recommendations": recommendations,
        "filters": {
            "category": category,
            "location": location,
            "period_days": period_days
        },
        "count": len(recommendations),
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/recommendations/similar/{product_id}", response_model=Dict[str, Any])
async def get_similar_products(
    product_id: str,
    limit: int = Query(default=10, ge=1, le=30, description="Number of similar products"),
    similarity_threshold: float = Query(default=0.5, ge=0.0, le=1.0, description="Similarity threshold"),
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get products similar to the specified product
    """
    from app.models.product import Product, ProductStatus
    
    # Get the source product
    source_product = session.query(Product).filter(
        Product.id == product_id,
        Product.status == ProductStatus.APPROVED
    ).first()
    
    if not source_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    recommendation_service = RecommendationService(session)
    
    try:
        recommendations = await recommendation_service._get_similar_products(
            product_id, limit
        )
        
        # Enhanced similarity scoring
        for rec in recommendations:
            # Calculate similarity score based on multiple factors
            price_similarity = 1.0 - abs(rec['price'] - float(source_product.price)) / max(rec['price'], float(source_product.price))
            category_match = 1.0 if rec['category'] == source_product.category else 0.5
            
            # Combined similarity score
            similarity_score = (price_similarity * 0.4) + (category_match * 0.6)
            rec['similarity_score'] = round(similarity_score, 3)
            rec['similarity_factors'] = {
                'price_similarity': round(price_similarity, 3),
                'category_match': category_match,
                'same_vendor': rec['vendor']['id'] == source_product.vendor_id
            }
        
        # Filter by similarity threshold
        filtered_recommendations = [
            rec for rec in recommendations 
            if rec['similarity_score'] >= similarity_threshold
        ]
        
        return {
            "source_product": {
                "id": source_product.id,
                "title": source_product.name,
                "price": float(source_product.price),
                "category": source_product.category
            },
            "similar_products": filtered_recommendations,
            "count": len(filtered_recommendations),
            "similarity_threshold": similarity_threshold,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find similar products: {str(e)}"
        )


@router.get("/recommendations/cross-sell", response_model=Dict[str, Any])
async def get_cross_sell_recommendations(
    product_ids: List[str] = Query(..., description="Product IDs in cart/order"),
    limit: int = Query(default=10, ge=1, le=30, description="Number of recommendations"),
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get cross-sell recommendations based on cart/order contents
    """
    from app.models.product import Product, ProductStatus
    from app.models.order import Order, OrderItem
    
    if not product_ids:
        return {
            "recommendations": [],
            "count": 0,
            "message": "No products provided for cross-sell analysis"
        }
    
    # Find products frequently bought together
    # Get orders that contain any of the provided products
    related_orders = session.query(Order.id).join(OrderItem).filter(
        OrderItem.product_id.in_(product_ids)
    ).distinct().subquery()
    
    # Find other products in those orders
    cross_sell_products = session.query(
        Product,
        func.count(OrderItem.id).label('frequency'),
        func.avg(OrderItem.price).label('avg_price')
    ).join(OrderItem).join(Order).filter(
        Order.id.in_(session.query(related_orders.c.id)),
        Product.id.notin_(product_ids),  # Exclude products already in cart
        Product.status == ProductStatus.APPROVED
    ).group_by(Product.id).having(
        func.count(OrderItem.id) >= 2  # Minimum frequency threshold
    ).order_by(desc('frequency')).limit(limit).all()
    
    # Format recommendations
    recommendations = []
    for product_data in cross_sell_products:
        product = product_data.Product
        frequency = product_data.frequency
        
        # Get vendor info
        from app.models.vendor import Vendor
        vendor = session.query(Vendor).filter(Vendor.id == product.vendor_id).first()
        
        # Calculate cross-sell score
        cross_sell_score = frequency * 10  # Simple scoring
        
        recommendations.append({
            "id": product.id,
            "title": product.name,
            "description": product.description,
            "price": float(product.price),
            "currency": "USD",
            "category": product.category,
            "vendor": {
                "id": vendor.id if vendor else None,
                "name": vendor.business_name if vendor else "Unknown"
            },
            "image_url": getattr(product, 'image_url', None),
            "url": f"/products/{product.id}",
            "recommendation_type": "cross_sell",
            "cross_sell_score": cross_sell_score,
            "frequency": frequency,
            "avg_price": float(product_data.avg_price) if product_data.avg_price else None,
            "reason": "Frequently bought together"
        })
    
    return {
        "input_products": product_ids,
        "recommendations": recommendations,
        "count": len(recommendations),
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/recommendations/category/{category}", response_model=Dict[str, Any])
async def get_category_recommendations(
    category: str,
    sort_by: str = Query(default="popularity", description="Sort order: popularity, price, rating, newest"),
    limit: int = Query(default=20, ge=1, le=50, description="Number of recommendations"),
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get recommendations for a specific category
    """
    from app.models.product import Product, ProductStatus
    from app.models.order import OrderItem
    
    # Base query for category products
    base_query = session.query(Product).filter(
        Product.category == category,
        Product.status == ProductStatus.APPROVED
    )
    
    # Apply sorting
    if sort_by == "popularity":
        # Sort by order frequency
        popularity_query = session.query(
            Product,
            func.count(OrderItem.id).label('order_count')
        ).outerjoin(OrderItem).filter(
            Product.category == category,
            Product.status == ProductStatus.APPROVED
        ).group_by(Product.id).order_by(
            desc('order_count'), Product.created_at.desc()
        ).limit(limit)
        
        products_data = popularity_query.all()
        products = [p.Product for p in products_data]
        
    elif sort_by == "price":
        products = base_query.order_by(Product.price.asc()).limit(limit).all()
    elif sort_by == "newest":
        products = base_query.order_by(Product.created_at.desc()).limit(limit).all()
    else:  # Default to popularity
        products = base_query.order_by(Product.created_at.desc()).limit(limit).all()
    
    # Format recommendations
    recommendations = []
    for product in products:
        # Get vendor info
        from app.models.vendor import Vendor
        vendor = session.query(Vendor).filter(Vendor.id == product.vendor_id).first()
        
        recommendations.append({
            "id": product.id,
            "title": product.name,
            "description": product.description,
            "price": float(product.price),
            "currency": "USD",
            "category": product.category,
            "vendor": {
                "id": vendor.id if vendor else None,
                "name": vendor.business_name if vendor else "Unknown"
            },
            "image_url": getattr(product, 'image_url', None),
            "url": f"/products/{product.id}",
            "recommendation_type": "category_based",
            "reason": f"Top picks in {category}",
            "created_at": product.created_at.isoformat()
        })
    
    return {
        "category": category,
        "sort_by": sort_by,
        "recommendations": recommendations,
        "count": len(recommendations),
        "generated_at": datetime.utcnow().isoformat()
    }


@router.post("/recommendations/feedback", response_model=Dict[str, Any])
async def track_recommendation_feedback(
    recommendation_id: Optional[int] = None,
    product_id: str = None,
    event_type: str = "click",  # click, view, purchase, dismiss, like, dislike
    feedback_data: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Track user feedback on recommendations
    """
    if not recommendation_id and not product_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either recommendation_id or product_id must be provided"
        )
    
    # Create recommendation event
    event = RecommendationEvent(
        recommendation_id=recommendation_id,
        session_id=session_id,
        user_id=current_user.id if current_user else None,
        event_type=event_type,
        product_id=product_id,
        event_data=feedback_data or {}
    )
    
    session.add(event)
    
    # Update recommendation statistics if recommendation_id provided
    if recommendation_id:
        recommendation = session.query(UserRecommendation).filter(
            UserRecommendation.id == recommendation_id
        ).first()
        
        if recommendation:
            if event_type == "click":
                recommendation.clicks += 1
            elif event_type == "view":
                recommendation.impressions += 1
            elif event_type == "purchase":
                recommendation.conversions += 1
            
            recommendation.last_shown = datetime.utcnow()
    
    session.commit()
    
    return {
        "message": "Recommendation feedback tracked successfully",
        "event_id": event.id,
        "event_type": event_type,
        "tracked_at": datetime.utcnow().isoformat()
    }


@router.get("/recommendations/analytics", response_model=Dict[str, Any])
async def get_recommendation_analytics(
    period_days: int = Query(default=7, ge=1, le=90, description="Analytics period"),
    recommendation_type: Optional[str] = Query(default=None, description="Filter by recommendation type"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get recommendation system analytics and performance metrics
    """
    start_date = datetime.utcnow() - timedelta(days=period_days)
    
    # Base query for recommendations in period
    base_query = session.query(ProductRecommendation).filter(
        ProductRecommendation.created_at >= start_date
    )
    
    if recommendation_type:
        base_query = base_query.filter(
            ProductRecommendation.recommendation_type == recommendation_type
        )
    
    # Basic statistics
    total_recommendations = base_query.count()
    total_impressions = session.query(func.sum(ProductRecommendation.impressions)).filter(
        ProductRecommendation.created_at >= start_date
    ).scalar() or 0
    
    total_clicks = session.query(func.sum(ProductRecommendation.clicks)).filter(
        ProductRecommendation.created_at >= start_date
    ).scalar() or 0
    
    total_conversions = session.query(func.sum(ProductRecommendation.conversions)).filter(
        ProductRecommendation.created_at >= start_date
    ).scalar() or 0
    
    # Calculate rates
    ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0
    
    # Performance by recommendation type
    type_performance = session.query(
        ProductRecommendation.recommendation_type,
        func.count(ProductRecommendation.id).label('count'),
        func.sum(ProductRecommendation.impressions).label('impressions'),
        func.sum(ProductRecommendation.clicks).label('clicks'),
        func.sum(ProductRecommendation.conversions).label('conversions')
    ).filter(
        ProductRecommendation.created_at >= start_date
    ).group_by(ProductRecommendation.recommendation_type).all()
    
    type_stats = []
    for perf in type_performance:
        type_ctr = (perf.clicks / perf.impressions * 100) if perf.impressions > 0 else 0
        type_conv_rate = (perf.conversions / perf.clicks * 100) if perf.clicks > 0 else 0
        
        type_stats.append({
            "recommendation_type": perf.recommendation_type,
            "count": perf.count,
            "impressions": perf.impressions or 0,
            "clicks": perf.clicks or 0,
            "conversions": perf.conversions or 0,
            "ctr": round(type_ctr, 2),
            "conversion_rate": round(type_conv_rate, 2)
        })
    
    return {
        "period_days": period_days,
        "summary": {
            "total_recommendations": total_recommendations,
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "overall_ctr": round(ctr, 2),
            "overall_conversion_rate": round(conversion_rate, 2)
        },
        "performance_by_type": type_stats,
        "generated_at": datetime.utcnow().isoformat()
    }


async def _track_recommendation_event(
    session: Session, 
    recommendations: List[Dict], 
    user_id: str, 
    event_type: str,
    session_id: Optional[str] = None
):
    """Helper function to track recommendation events"""
    try:
        for rec in recommendations:
            event = RecommendationEvent(
                recommendation_id=None,  # Would link to actual recommendation record
                session_id=session_id,
                user_id=user_id,
                event_type=event_type,
                product_id=rec.get('id'),
                event_data={"recommendation_type": rec.get('recommendation_type')}
            )
            session.add(event)
        
        session.commit()
    except Exception as e:
        session.rollback()
        # Log error but don't fail the main request
        pass
