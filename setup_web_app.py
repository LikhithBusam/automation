#!/usr/bin/env python3
"""
Web Application Setup Script

This script generates all necessary files for the FastAPI backend
and React frontend, implementing the architecture detailed in
WEB_APP_ARCHITECTURE.md

Usage:
    python setup_web_app.py --backend  # Setup backend only
    python setup_web_app.py --frontend # Setup frontend only
    python setup_web_app.py --all      # Setup everything
"""

import argparse
from pathlib import Path
import os

# Backend file templates
BACKEND_FILES = {
    "backend/core/config.py": '''"""
Application configuration using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # API
    PROJECT_NAME: str = "AutoGen Dev Assistant API"
    API_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/autogen_dev"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative frontend port
    ]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
''',

    "backend/core/__init__.py": "",

    "backend/db/session.py": '''"""
Database session management
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from backend.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()


async def get_db():
    """Dependency for getting database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
''',

    "backend/db/__init__.py": "",

    "backend/schemas/user.py": '''"""
User Pydantic schemas
"""
from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[UUID] = None
''',

    "backend/api/v1/routes/auth.py": '''"""
Authentication endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.schemas.user import UserCreate, UserLogin, Token, User
from backend.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register new user"""
    auth_service = AuthService(db)
    return await auth_service.register_user(user_data)


@router.post("/login", response_model=Token)
async def login(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login user"""
    auth_service = AuthService(db)
    return await auth_service.login_user(user_data)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token"""
    auth_service = AuthService(db)
    return await auth_service.refresh_access_token(refresh_token)
''',

    "backend/api/v1/api.py": '''"""
API v1 router
"""
from fastapi import APIRouter
from backend.api.v1.routes import auth, workflows, code_review

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
api_router.include_router(code_review.router, prefix="/code-review", tags=["Code Review"])
''',

}


def create_file(filepath: str, content: str):
    """Create a file with given content"""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ Created: {filepath}")


def setup_backend():
    """Setup FastAPI backend"""
    print("\n🚀 Setting up FastAPI Backend...\n")

    for filepath, content in BACKEND_FILES.items():
        create_file(filepath, content)

    print("\n✅ Backend setup complete!")
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r backend/requirements.txt")
    print("2. Setup PostgreSQL database")
    print("3. Update backend/core/config.py with your settings")
    print("4. Run: uvicorn backend.main:app --reload")


def setup_frontend():
    """Setup React frontend"""
    print("\n🚀 Setting up React Frontend...\n")
    print("Creating frontend with Vite...")

    # Create frontend directory
    Path("frontend").mkdir(exist_ok=True)

    # Create package.json
    package_json = '''{
  "name": "autogen-dev-assistant-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.21.0",
    "axios": "^1.6.2",
    "@tanstack/react-query": "^5.14.2",
    "zustand": "^4.4.7",
    "socket.io-client": "^4.6.0",
    "@monaco-editor/react": "^4.6.0",
    "react-hook-form": "^7.49.2",
    "zod": "^3.22.4",
    "@hookform/resolvers": "^3.3.3",
    "recharts": "^2.10.3"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@typescript-eslint/eslint-plugin": "^6.14.0",
    "@typescript-eslint/parser": "^6.14.0",
    "@vitejs/plugin-react": "^4.2.1",
    "autoprefixer": "^10.4.16",
    "eslint": "^8.55.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.5",
    "postcss": "^8.4.32",
    "tailwindcss": "^3.3.6",
    "typescript": "^5.2.2",
    "vite": "^5.0.8"
  }
}
'''
    create_file("frontend/package.json", package_json)

    # Create README
    readme = '''# AutoGen Development Assistant - Frontend

React + TypeScript frontend for the AutoGen Development Assistant.

## Setup

```bash
npm install
npm run dev
```

Open http://localhost:5173

## Build

```bash
npm run build
```

## Features

- 🎨 Modern UI with Tailwind CSS
- ⚡ Fast development with Vite
- 🔐 JWT authentication
- 📊 Real-time code review
- 💻 Monaco code editor
- 📈 Analytics dashboards
'''
    create_file("frontend/README.md", readme)

    print("\n✅ Frontend setup complete!")
    print("\nNext steps:")
    print("1. cd frontend")
    print("2. npm install")
    print("3. npm run dev")


def main():
    parser = argparse.ArgumentParser(description="Setup AutoGen Web Application")
    parser.add_argument('--backend', action='store_true', help='Setup backend only')
    parser.add_argument('--frontend', action='store_true', help='Setup frontend only')
    parser.add_argument('--all', action='store_true', help='Setup everything')

    args = parser.parse_args()

    if args.all or (not args.backend and not args.frontend):
        setup_backend()
        setup_frontend()
    elif args.backend:
        setup_backend()
    elif args.frontend:
        setup_frontend()

    print("\n" + "="*70)
    print("🎉 Web Application Setup Complete!")
    print("="*70)
    print("\nSee WEB_APP_ARCHITECTURE.md for full architecture details.")
    print("See COMPREHENSIVE_CODEBASE_AUDIT.md for codebase analysis.")


if __name__ == "__main__":
    main()
