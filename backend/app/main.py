"""Main FastAPI application"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.redis import redis_manager
from app.services.cache_service import CacheService
from app.api import chat, auth, cbt_stages
from middleware.security import (
    SecurityHeadersMiddleware,
    SQLInjectionProtectionMiddleware,
    XSSProtectionMiddleware,
    RateLimitMiddleware,
    CSRFProtectionMiddleware,
    RequestValidationMiddleware,
    AuditLoggingMiddleware,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("🚀 Starting Mindful AI Counselor Backend...")

    # Initialize database
    print("📊 Initializing database...")
    await init_db()

    # Initialize Redis
    print("🔴 Connecting to Redis...")
    await redis_manager.connect()

    # Initialize FAQ cache
    print("💬 Initializing FAQ cache...")
    cache_service = CacheService(redis_manager)
    faq_count = await cache_service.initialize_faq_cache()
    print(f"✅ Cached {faq_count} FAQs")

    print("✅ Application started successfully!")

    yield

    # Shutdown
    print("👋 Shutting down...")

    # Close connections
    await redis_manager.disconnect()
    await close_db()

    print("✅ Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Production-grade AI counseling chatbot with crisis detection",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware (order matters - add from innermost to outermost)
# 1. Audit logging (innermost - logs everything)
app.add_middleware(AuditLoggingMiddleware)

# 2. Request validation
app.add_middleware(RequestValidationMiddleware)

# 3. CSRF protection
app.add_middleware(CSRFProtectionMiddleware, allowed_origins=settings.ALLOWED_ORIGINS)

# 4. Rate limiting (uses Redis if available)
app.add_middleware(RateLimitMiddleware, redis_manager=redis_manager)

# 5. XSS protection
app.add_middleware(XSSProtectionMiddleware)

# 6. SQL injection protection
app.add_middleware(SQLInjectionProtectionMiddleware)

# 7. Security headers (outermost - adds headers to all responses)
app.add_middleware(SecurityHeadersMiddleware)


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Mindful AI Counselor API",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
    }


# Include routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(cbt_stages.router)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle uncaught exceptions"""
    print(f"❌ Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "type": "internal_error",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
