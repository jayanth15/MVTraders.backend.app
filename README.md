# MvTraders Backend API

## Overview
FastAPI-based backend for MvTraders vendor marketplace application with phone-based authentication system for Indian market.

## Tech Stack
- **Framework**: FastAPI
- **ORM**: SQLModel
- **Database**: SQLite (development) / PostgreSQL (production)
- **Testing**: Pytest
- **Authentication**: Phone-based with JWT tokens
- **Validation**: Pydantic models

## Project Structure
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py              # Configuration settings
│   ├── database.py            # Database connection and session management
│   ├── dependencies.py        # Common dependencies
│   ├── exceptions.py          # Custom exception handlers
│   ├── models/               # SQLModel database models
│   ├── schemas/              # Pydantic request/response schemas
│   ├── api/                  # API route handlers
│   ├── core/                 # Core business logic
│   ├── services/             # Business logic services
│   └── utils/                # Utility functions
├── tests/                    # Test suite
├── migrations/               # Database migrations
├── requirements.txt          # Python dependencies
├── pytest.ini              # Pytest configuration
└── TODO.md                  # Development phases and tasks
```

## Development Phases
See `TODO.md` for detailed development roadmap and current phase status.

## Getting Started
1. Install dependencies: `pip install -r requirements.txt`
2. Set up database: `python -m app.database init`
3. Run development server: `uvicorn app.main:app --reload`
4. Run tests: `pytest`

## API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
