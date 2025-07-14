from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any
import time
import logging

from config.settings import get_settings, Settings
from models.requests import CategorizationRequest, BulkCategorizationRequest
from models.responses import (
    CategorizationResponse, 
    BulkCategorizationResponse,
    HealthCheckResponse,
    ErrorResponse
)
from services.categorization_service import CategorizationService

# Create router instance
router = APIRouter()

# Set up logging
logger = logging.getLogger(__name__)

# Global categorization service instance (will be initialized on first use)
_categorization_service = None


def get_categorization_service(settings: Settings = Depends(get_settings)) -> CategorizationService:
    """
    Get or create the categorization service instance.
    
    This uses a singleton pattern to ensure we only create one service instance.
    
    Args:
        settings: Injected application settings
        
    Returns:
        CategorizationService: Service instance
    """
    global _categorization_service
    if _categorization_service is None:
        _categorization_service = CategorizationService(settings)
        logger.info("Created new categorization service instance")
    return _categorization_service


@router.get("/info", tags=["Service"])
async def get_service_info(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """
    Get detailed service information and configuration.
    
    Args:
        settings: Injected application settings
        
    Returns:
        dict: Comprehensive service information
    """
    return {
        "service_name": settings.app_name,
        "version": settings.app_version,
        "model_info": {
            "name": settings.model_name,
            "max_tokens": settings.max_tokens,
            "temperature": settings.temperature,
            "timeout_seconds": settings.timeout_seconds
        },
        "features": {
            "fallback_enabled": settings.fallback_enabled,
            "cache_ttl_seconds": settings.cache_ttl_seconds,
            "max_retries": settings.max_retries
        },
        "environment": "development" if settings.is_development() else "production",
        "timestamp": time.time()
    }


@router.get("/status", tags=["Service"])
async def get_service_status() -> Dict[str, Any]:
    """
    Get current service operational status.
    
    This endpoint provides real-time status information for monitoring.
    
    Returns:
        dict: Current service status
    """
    # TODO: Add more sophisticated status checks in later phases
    # - Groq API connectivity
    # - Response time metrics
    # - Error rate monitoring
    
    return {
        "status": "operational",
        "timestamp": time.time(),
        "uptime_seconds": "not_implemented",  # TODO: Implement uptime tracking
        "requests_processed": "not_implemented",  # TODO: Add request counter
        "average_response_time": "not_implemented",  # TODO: Add timing metrics
        "last_groq_api_call": "not_implemented"  # TODO: Track last successful API call
    }


@router.post("/categorize", 
            tags=["Categorization"], 
            response_model=CategorizationResponse,
            status_code=status.HTTP_200_OK)
async def categorize_struggle(
    request: CategorizationRequest,
    service: CategorizationService = Depends(get_categorization_service)
) -> CategorizationResponse:
    """
    Categorize user struggle text into predefined categories.
    
    This is the main endpoint that handles struggle categorization using
    Groq LLM with fallback to rule-based categorization.
    
    Args:
        request: Validated categorization request
        service: Injected categorization service
        
    Returns:
        CategorizationResponse: Categorization results with confidence scores
        
    Raises:
        HTTPException: If categorization fails completely
    """
    try:
        logger.info(f"Categorization request received for session: {request.session_id}")
        
        # Process the categorization
        result = await service.categorize(request)
        
        # Log the result
        logger.info(
            f"Categorization completed - Primary: {result.primary_category}, "
            f"Confidence: {result.overall_confidence:.2f}, "
            f"Time: {result.processing_metrics.processing_time_ms}ms"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Categorization endpoint error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Categorization service error",
                "message": "Unable to process categorization request",
                "session_id": request.session_id,
                "timestamp": time.time()
            }
        )


@router.post("/categorize/bulk",
            tags=["Categorization"],
            response_model=BulkCategorizationResponse,
            status_code=status.HTTP_200_OK)
async def bulk_categorize_struggles(
    request: BulkCategorizationRequest,
    service: CategorizationService = Depends(get_categorization_service)
) -> BulkCategorizationResponse:
    """
    Process multiple categorization requests in parallel.
    
    Args:
        request: Bulk categorization request
        service: Injected categorization service
        
    Returns:
        BulkCategorizationResponse: Results for all requests
    """
    start_time = time.time()
    
    try:
        logger.info(f"Bulk categorization request for {len(request.requests)} items")
        
        # Process all requests
        results = await service.bulk_categorize(request.requests)
        
        # Calculate statistics
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_time = int((time.time() - start_time) * 1000)
        
        response = BulkCategorizationResponse(
            success=True,
            total_requests=len(request.requests),
            successful_requests=successful,
            failed_requests=failed,
            results=results,
            batch_id=request.batch_id,
            processing_time_ms=total_time
        )
        
        logger.info(f"Bulk categorization completed: {successful}/{len(results)} successful")
        return response
        
    except Exception as e:
        logger.error(f"Bulk categorization error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Bulk categorization failed",
                "message": str(e),
                "batch_id": request.batch_id,
                "timestamp": time.time()
            }
        )


@router.get("/models", tags=["Service"])
async def get_available_models(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """
    Get information about available LLM models.
    
    Args:
        settings: Injected application settings
        
    Returns:
        dict: Available models and current configuration
    """
    return {
        "current_model": settings.model_name,
        "available_models": [
            {
                "name": "mixtral-8x7b-32768",
                "description": "Balanced speed and accuracy",
                "recommended_for": "General categorization tasks"
            },
            {
                "name": "llama3-8b-8192",
                "description": "Fast inference, good for simple tasks",
                "recommended_for": "High-volume, simple categorization"
            },
            {
                "name": "llama3-70b-8192",
                "description": "Highest accuracy, slower inference",
                "recommended_for": "Complex categorization requiring nuance"
            }
        ],
        "configuration": {
            "max_tokens": settings.max_tokens,
            "temperature": settings.temperature,
            "timeout_seconds": settings.timeout_seconds
        }
    }

