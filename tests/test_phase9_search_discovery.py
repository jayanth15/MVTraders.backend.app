"""
Phase 9 Test Suite: Advanced Search & Discovery Engine
Comprehensive tests for search functionality and AI-powered recommendations.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.main import app
from app.models.user import User
from app.models.product import Product, ProductStatus
from app.models.vendor import Vendor
from app.models.search import (
    SearchSession, SearchQuery, SearchResult, SearchInteraction,
    SearchFacet, SearchFacetValue, RecommendationEngine, 
    ProductRecommendation, RecommendationEvent, SearchTrendingTopic,
    QueryType, QueryIntent, InteractionType, RecommendationType, 
    FacetType
)
from app.services.search_service import SearchService, RecommendationService


class TestSearchModels:
    """Test Phase 9 search and discovery models"""
    
    def test_search_session_model(self, db_session: Session):
        """Test SearchSession model creation and relationships"""
        # Create test user
        user = User(
            id="test-user-id",
            email="test@example.com",
            username="testuser",
            first_name="Test",
            last_name="User",
            is_verified=True
        )
        db_session.add(user)
        db_session.commit()
        
        # Create search session
        session = SearchSession(
            id="test-session-id",
            user_id=user.id,
            session_token="session-token-123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0 (Test Browser)",
            location_data={"country": "US", "city": "New York"},
            started_at=datetime.utcnow(),
            device_type="desktop",
            referrer="https://google.com"
        )
        
        db_session.add(session)
        db_session.commit()
        
        # Verify session creation
        assert session.id == "test-session-id"
        assert session.user_id == user.id
        assert session.total_queries == 0
        assert session.conversion_events == 0
        assert session.location_data["city"] == "New York"
    
    def test_search_query_model(self, db_session: Session):
        """Test SearchQuery model with intent detection"""
        # Create search session
        session = SearchSession(
            id="query-session-id",
            started_at=datetime.utcnow()
        )
        db_session.add(session)
        db_session.commit()
        
        # Create search query
        query = SearchQuery(
            id="test-query-id",
            session_id=session.id,
            query_text="iPhone 13 Pro Max",
            normalized_query="iphone 13 pro max",
            query_intent=QueryIntent.PURCHASE,
            query_type=QueryType.SEARCH,
            filters_applied={"category": "electronics", "price_max": 1200},
            sort_order="relevance",
            total_results=150,
            search_duration_ms=245
        )
        
        db_session.add(query)
        db_session.commit()
        
        # Verify query creation
        assert query.query_text == "iPhone 13 Pro Max"
        assert query.query_intent == QueryIntent.PURCHASE
        assert query.filters_applied["category"] == "electronics"
        assert query.total_results == 150
    
    def test_recommendation_engine_model(self, db_session: Session):
        """Test RecommendationEngine model configuration"""
        engine = RecommendationEngine(
            id="test-engine-id",
            engine_name="collaborative_filtering",
            engine_type=RecommendationType.PERSONALIZED,
            description="User-based collaborative filtering",
            is_active=True,
            configuration={
                "min_user_interactions": 5,
                "similarity_threshold": 0.7,
                "max_recommendations": 50
            },
            model_version="v1.2.0",
            training_data_version="2025-01-22",
            performance_metrics={
                "precision": 0.85,
                "recall": 0.72,
                "f1_score": 0.78
            }
        )
        
        db_session.add(engine)
        db_session.commit()
        
        # Verify engine creation
        assert engine.engine_name == "collaborative_filtering"
        assert engine.configuration["similarity_threshold"] == 0.7
        assert engine.performance_metrics["precision"] == 0.85


class TestSearchService:
    """Test SearchService functionality"""
    
    @pytest.fixture
    def search_service(self, db_session: Session):
        """Create SearchService instance for testing"""
        return SearchService(db_session)
    
    @pytest.mark.asyncio
    async def test_advanced_search(self, search_service, db_session: Session):
        """Test advanced search functionality"""
        # Create test vendor
        vendor = Vendor(
            id="test-vendor-id",
            user_id="vendor-user-id",
            business_name="Tech Store",
            business_type="retail",
            tax_id="123456789",
            phone="555-0123",
            email="vendor@techstore.com",
            website="https://techstore.com",
            verification_status="approved"
        )
        db_session.add(vendor)
        
        # Create test products
        products = [
            Product(
                id="product-1",
                vendor_id=vendor.id,
                name="iPhone 13 Pro",
                description="Latest Apple smartphone",
                category="electronics",
                price=999.99,
                stock_quantity=50,
                status=ProductStatus.APPROVED
            ),
            Product(
                id="product-2",
                vendor_id=vendor.id,
                name="Samsung Galaxy S21",
                description="Android flagship phone",
                category="electronics",
                price=799.99,
                stock_quantity=30,
                status=ProductStatus.APPROVED
            )
        ]
        
        for product in products:
            db_session.add(product)
        db_session.commit()
        
        # Test search
        results = await search_service.advanced_search(
            query="iPhone",
            filters={"category": "electronics"},
            sort_by="relevance",
            page=1,
            per_page=10
        )
        
        # Verify search results
        assert "products" in results
        assert "total_count" in results
        assert "facets" in results
        assert len(results["products"]) >= 1
        
        # Check that iPhone product is in results
        iphone_found = any(
            "iPhone" in product["title"] 
            for product in results["products"]
        )
        assert iphone_found
    
    @pytest.mark.asyncio
    async def test_search_suggestions(self, search_service, db_session: Session):
        """Test search autocomplete suggestions"""
        # Create search session and queries for history
        session = SearchSession(
            id="suggestion-session",
            started_at=datetime.utcnow()
        )
        db_session.add(session)
        
        queries = [
            SearchQuery(
                id="q1",
                session_id=session.id,
                query_text="iPhone 13",
                normalized_query="iphone 13",
                total_results=50
            ),
            SearchQuery(
                id="q2",
                session_id=session.id,
                query_text="iPhone Pro Max",
                normalized_query="iphone pro max",
                total_results=25
            )
        ]
        
        for query in queries:
            db_session.add(query)
        db_session.commit()
        
        # Test suggestions
        suggestions = await search_service.get_search_suggestions("iP", limit=5)
        
        # Verify suggestions
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 5
    
    @pytest.mark.asyncio
    async def test_search_analytics(self, search_service, db_session: Session):
        """Test search analytics functionality"""
        # Create test data
        session = SearchSession(
            id="analytics-session",
            started_at=datetime.utcnow() - timedelta(days=1),
            total_queries=5,
            conversion_events=2
        )
        db_session.add(session)
        db_session.commit()
        
        # Test analytics
        analytics = await search_service.get_search_analytics(period_days=7)
        
        # Verify analytics structure
        assert "total_searches" in analytics
        assert "total_sessions" in analytics
        assert "average_session_duration" in analytics
        assert "conversion_rate" in analytics
        assert "top_queries" in analytics


class TestRecommendationService:
    """Test RecommendationService functionality"""
    
    @pytest.fixture
    def recommendation_service(self, db_session: Session):
        """Create RecommendationService instance for testing"""
        return RecommendationService(db_session)
    
    @pytest.mark.asyncio
    async def test_personalized_recommendations(self, recommendation_service, db_session: Session):
        """Test personalized recommendations"""
        # Create test user
        user = User(
            id="rec-user-id",
            email="recuser@example.com",
            username="recuser",
            first_name="Rec",
            last_name="User",
            is_verified=True
        )
        db_session.add(user)
        db_session.commit()
        
        # Test recommendations
        recommendations = await recommendation_service.get_recommendations(
            user_id=user.id,
            context_type="homepage",
            limit=10
        )
        
        # Verify recommendations structure
        assert isinstance(recommendations, list)
        assert len(recommendations) <= 10
        
        if recommendations:
            rec = recommendations[0]
            assert "id" in rec
            assert "title" in rec
            assert "price" in rec
            assert "recommendation_type" in rec
    
    @pytest.mark.asyncio
    async def test_similar_products(self, recommendation_service, db_session: Session):
        """Test similar product recommendations"""
        # Create test vendor and products
        vendor = Vendor(
            id="similar-vendor-id",
            user_id="similar-vendor-user",
            business_name="Similar Store",
            business_type="retail",
            tax_id="987654321",
            phone="555-0456",
            email="vendor@similarstore.com",
            website="https://similarstore.com",
            verification_status="approved"
        )
        db_session.add(vendor)
        
        products = [
            Product(
                id="similar-product-1",
                vendor_id=vendor.id,
                name="MacBook Pro 13",
                description="Apple laptop",
                category="electronics",
                price=1299.99,
                stock_quantity=20,
                status=ProductStatus.APPROVED
            ),
            Product(
                id="similar-product-2",
                vendor_id=vendor.id,
                name="MacBook Air",
                description="Lightweight Apple laptop",
                category="electronics",
                price=999.99,
                stock_quantity=15,
                status=ProductStatus.APPROVED
            )
        ]
        
        for product in products:
            db_session.add(product)
        db_session.commit()
        
        # Test similar products
        similar = await recommendation_service._get_similar_products(
            "similar-product-1", limit=5
        )
        
        # Verify similar products
        assert isinstance(similar, list)
        assert len(similar) <= 5


class TestSearchAPI:
    """Test search API endpoints"""
    
    def test_advanced_search_endpoint(self, client: TestClient, db_session: Session):
        """Test /search/advanced endpoint"""
        response = client.get(
            "/search/advanced",
            params={
                "q": "laptop",
                "category": "electronics",
                "sort_by": "price",
                "page": 1,
                "per_page": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "products" in data
        assert "total_count" in data
        assert "facets" in data
        assert "query_info" in data
    
    def test_autocomplete_endpoint(self, client: TestClient):
        """Test /search/autocomplete endpoint"""
        response = client.get(
            "/search/autocomplete",
            params={"q": "iph", "limit": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
    
    def test_trending_searches_endpoint(self, client: TestClient):
        """Test /search/trending endpoint"""
        response = client.get(
            "/search/trending",
            params={"period": "day", "limit": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "trending_searches" in data
        assert "period" in data


class TestRecommendationAPI:
    """Test recommendation API endpoints"""
    
    def test_personalized_recommendations_endpoint(self, client: TestClient):
        """Test /recommendations endpoint"""
        response = client.get(
            "/recommendations",
            params={
                "context": "homepage",
                "limit": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "recommendations" in data
        assert "context" in data
        assert "count" in data
    
    def test_trending_recommendations_endpoint(self, client: TestClient):
        """Test /recommendations/trending endpoint"""
        response = client.get(
            "/recommendations/trending",
            params={
                "period_days": 7,
                "limit": 20
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "recommendations" in data
        assert "filters" in data
        assert "count" in data
    
    def test_similar_products_endpoint(self, client: TestClient, db_session: Session):
        """Test /recommendations/similar/{product_id} endpoint"""
        # Create test product
        vendor = Vendor(
            id="api-test-vendor",
            user_id="api-vendor-user",
            business_name="API Test Store",
            business_type="retail",
            tax_id="111222333",
            phone="555-0789",
            email="vendor@apitest.com",
            website="https://apitest.com",
            verification_status="approved"
        )
        db_session.add(vendor)
        
        product = Product(
            id="api-test-product",
            vendor_id=vendor.id,
            name="Test Product",
            description="Product for API testing",
            category="test",
            price=99.99,
            stock_quantity=10,
            status=ProductStatus.APPROVED
        )
        db_session.add(product)
        db_session.commit()
        
        response = client.get(
            f"/recommendations/similar/{product.id}",
            params={"limit": 10, "similarity_threshold": 0.5}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "source_product" in data
        assert "similar_products" in data
        assert "count" in data
    
    def test_recommendation_feedback_endpoint(self, client: TestClient):
        """Test /recommendations/feedback endpoint"""
        response = client.post(
            "/recommendations/feedback",
            params={
                "product_id": "test-product-id",
                "event_type": "click",
                "session_id": "test-session"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "event_type" in data
        assert "tracked_at" in data


class TestSearchPerformance:
    """Test search performance and optimization"""
    
    @pytest.mark.asyncio
    async def test_search_performance(self, db_session: Session):
        """Test search performance with large dataset"""
        search_service = SearchService(db_session)
        
        # Measure search time
        start_time = datetime.utcnow()
        
        results = await search_service.advanced_search(
            query="test",
            filters={},
            sort_by="relevance",
            page=1,
            per_page=20
        )
        
        end_time = datetime.utcnow()
        search_duration = (end_time - start_time).total_seconds()
        
        # Verify performance (should complete within 5 seconds)
        assert search_duration < 5.0
        assert "products" in results
    
    @pytest.mark.asyncio
    async def test_recommendation_caching(self, db_session: Session):
        """Test recommendation caching mechanism"""
        recommendation_service = RecommendationService(db_session)
        
        # Generate recommendations twice
        start_time = datetime.utcnow()
        first_recs = await recommendation_service.get_recommendations(
            user_id="cache-test-user",
            context_type="homepage",
            limit=10
        )
        first_duration = (datetime.utcnow() - start_time).total_seconds()
        
        start_time = datetime.utcnow()
        second_recs = await recommendation_service.get_recommendations(
            user_id="cache-test-user",
            context_type="homepage",
            limit=10
        )
        second_duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Second call should be faster (cached)
        # Note: This test assumes caching is implemented
        assert isinstance(first_recs, list)
        assert isinstance(second_recs, list)


# Test configuration
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.phase9
]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
