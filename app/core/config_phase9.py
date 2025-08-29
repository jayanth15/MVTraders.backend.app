"""
Phase 9: Advanced Search & Discovery Engine Configuration
Settings for search functionality and AI-powered recommendations.
"""

from typing import Dict, Any, List
from pydantic import BaseSettings, Field
from enum import Enum


class SearchBackend(str, Enum):
    """Available search backends"""
    DATABASE = "database"
    ELASTICSEARCH = "elasticsearch"
    OPENSEARCH = "opensearch"
    SOLR = "solr"


class RecommendationAlgorithm(str, Enum):
    """Available recommendation algorithms"""
    COLLABORATIVE_FILTERING = "collaborative_filtering"
    CONTENT_BASED = "content_based"
    HYBRID = "hybrid"
    MATRIX_FACTORIZATION = "matrix_factorization"
    DEEP_LEARNING = "deep_learning"


class SearchConfig(BaseSettings):
    """Search engine configuration"""
    
    # Search Backend Configuration
    search_backend: SearchBackend = SearchBackend.DATABASE
    elasticsearch_url: str = Field(default="http://localhost:9200", env="ELASTICSEARCH_URL")
    elasticsearch_index_prefix: str = Field(default="mvtraders", env="ELASTICSEARCH_INDEX_PREFIX")
    
    # Search Parameters
    default_search_limit: int = Field(default=20, ge=1, le=100)
    max_search_limit: int = Field(default=100, ge=1, le=500)
    search_timeout_seconds: int = Field(default=10, ge=1, le=60)
    
    # Query Processing
    enable_query_normalization: bool = True
    enable_spell_correction: bool = True
    enable_stemming: bool = True
    enable_synonym_expansion: bool = True
    
    # Autocomplete Settings
    autocomplete_min_chars: int = Field(default=2, ge=1, le=10)
    autocomplete_max_suggestions: int = Field(default=10, ge=1, le=50)
    autocomplete_cache_ttl_minutes: int = Field(default=60, ge=1, le=1440)
    
    # Faceted Search
    enable_faceted_search: bool = True
    max_facet_values: int = Field(default=20, ge=5, le=100)
    facet_min_doc_count: int = Field(default=1, ge=1, le=10)
    
    # Search Analytics
    enable_search_analytics: bool = True
    analytics_retention_days: int = Field(default=90, ge=1, le=365)
    track_search_interactions: bool = True
    
    # Performance
    enable_search_caching: bool = True
    search_cache_ttl_minutes: int = Field(default=15, ge=1, le=180)
    enable_result_pagination: bool = True
    
    class Config:
        env_file = ".env"
        env_prefix = "SEARCH_"


class RecommendationConfig(BaseSettings):
    """Recommendation engine configuration"""
    
    # Algorithm Selection
    primary_algorithm: RecommendationAlgorithm = RecommendationAlgorithm.HYBRID
    fallback_algorithm: RecommendationAlgorithm = RecommendationAlgorithm.CONTENT_BASED
    
    # Recommendation Parameters
    default_recommendation_limit: int = Field(default=10, ge=1, le=50)
    max_recommendation_limit: int = Field(default=50, ge=1, le=100)
    recommendation_timeout_seconds: int = Field(default=5, ge=1, le=30)
    
    # Personalization
    enable_personalization: bool = True
    min_user_interactions: int = Field(default=5, ge=1, le=50)
    user_preference_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    
    # Content-Based Filtering
    content_similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    content_feature_weights: Dict[str, float] = {
        "category": 0.3,
        "price": 0.2,
        "brand": 0.2,
        "description": 0.15,
        "tags": 0.15
    }
    
    # Collaborative Filtering
    collaborative_similarity_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    min_common_items: int = Field(default=3, ge=1, le=20)
    max_similar_users: int = Field(default=50, ge=10, le=200)
    
    # Trending Recommendations
    trending_period_hours: int = Field(default=24, ge=1, le=168)  # 1 hour to 1 week
    trending_min_interactions: int = Field(default=10, ge=1, le=100)
    trending_boost_factor: float = Field(default=1.5, ge=1.0, le=3.0)
    
    # Cross-Sell Recommendations
    cross_sell_confidence_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    cross_sell_min_frequency: int = Field(default=3, ge=1, le=20)
    cross_sell_time_window_days: int = Field(default=30, ge=1, le=365)
    
    # Performance & Caching
    enable_recommendation_caching: bool = True
    recommendation_cache_ttl_minutes: int = Field(default=30, ge=5, le=240)
    enable_precomputed_recommendations: bool = True
    precompute_batch_size: int = Field(default=100, ge=10, le=1000)
    
    # A/B Testing
    enable_ab_testing: bool = True
    default_experiment_allocation: float = Field(default=0.1, ge=0.0, le=0.5)
    
    # Quality Control
    recommendation_diversity_factor: float = Field(default=0.3, ge=0.0, le=1.0)
    max_same_vendor_recommendations: int = Field(default=3, ge=1, le=10)
    filter_out_of_stock: bool = True
    filter_inactive_products: bool = True
    
    class Config:
        env_file = ".env"
        env_prefix = "RECOMMENDATION_"


