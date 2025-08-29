"""
Phase 9: Advanced Search Service
Core search functionality with Elasticsearch integration and AI recommendations.
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, text
from datetime import datetime, timedelta
import json
import uuid
import logging
from dataclasses import dataclass
import asyncio
import re

from app.models.search import (
    SearchSession, SearchQuery, SearchResult, SearchInteraction, SearchFilter,
    RecommendationModel, UserRecommendation, SearchType, SearchIntent, SearchAnalytics
)
from app.models.product import Product, ProductStatus
from app.models.vendor import Vendor
from app.models.order import Order, OrderItem

logger = logging.getLogger(__name__)


@dataclass
class SearchRequest:
    """Search request parameters"""
    query: str
    search_type: SearchType = SearchType.PRODUCT
    filters: Dict[str, Any] = None
    sort_by: str = "relevance"
    page: int = 1
    page_size: int = 20
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    location: Optional[Dict[str, Any]] = None


@dataclass
class SearchResponse:
    """Search response with results and metadata"""
    results: List[Dict[str, Any]]
    total_results: int
    page: int
    page_size: int
    execution_time_ms: int
    facets: Dict[str, List[Dict[str, Any]]]
    suggestions: List[str]
    query_id: int
    search_intent: Optional[SearchIntent] = None


class SearchService:
    """Advanced search service with AI-powered capabilities"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.elasticsearch_enabled = False  # Set to True when ES is configured
        
    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Execute advanced search with AI enhancements
        """
        start_time = datetime.utcnow()
        
        # Get or create search session
        session = await self._get_or_create_session(request.session_id, request.user_id)
        
        # Analyze search intent
        search_intent = await self._analyze_search_intent(request.query)
        
        # Create search query record
        search_query = SearchQuery(
            session_id=session.session_id,
            user_id=request.user_id,
            query_text=request.query,
            normalized_query=self._normalize_query(request.query),
            search_type=request.search_type,
            search_intent=search_intent,
            filters_applied=request.filters or {},
            sort_order=request.sort_by,
            page_number=request.page,
            results_per_page=request.page_size
        )
        
        self.db.add(search_query)
        self.db.commit()
        self.db.refresh(search_query)
        
        try:
            # Execute search
            if self.elasticsearch_enabled:
                results, total_count = await self._elasticsearch_search(request, search_query)
            else:
                results, total_count = await self._database_search(request, search_query)
            
            # Store search results
            await self._store_search_results(search_query.id, results)
            
            # Get facets for filtering
            facets = await self._get_search_facets(request, total_count)
            
            # Generate search suggestions
            suggestions = await self._get_search_suggestions(request.query)
            
            # Calculate execution time
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Update search query with results
            search_query.total_results = total_count
            search_query.execution_time_ms = execution_time
            self.db.commit()
            
            # Update session statistics
            await self._update_session_stats(session.session_id)
            
            return SearchResponse(
                results=results,
                total_results=total_count,
                page=request.page,
                page_size=request.page_size,
                execution_time_ms=execution_time,
                facets=facets,
                suggestions=suggestions,
                query_id=search_query.id,
                search_intent=search_intent
            )
            
        except Exception as e:
            logger.error(f"Search execution failed: {str(e)}")
            search_query.abandoned = True
            self.db.commit()
            raise
    
    async def _get_or_create_session(self, session_id: Optional[str], user_id: Optional[str]) -> SearchSession:
        """Get existing or create new search session"""
        if session_id:
            session = self.db.query(SearchSession).filter(
                SearchSession.session_id == session_id
            ).first()
            if session:
                return session
        
        # Create new session
        new_session_id = session_id or str(uuid.uuid4())
        session = SearchSession(
            session_id=new_session_id,
            user_id=user_id,
            session_start=datetime.utcnow()
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    async def _analyze_search_intent(self, query: str) -> SearchIntent:
        """Analyze search query to determine user intent"""
        query_lower = query.lower().strip()
        
        # Intent patterns
        if any(word in query_lower for word in ['buy', 'purchase', 'order', 'get']):
            return SearchIntent.BUY
        elif any(word in query_lower for word in ['compare', 'vs', 'versus', 'difference']):
            return SearchIntent.COMPARE
        elif any(word in query_lower for word in ['review', 'rating', 'quality', 'good', 'best']):
            return SearchIntent.RESEARCH
        elif any(word in query_lower for word in ['find', 'where', 'location', 'near']):
            return SearchIntent.NAVIGATE
        elif len(query_lower.split()) == 1:
            return SearchIntent.DISCOVER
        else:
            return SearchIntent.BROWSE
    
    def _normalize_query(self, query: str) -> str:
        """Normalize search query for better matching"""
        # Remove special characters, extra spaces, convert to lowercase
        normalized = re.sub(r'[^\w\s]', ' ', query.lower())
        normalized = ' '.join(normalized.split())
        return normalized
    
    async def _elasticsearch_search(self, request: SearchRequest, query: SearchQuery) -> Tuple[List[Dict], int]:
        """Execute search using Elasticsearch (placeholder for ES integration)"""
        # This would integrate with Elasticsearch when available
        # For now, fall back to database search
        return await self._database_search(request, query)
    
    async def _database_search(self, request: SearchRequest, query: SearchQuery) -> Tuple[List[Dict], int]:
        """Execute search using database queries"""
        if request.search_type == SearchType.PRODUCT:
            return await self._search_products(request)
        elif request.search_type == SearchType.VENDOR:
            return await self._search_vendors(request)
        else:
            return [], 0
    
    async def _search_products(self, request: SearchRequest) -> Tuple[List[Dict], int]:
        """Search for products"""
        base_query = self.db.query(Product).filter(
            Product.status == ProductStatus.APPROVED
        )
        
        # Text search
        if request.query:
            search_terms = request.query.split()
            for term in search_terms:
                base_query = base_query.filter(
                    or_(
                        Product.name.ilike(f'%{term}%'),
                        Product.description.ilike(f'%{term}%'),
                        Product.category.ilike(f'%{term}%')
                    )
                )
        
        # Apply filters
        if request.filters:
            if 'category' in request.filters:
                base_query = base_query.filter(Product.category == request.filters['category'])
            
            if 'vendor_id' in request.filters:
                base_query = base_query.filter(Product.vendor_id == request.filters['vendor_id'])
            
            if 'price_min' in request.filters:
                base_query = base_query.filter(Product.price >= request.filters['price_min'])
            
            if 'price_max' in request.filters:
                base_query = base_query.filter(Product.price <= request.filters['price_max'])
        
        # Get total count
        total_count = base_query.count()
        
        # Apply sorting
        if request.sort_by == 'price_asc':
            base_query = base_query.order_by(Product.price.asc())
        elif request.sort_by == 'price_desc':
            base_query = base_query.order_by(Product.price.desc())
        elif request.sort_by == 'name':
            base_query = base_query.order_by(Product.name.asc())
        else:  # relevance (default)
            base_query = base_query.order_by(Product.created_at.desc())
        
        # Apply pagination
        offset = (request.page - 1) * request.page_size
        products = base_query.offset(offset).limit(request.page_size).all()
        
        # Format results
        results = []
        for i, product in enumerate(products):
            # Get vendor info
            vendor = self.db.query(Vendor).filter(Vendor.id == product.vendor_id).first()
            
            results.append({
                'id': product.id,
                'title': product.name,
                'description': product.description,
                'price': float(product.price),
                'currency': 'USD',
                'category': product.category,
                'vendor': {
                    'id': vendor.id if vendor else None,
                    'name': vendor.business_name if vendor else 'Unknown'
                },
                'image_url': getattr(product, 'image_url', None),
                'url': f'/products/{product.id}',
                'position': offset + i + 1,
                'relevance_score': 1.0,  # Would be calculated by search engine
                'created_at': product.created_at.isoformat()
            })
        
        return results, total_count
    
    async def _search_vendors(self, request: SearchRequest) -> Tuple[List[Dict], int]:
        """Search for vendors"""
        base_query = self.db.query(Vendor)
        
        # Text search
        if request.query:
            search_terms = request.query.split()
            for term in search_terms:
                base_query = base_query.filter(
                    or_(
                        Vendor.business_name.ilike(f'%{term}%'),
                        Vendor.description.ilike(f'%{term}%')
                    )
                )
        
        # Get total count
        total_count = base_query.count()
        
        # Apply sorting
        base_query = base_query.order_by(Vendor.business_name.asc())
        
        # Apply pagination
        offset = (request.page - 1) * request.page_size
        vendors = base_query.offset(offset).limit(request.page_size).all()
        
        # Format results
        results = []
        for i, vendor in enumerate(vendors):
            # Get product count
            product_count = self.db.query(Product).filter(
                Product.vendor_id == vendor.id,
                Product.status == ProductStatus.APPROVED
            ).count()
            
            results.append({
                'id': vendor.id,
                'title': vendor.business_name,
                'description': vendor.description,
                'phone': vendor.phone,
                'email': vendor.email,
                'product_count': product_count,
                'url': f'/vendors/{vendor.id}',
                'position': offset + i + 1,
                'relevance_score': 1.0,
                'created_at': vendor.created_at.isoformat()
            })
        
        return results, total_count
    
    async def _store_search_results(self, query_id: int, results: List[Dict]):
        """Store search results for tracking"""
        for result in results:
            search_result = SearchResult(
                query_id=query_id,
                result_type=result.get('type', 'product'),
                result_id=result['id'],
                result_title=result['title'],
                result_description=result.get('description'),
                result_url=result.get('url'),
                position=result['position'],
                relevance_score=result.get('relevance_score'),
                price=result.get('price'),
                vendor_name=result.get('vendor', {}).get('name')
            )
            self.db.add(search_result)
        
        self.db.commit()
    
    async def _get_search_facets(self, request: SearchRequest, total_results: int) -> Dict[str, List[Dict]]:
        """Get facets for search filtering"""
        if request.search_type != SearchType.PRODUCT:
            return {}
        
        facets = {}
        
        # Category facet
        category_query = self.db.query(
            Product.category,
            func.count(Product.id).label('count')
        ).filter(Product.status == ProductStatus.APPROVED)
        
        if request.query:
            search_terms = request.query.split()
            for term in search_terms:
                category_query = category_query.filter(
                    or_(
                        Product.name.ilike(f'%{term}%'),
                        Product.description.ilike(f'%{term}%'),
                        Product.category.ilike(f'%{term}%')
                    )
                )
        
        categories = category_query.group_by(Product.category).all()
        facets['category'] = [
            {'value': cat.category, 'count': cat.count, 'display_name': cat.category}
            for cat in categories
        ]
        
        # Price range facet
        price_ranges = [
            {'min': 0, 'max': 50, 'display': 'Under $50'},
            {'min': 50, 'max': 100, 'display': '$50 - $100'},
            {'min': 100, 'max': 200, 'display': '$100 - $200'},
            {'min': 200, 'max': None, 'display': 'Over $200'}
        ]
        
        price_facets = []
        for price_range in price_ranges:
            query = self.db.query(func.count(Product.id)).filter(
                Product.status == ProductStatus.APPROVED,
                Product.price >= price_range['min']
            )
            if price_range['max']:
                query = query.filter(Product.price <= price_range['max'])
            
            count = query.scalar()
            if count > 0:
                price_facets.append({
                    'value': f"{price_range['min']}-{price_range['max'] or 'max'}",
                    'count': count,
                    'display_name': price_range['display']
                })
        
        facets['price_range'] = price_facets
        
        return facets
    
    async def _get_search_suggestions(self, query: str) -> List[str]:
        """Get search suggestions based on popular queries"""
        if len(query) < 2:
            return []
        
        # Get similar queries from search history
        similar_queries = self.db.query(SearchQuery.query_text).filter(
            SearchQuery.query_text.ilike(f'%{query}%'),
            SearchQuery.query_text != query
        ).group_by(SearchQuery.query_text).limit(5).all()
        
        suggestions = [q.query_text for q in similar_queries]
        
        # Add product name suggestions
        product_suggestions = self.db.query(Product.name).filter(
            Product.name.ilike(f'%{query}%'),
            Product.status == ProductStatus.APPROVED
        ).limit(3).all()
        
        suggestions.extend([p.name for p in product_suggestions])
        
        return list(set(suggestions))[:5]
    
    async def _update_session_stats(self, session_id: str):
        """Update search session statistics"""
        session = self.db.query(SearchSession).filter(
            SearchSession.session_id == session_id
        ).first()
        
        if session:
            # Count searches in this session
            search_count = self.db.query(SearchQuery).filter(
                SearchQuery.session_id == session_id
            ).count()
            
            session.total_searches = search_count
            session.updated_at = datetime.utcnow()
            self.db.commit()


class RecommendationService:
    """AI-powered recommendation service"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def get_recommendations(
        self, 
        user_id: Optional[str], 
        context_type: str,
        context_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get personalized recommendations"""
        
        # Check for existing recommendations
        existing_rec = self.db.query(UserRecommendation).filter(
            UserRecommendation.user_id == user_id,
            UserRecommendation.item_type == context_type,
            UserRecommendation.item_id == context_id,
            UserRecommendation.is_active == True,
            or_(
                UserRecommendation.expires_at.is_(None),
                UserRecommendation.expires_at > datetime.utcnow()
            )
        ).first()
        
        if existing_rec:
            return await self._format_recommendations(existing_rec)
        
        # Generate new recommendations
        recommendations = await self._generate_recommendations(user_id, context_type, context_id, limit)
        
        return recommendations
    
    async def _generate_recommendations(
        self, 
        user_id: Optional[str], 
        context_type: str,
        context_id: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Generate new recommendations based on context"""
        
        if context_type == "homepage":
            return await self._get_homepage_recommendations(user_id, limit)
        elif context_type == "product_page":
            return await self._get_similar_products(context_id, limit)
        elif context_type == "category":
            return await self._get_category_recommendations(context_id, limit)
        else:
            return await self._get_trending_products(limit)
    
    async def _get_homepage_recommendations(self, user_id: Optional[str], limit: int) -> List[Dict[str, Any]]:
        """Get personalized homepage recommendations"""
        
        if user_id:
            # Get user's order history for personalization
            user_orders = self.db.query(OrderItem).join(Order).filter(
                Order.customer_phone == user_id  # Assuming user_id maps to phone
            ).all()
            
            if user_orders:
                # Recommend based on purchase history
                purchased_categories = [item.product.category for item in user_orders if item.product]
                
                if purchased_categories:
                    # Get products from similar categories
                    recommendations = self.db.query(Product).filter(
                        Product.category.in_(purchased_categories),
                        Product.status == ProductStatus.APPROVED
                    ).order_by(Product.created_at.desc()).limit(limit).all()
                    
                    return await self._format_product_recommendations(recommendations, "personalized")
        
        # Fall back to trending products
        return await self._get_trending_products(limit)
    
    async def _get_similar_products(self, product_id: str, limit: int) -> List[Dict[str, Any]]:
        """Get products similar to the given product"""
        
        # Get the source product
        source_product = self.db.query(Product).filter(Product.id == product_id).first()
        if not source_product:
            return []
        
        # Find similar products by category and price range
        similar_products = self.db.query(Product).filter(
            Product.category == source_product.category,
            Product.id != product_id,
            Product.status == ProductStatus.APPROVED,
            Product.price.between(
                source_product.price * 0.5,
                source_product.price * 2.0
            )
        ).order_by(
            func.abs(Product.price - source_product.price)
        ).limit(limit).all()
        
        return await self._format_product_recommendations(similar_products, "similar")
    
    async def _get_category_recommendations(self, category: str, limit: int) -> List[Dict[str, Any]]:
        """Get recommendations for a specific category"""
        
        products = self.db.query(Product).filter(
            Product.category == category,
            Product.status == ProductStatus.APPROVED
        ).order_by(Product.created_at.desc()).limit(limit).all()
        
        return await self._format_product_recommendations(products, "category_based")
    
    async def _get_trending_products(self, limit: int) -> List[Dict[str, Any]]:
        """Get trending/popular products"""
        
        # Get products with recent orders
        trending_products = self.db.query(Product).join(OrderItem).join(Order).filter(
            Order.created_at >= datetime.utcnow() - timedelta(days=7),
            Product.status == ProductStatus.APPROVED
        ).group_by(Product.id).order_by(
            func.count(OrderItem.id).desc()
        ).limit(limit).all()
        
        if not trending_products:
            # Fall back to newest products
            trending_products = self.db.query(Product).filter(
                Product.status == ProductStatus.APPROVED
            ).order_by(Product.created_at.desc()).limit(limit).all()
        
        return await self._format_product_recommendations(trending_products, "trending")
    
    async def _format_product_recommendations(self, products: List[Product], rec_type: str) -> List[Dict[str, Any]]:
        """Format product recommendations"""
        
        recommendations = []
        for product in products:
            vendor = self.db.query(Vendor).filter(Vendor.id == product.vendor_id).first()
            
            recommendations.append({
                'id': product.id,
                'title': product.name,
                'description': product.description,
                'price': float(product.price),
                'currency': 'USD',
                'category': product.category,
                'vendor': {
                    'id': vendor.id if vendor else None,
                    'name': vendor.business_name if vendor else 'Unknown'
                },
                'image_url': getattr(product, 'image_url', None),
                'url': f'/products/{product.id}',
                'recommendation_type': rec_type,
                'confidence_score': 0.85,  # Would be calculated by ML model
                'reason': self._get_recommendation_reason(rec_type)
            })
        
        return recommendations
    
    async def _format_recommendations(self, recommendation: UserRecommendation) -> List[Dict[str, Any]]:
        """Format existing recommendation"""
        try:
            product_data = json.loads(recommendation.recommended_products) if isinstance(recommendation.recommended_products, str) else recommendation.recommended_products
            return product_data
        except:
            return []
    
    def _get_recommendation_reason(self, rec_type: str) -> str:
        """Get explanation for recommendation"""
        reasons = {
            "personalized": "Based on your purchase history",
            "similar": "Similar to what you're viewing",
            "trending": "Popular right now",
            "category_based": "Top picks in this category",
            "cross_sell": "Frequently bought together",
            "up_sell": "Customers also considered"
        }
        return reasons.get(rec_type, "Recommended for you")
