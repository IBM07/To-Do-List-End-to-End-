# ===========================================
# AuraTask - FastAPI Application Entry Point
# ===========================================

import signal
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, close_db


# ===========================================
# Graceful Shutdown Handler
# ===========================================
def handle_shutdown_signal(signum, frame):
    """Handle SIGTERM and SIGINT for graceful shutdown."""
    print(f"\n⚠️  Received signal {signum}, initiating graceful shutdown...")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, handle_shutdown_signal)
signal.signal(signal.SIGINT, handle_shutdown_signal)


# ===========================================
# Application Lifespan (Startup/Shutdown)
# ===========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    - Startup: Initialize database connection pool
    - Shutdown: Close database connections gracefully
    """
    # Startup
    print("🚀 Starting AuraTask...")
    print(f"   Environment: {settings.ENVIRONMENT}")
    print(f"   Debug Mode: {settings.DEBUG}")
    print(f"   Database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    
    # Initialize database tables (development only - use Alembic in production)
    if settings.ENVIRONMENT == "development":
        await init_db()
        print("   ✅ Database tables initialized (dev mode)")
    else:
        print("   📋 Using Alembic migrations (production mode)")
    
    yield
    
    # Shutdown
    print("👋 Shutting down AuraTask gracefully...")
    await close_db()
    print("   ✅ Database connections closed")


# ===========================================
# FastAPI Application
# ===========================================
app = FastAPI(
    title="AuraTask API",
    description="High-intelligence task manager with proactive notifications and NLP-powered task management.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ===========================================
# CORS Middleware
# ===========================================
# Dynamic CORS based on environment
cors_origins = settings.get_cors_origins
print(f"🔒 CORS Origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===========================================
# Health Check Endpoint
# ===========================================
@app.get("/", tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    return {
        "status": "AuraTask Online",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health", tags=["Health"])
async def detailed_health_check():
    """
    Detailed health check with component status.
    
    In development: Shows detailed config for debugging
    In production: Shows minimal status only
    """
    response = {
        "status": "healthy",
        "components": {
            "api": "online",
            "database": "configured",
            "redis": "configured",
        }
    }
    
    # Only show config details in development
    if settings.ENVIRONMENT == "development":
        response["config"] = {
            "db_host": settings.DB_HOST,
            "redis_host": settings.REDIS_HOST,
            "smtp_configured": settings.SMTP_USER is not None,
            "debug_mode": settings.DEBUG,
        }
    
    return response


# ===========================================
# API Routes
# ===========================================
from app.api.auth import router as auth_router
from app.api.tasks import router as tasks_router
from app.api.notifications import router as notifications_router
from app.api.websocket import router as websocket_router

# Authentication endpoints
app.include_router(
    auth_router, 
    prefix="/api/auth", 
    tags=["Authentication"]
)

# Task CRUD endpoints
app.include_router(
    tasks_router, 
    prefix="/api/tasks", 
    tags=["Tasks"]
)

# Notification settings endpoints
app.include_router(
    notifications_router, 
    prefix="/api/notifications", 
    tags=["Notifications"]
)

# WebSocket endpoint for live updates
app.include_router(
    websocket_router, 
    tags=["WebSocket"]
)
