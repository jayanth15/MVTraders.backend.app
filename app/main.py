"""
MvTraders FastAPI Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.database import init_db


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting up MvTraders API...")
    init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down MvTraders API...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="MvTraders vendor marketplace API with phone-based authentication",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-CSRF-Token"
    ],
    expose_headers=["*"],
    max_age=3600,
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to MvTraders API",
        "version": settings.app_version,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version
    }


# Import and include API routers
from app.api.main import api_router

app.include_router(api_router, prefix=settings.api_v1_prefix)

# Note: Additional routers will be added in future phases
# from app.api.v1.users import router as users_router
# from app.api.v1.vendors import router as vendors_router
# from app.api.v1.organizations import router as organizations_router

# app.include_router(users_router, prefix=f"{settings.api_v1_prefix}/users", tags=["users"])
# app.include_router(vendors_router, prefix=f"{settings.api_v1_prefix}/vendors", tags=["vendors"])
# app.include_router(organizations_router, prefix=f"{settings.api_v1_prefix}/organizations", tags=["organizations"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0", 
        port=8000,
        reload=settings.debug,
        log_level="info"
    )
