"""
Main FastAPI application entry point.

This module creates and configures the FastAPI application with all necessary
middleware, CORS settings, and route registrations.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from contextlib import asynccontextmanager

from config.settings import get_settings
from api.routes import router
from services.categorization_service import CategorizationService


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Async context manager for application lifespan events.
    
    This handles startup and shutdown operations for the FastAPI app.
    """
    # Startup operations
    logger.info("Starting AI Categorization Service...")
    settings = get_settings()
    logger.info(f"Service configured with model: {settings.model_name}")
    logger.info(f"Fallback categorization: {'enabled' if settings.fallback_enabled else 'disabled'}")
    
    # Initialize Redis cache connection
    categorization_service = CategorizationService(settings)
    await categorization_service.initialize()
    
    # Store service instance for access during app lifecycle
    app.state.categorization_service = categorization_service
    
    yield
    
    # Shutdown operations
    logger.info("Shutting down AI Categorization Service...")
    
    # Close Redis connections
    await app.state.categorization_service.cache_service.close()


def create_app() -> FastAPI:
    """
    Factory function to create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    settings = get_settings()
    
    # Create FastAPI instance with metadata
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-powered categorization service for peer support platform struggle analysis",
        docs_url="/docs",  # Swagger UI
        redoc_url="/redoc",  # ReDoc documentation
        lifespan=lifespan
    )
    
    # Add CORS middleware for cross-origin requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Add timing middleware for performance monitoring
    @app.middleware("http")
    async def add_process_time_header(request, call_next):
        """Add processing time to response headers."""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    # Include API routes
    app.include_router(router, prefix="/api/v1")
    
    return app


# Create the FastAPI app instance
app = create_app()


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint providing basic service information.
    
    Returns:
        dict: Service status and basic information
    """
    settings = get_settings()
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs_url": "/docs",
        "health_check": "/health"
    }


@app.get("/health", tags=["Health"])
async def health_check(request: Request):
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        dict: Detailed health status of the service
    """
    settings = get_settings()
    
    # Basic health check
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "service": settings.app_name,
        "version": settings.app_version,
        "model": settings.model_name,
        "fallback_enabled": settings.fallback_enabled,
        "environment": "development" if settings.is_development() else "production"
    }
    
    try:
        # Check Redis connection if available
        if hasattr(request.app.state, 'categorization_service'):
            cache_service = request.app.state.categorization_service.cache_service
            redis_healthy = await cache_service.test_connection()
            cache_stats = await cache_service.get_cache_stats()
            
            health_status["cache"] = {
                "type": cache_stats["cache_type"],
                "status": "connected" if redis_healthy else "fallback",
                "connection_status": cache_stats["connection_status"]
            }
        else:
            health_status["cache"] = "not_initialized"
        
        # TODO: Add Groq API connectivity check here later
        health_status["groq_api"] = "not_checked"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors.
    
    Args:
        request: The HTTP request that caused the error
        exc: The exception that was raised
        
    Returns:
        JSONResponse: Standardized error response
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": time.time()
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    api_config = settings.get_api_config()
    
    logger.info(f"Starting server on {api_config['host']}:{api_config['port']}")
    
    uvicorn.run(
        "app.main:app",
        **api_config
    )