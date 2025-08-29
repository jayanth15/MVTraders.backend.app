"""
Database configuration and session management
"""
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool
from typing import Generator
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Create engine with proper configuration for SQLite and PostgreSQL
if settings.database_url.startswith("sqlite"):
    # SQLite configuration
    engine = create_engine(
        settings.database_url,
        echo=settings.database_echo,
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )
else:
    # PostgreSQL configuration
    engine = create_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_pre_ping=True,
        pool_recycle=300,
    )


def create_db_and_tables():
    """Create database tables"""
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def get_session() -> Generator[Session, None, None]:
    """Get database session"""
    with Session(engine) as session:
        yield session


def init_db():
    """Initialize database with default data"""
    from app.models.user import User, UserType
    from app.models.app_initialization import AppInitialization
    from app.core.security import get_password_hash
    
    create_db_and_tables()
    
    with Session(engine) as session:
        # Check if app is already initialized
        app_init = session.query(AppInitialization).first()
        if app_init and app_init.is_initialized:
            logger.info("Database already initialized")
            return
            
        # Create default super admin
        super_admin = session.query(User).filter(
            User.phone == settings.default_super_admin_phone
        ).first()
        
        if not super_admin:
            super_admin = User(
                phone=settings.default_super_admin_phone,
                username=settings.default_super_admin_username,
                password_hash=get_password_hash(settings.default_super_admin_password),
                first_name="Super",
                last_name="Admin",
                email="superadmin@mvtraders.com",
                user_type=UserType.APP_SUPER_ADMIN,
                profile_completed=True,
                is_default_login=False,
                must_change_password=False,
                is_active=True
            )
            session.add(super_admin)
            session.commit()
            session.refresh(super_admin)
            logger.info("Default super admin created")
        
        # Mark app as initialized
        if not app_init:
            app_init = AppInitialization(
                app_version=settings.app_version,
                default_super_admin_created=True,
                default_username=settings.default_super_admin_username,
                default_password_hash=get_password_hash(settings.default_super_admin_password),
                is_initialized=True
            )
            session.add(app_init)
            session.commit()
            logger.info("App initialization completed")


# Import all models to ensure they are registered with SQLModel
def import_all_models():
    """Import all models to register them with SQLModel"""
    from app.models import user
    # Other models temporarily disabled due to relationship conflicts
    # Will be restored in Phase 3
    # from app.models import (
    #     organization,
    #     vendor,
    #     product,
    #     order,
    #     review,
    #     address,
    #     app_initialization,
    #     order_form,
    # )


# Call import_all_models to register models
import_all_models()