class SearchFacetConfig:
    """Configuration for search facets"""
    
    # Default facets for product search
    DEFAULT_FACETS = [
        {
            "name": "category",
            "type": "terms",
            "display_name": "Category",
            "field": "category",
            "order": 1,
            "is_multi_select": True,
            "show_count": True,
            "min_doc_count": 1
        },
        {
            "name": "price_range",
            "type": "range",
            "display_name": "Price Range",
            "field": "price",
            "order": 2,
            "ranges": [
                {"key": "0-50", "from": 0, "to": 50, "label": "Under $50"},
                {"key": "50-100", "from": 50, "to": 100, "label": "$50 - $100"},
                {"key": "100-250", "from": 100, "to": 250, "label": "$100 - $250"},
                {"key": "250-500", "from": 250, "to": 500, "label": "$250 - $500"},
                {"key": "500+", "from": 500, "label": "$500+"}
            ]
        },
        {
            "name": "vendor",
            "type": "terms",
            "display_name": "Vendor",
            "field": "vendor.business_name",
            "order": 3,
            "is_multi_select": True,
            "show_count": True,
            "min_doc_count": 1,
            "max_values": 10
        },
        {
            "name": "availability",
            "type": "terms",
            "display_name": "Availability",
            "field": "stock_status",
            "order": 4,
            "is_multi_select": True,
            "show_count": True,
            "values": [
                {"key": "in_stock", "label": "In Stock"},
                {"key": "low_stock", "label": "Low Stock"},
                {"key": "out_of_stock", "label": "Out of Stock"}
            ]
        },
        {
            "name": "rating",
            "type": "range",
            "display_name": "Customer Rating",
            "field": "average_rating",
            "order": 5,
            "ranges": [
                {"key": "4+", "from": 4, "label": "4+ Stars"},
                {"key": "3+", "from": 3, "label": "3+ Stars"},
                {"key": "2+", "from": 2, "label": "2+ Stars"},
                {"key": "1+", "from": 1, "label": "1+ Stars"}
            ]
        }
    ]


class AnalyticsConfig(BaseSettings):
    """Analytics and tracking configuration"""
    
    # Search Analytics
    enable_search_tracking: bool = True
    track_search_sessions: bool = True
    track_query_performance: bool = True
    track_facet_usage: bool = True
    
    # Recommendation Analytics
    enable_recommendation_tracking: bool = True
    track_recommendation_impressions: bool = True
    track_recommendation_clicks: bool = True
    track_recommendation_conversions: bool = True
    
    # Performance Monitoring
    enable_performance_monitoring: bool = True
    slow_query_threshold_ms: int = Field(default=1000, ge=100, le=10000)
    log_slow_queries: bool = True
    
    # Data Retention
    search_data_retention_days: int = Field(default=90, ge=7, le=365)
    recommendation_data_retention_days: int = Field(default=90, ge=7, le=365)
    analytics_data_retention_days: int = Field(default=365, ge=30, le=730)
    
    # Privacy
    anonymize_user_data: bool = True
    hash_ip_addresses: bool = True
    respect_do_not_track: bool = True
    
    class Config:
        env_file = ".env"
        env_prefix = "ANALYTICS_"


