"""
Application configuration settings
"""
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "MvTraders API"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, description="Debug mode")
    
    # Database
    database_url: str = Field(
        default="sqlite:///./mvtraders.db",
        description="Database URL"
    )
    database_echo: bool = Field(
        default=False,
        description="Echo SQL queries"
    )
    
    # Security
    secret_key: str = Field(
        default="your-super-secret-key-change-this-in-production",
        description="JWT secret key"
    )
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes"
    )
    algorithm: str = Field(
        default="HS256",
        description="JWT algorithm"
    )
    
    # Phone validation
    default_country_code: str = Field(
        default="IN",
        description="Default country code for phone validation"
    )
    
    # Super admin default credentials
    default_super_admin_username: str = Field(
        default="superadmin",
        description="Default super admin username"
    )
    default_super_admin_password: str = Field(
        default="admin123",
        description="Default super admin password"
    )
    default_super_admin_phone: str = Field(
        default="9999999999",
        description="Default super admin phone"
    )
    
    # API Configuration
    api_v1_prefix: str = "/api/v1"
    cors_origins: List[str] = [
        "*",
        "http://localhost:3000", 
        "http://localhost:8080", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:5173",  # Vite default
        "http://localhost:4200",  # Angular default
        "http://127.0.0.1:4200"   # Angular default
    ]
    
    # File upload
    max_file_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="Maximum file size in bytes"
    )
    allowed_image_types: List[str] = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
