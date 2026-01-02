#!/usr/bin/env python3
"""
FastAPI Backend - AutoGen Development Assistant Web API

This FastAPI application provides a RESTful API and WebSocket interface
for the AutoGen Development Assistant, reusing the existing CLI core.

Run with: uvicorn backend.main:app --reload
"""

import sys
from pathlib import Path

# Add parent directory to path to import existing modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from backend.core.config import settings
from backend.api.v1.api import api_router
from backend.db.session import engine, Base

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown events"""
    # Startup
    logger.info("Starting FastAPI application...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"API Version: {settings.API_VERSION}")

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created/verified")

    yield

    # Shutdown
    logger.info("Shutting down FastAPI application...")
    await engine.dispose()


# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="RESTful API for AutoGen Development Assistant",
    version=settings.API_VERSION,
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Middleware setup
# 1. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )


# Health check endpoint (root level)
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers"""
    return {
        "status": "healthy",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "message": "AutoGen Development Assistant API",
        "version": settings.API_VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
        "health": "/health"
    }


# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to responses"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Development only
        log_level="info"
    )