class Phase9Config:
    """Complete Phase 9 configuration"""
    
    def __init__(self):
        self.search = SearchConfig()
        self.recommendations = RecommendationConfig()
        self.facets = SearchFacetConfig()
        self.analytics = AnalyticsConfig()
    
    def get_elasticsearch_config(self) -> Dict[str, Any]:
        """Get Elasticsearch configuration"""
        return {
            "url": self.search.elasticsearch_url,
            "index_prefix": self.search.elasticsearch_index_prefix,
            "timeout": self.search.search_timeout_seconds,
            "settings": {
                "number_of_shards": 2,
                "number_of_replicas": 1,
                "refresh_interval": "30s"
            },
            "mappings": {
                "products": {
                    "properties": {
                        "name": {"type": "text", "analyzer": "standard"},
                        "description": {"type": "text", "analyzer": "standard"},
                        "category": {"type": "keyword"},
                        "price": {"type": "float"},
                        "vendor_id": {"type": "keyword"},
                        "stock_quantity": {"type": "integer"},
                        "average_rating": {"type": "float"},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"}
                    }
                }
            }
        }
    
    def get_recommendation_engines(self) -> List[Dict[str, Any]]:
        """Get recommendation engine configurations"""
        return [
            {
                "name": "collaborative_filtering",
                "type": "personalized",
                "algorithm": "user_based_cf",
                "config": {
                    "min_user_interactions": self.recommendations.min_user_interactions,
                    "similarity_threshold": self.recommendations.collaborative_similarity_threshold,
                    "max_similar_users": self.recommendations.max_similar_users
                }
            },
            {
                "name": "content_based",
                "type": "similar",
                "algorithm": "content_similarity",
                "config": {
                    "similarity_threshold": self.recommendations.content_similarity_threshold,
                    "feature_weights": self.recommendations.content_feature_weights
                }
            },
            {
                "name": "trending_products",
                "type": "trending",
                "algorithm": "popularity_based",
                "config": {
                    "time_window_hours": self.recommendations.trending_period_hours,
                    "min_interactions": self.recommendations.trending_min_interactions,
                    "boost_factor": self.recommendations.trending_boost_factor
                }
            },
            {
                "name": "cross_sell",
                "type": "cross_sell",
                "algorithm": "market_basket",
                "config": {
                    "confidence_threshold": self.recommendations.cross_sell_confidence_threshold,
                    "min_frequency": self.recommendations.cross_sell_min_frequency,
                    "time_window_days": self.recommendations.cross_sell_time_window_days
                }
            }
        ]


# Global configuration instance
phase9_config = Phase9Config()

# Export commonly used configurations
SEARCH_CONFIG = phase9_config.search
RECOMMENDATION_CONFIG = phase9_config.recommendations
ANALYTICS_CONFIG = phase9_config.analytics
FACET_CONFIG = phase9_config.facets

# Feature flags
FEATURES = {
    "elasticsearch_enabled": SEARCH_CONFIG.search_backend == SearchBackend.ELASTICSEARCH,
    "personalization_enabled": RECOMMENDATION_CONFIG.enable_personalization,
    "analytics_enabled": ANALYTICS_CONFIG.enable_search_tracking,
    "ab_testing_enabled": RECOMMENDATION_CONFIG.enable_ab_testing,
    "caching_enabled": SEARCH_CONFIG.enable_search_caching,
    "spell_correction_enabled": SEARCH_CONFIG.enable_spell_correction,
    "faceted_search_enabled": SEARCH_CONFIG.enable_faceted_search
}
