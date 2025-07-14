"""
Main categorization service for struggle analysis.

This service orchestrates the categorization process, handles fallbacks,
and integrates with various components to provide categorization results.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from core.groq_client import GroqClient, GroqClientError
from models.requests import CategorizationRequest
from models.responses import (
    CategorizationResponse, 
    CategoryConfidence, 
    ProcessingMetrics,
    ErrorResponse
)
from services.fallback_service import FallbackService
from services.redis_cache_service import RedisCacheService
from services.caching_service import cache_metrics
from services.monitoring_service import performance_monitor
from config.settings import Settings
from utils.categories import get_all_subcategories, get_main_category_for_subcategory
from utils.prompts import PromptEngineer

logger = logging.getLogger(__name__)


class CategorizationService:
    """
    Main service for struggle categorization.
    
    Coordinates between Groq LLM, fallback systems, caching, monitoring,
    and response formatting to provide reliable categorization results using PeerNest categories.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the categorization service with advanced features.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.groq_client = GroqClient(settings)
        self.fallback_service = FallbackService(settings)
        self.cache_service = RedisCacheService(settings)
        self.prompt_engineer = PromptEngineer()
        
        # Use PeerNest subcategories for precise matching
        self.available_categories = get_all_subcategories()
        
        logger.info(f"Categorization service initialized with {len(self.available_categories)} PeerNest subcategories")
        logger.info("Advanced features enabled: Redis caching, monitoring, enhanced prompts")
    
    async def initialize(self):
        """Initialize async components (Redis connection)."""
        await self.cache_service.initialize()
        logger.info("Categorization service async initialization completed")
    
    async def categorize(self, request: CategorizationRequest) -> CategorizationResponse:
        """
        Categorize a user's struggle description with advanced features.
        
        Args:
            request: Validated categorization request
            
        Returns:
            CategorizationResponse: Structured categorization result
        """
        start_time = time.time()
        
        try:
            logger.info(f"Processing categorization request for session: {request.session_id}")
            
            # Check cache first
            cache_key = self.cache_service.generate_cache_key(
                request.struggle_text,
                {"priority": request.priority, "session_id": request.session_id}
            )
            
            cached_result = await self.cache_service.get(cache_key)
            if cached_result:
                cache_metrics.record_hit()
                self._record_performance_metric(cached_result, request, start_time, cache_hit=True)
                logger.info(f"Cache hit for session: {request.session_id}")
                return CategorizationResponse(**cached_result)
            
            cache_metrics.record_miss()
            
            # First, try Groq LLM categorization with enhanced prompts
            try:
                result, metrics = await self._categorize_with_groq(request)
                
                # Format the successful response
                response = self._format_success_response(
                    result, 
                    metrics, 
                    request, 
                    start_time
                )
                
                # Cache the result
                cache_metrics.record_set()
                await self.cache_service.set(cache_key, response.model_dump())
                
                # Record performance metrics
                self._record_performance_metric(response.model_dump(), request, start_time)
                
                return response
                
            except GroqClientError as e:
                logger.warning(f"Groq categorization failed: {str(e)}")
                
                # Use fallback categorization if enabled
                if self.settings.fallback_enabled:
                    logger.info("Using fallback categorization")
                    response = await self._use_fallback_categorization(request, start_time, str(e))
                    
                    # Cache fallback result with shorter TTL
                    await self.cache_service.set(cache_key, response.model_dump())
                    
                    # Record performance metrics
                    self._record_performance_metric(response.model_dump(), request, start_time, fallback_used=True)
                    
                    return response
                else:
                    raise
        
        except Exception as e:
            logger.error(f"Categorization failed completely: {str(e)}")
            response = self._format_error_response(request, str(e), start_time)
            
            # Record error metrics
            self._record_performance_metric(
                response.model_dump(), 
                request, 
                start_time, 
                success=False, 
                error_type="categorization_failure"
            )
            
            return response
    
    async def _categorize_with_groq(
        self, 
        request: CategorizationRequest
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Perform categorization using Groq LLM with enhanced prompts.
        
        Args:
            request: Categorization request
            
        Returns:
            Tuple[Dict, Dict]: (categorization_result, processing_metrics)
        """
        # Create enhanced prompt
        enhanced_prompt = self.prompt_engineer.create_categorization_prompt(
            request.struggle_text,
            self.available_categories,
            {
                "session_id": request.session_id,
                "priority": request.priority
            }
        )
        
        # Use the enhanced prompt with Groq client
        return await self.groq_client.categorize_struggle(
            request.struggle_text,
            self.available_categories,
            enhanced_prompt
        )
    
    def _record_performance_metric(
        self,
        response_data: Dict[str, Any],
        request: CategorizationRequest,
        start_time: float,
        cache_hit: bool = False,
        fallback_used: bool = False,
        success: bool = True,
        error_type: str = None
    ) -> None:
        """
        Record performance metrics for monitoring.
        
        Args:
            response_data: Response data
            request: Original request
            start_time: Processing start time
            cache_hit: Whether result was from cache
            fallback_used: Whether fallback was used
            success: Whether categorization was successful
            error_type: Type of error if unsuccessful
        """
        processing_time = int((time.time() - start_time) * 1000)
        
        # Extract metrics from response
        if success and "processing_metrics" in response_data:
            metrics = response_data["processing_metrics"]
            model_used = metrics.get("model_used", "unknown")
            
            if "overall_confidence" in response_data:
                confidence = response_data["overall_confidence"]
            else:
                confidence = 0.0
            
            primary_category = response_data.get("primary_category", "unknown")
            categories_count = len(response_data.get("categories", []))
        else:
            model_used = "error"
            confidence = 0.0
            primary_category = "error"
            categories_count = 0
        
        # Record the metric
        performance_monitor.record_categorization(
            processing_time_ms=processing_time,
            model_used=model_used,
            confidence=confidence,
            primary_category=primary_category,
            categories_count=categories_count,
            fallback_used=fallback_used,
            cache_hit=cache_hit,
            session_id=request.session_id or "unknown",
            success=success,
            error_type=error_type
        )
    
    async def _use_fallback_categorization(
        self, 
        request: CategorizationRequest, 
        start_time: float,
        primary_error: str
    ) -> CategorizationResponse:
        """
        Use fallback categorization when Groq LLM fails.
        
        Args:
            request: Original categorization request
            start_time: Processing start time
            primary_error: Error from primary categorization attempt
            
        Returns:
            CategorizationResponse: Fallback categorization result
        """
        try:
            fallback_result = await self.fallback_service.categorize_struggle(
                request.struggle_text,
                self.available_categories
            )
            
            # Calculate processing metrics
            total_time = time.time() - start_time
            metrics = ProcessingMetrics(
                processing_time_ms=int(total_time * 1000),
                groq_api_time_ms=None,
                model_used="fallback_rules",
                tokens_used=None,
                fallback_used=True,
                cache_hit=False
            )
            
            # Format categories
            categories = [
                CategoryConfidence(
                    category=cat["category"],
                    confidence=cat["confidence"]
                ) for cat in fallback_result["categories"]
            ]
            
            return CategorizationResponse(
                success=True,
                categories=categories,
                primary_category=fallback_result["primary_category"],
                overall_confidence=fallback_result["overall_confidence"],
                suggested_rooms=None,  # TODO: Implement room suggestions
                processing_metrics=metrics,
                session_id=request.session_id,
                timestamp=datetime.now(),
                notes=[
                    "Primary AI categorization failed",
                    f"Fallback categorization used: {primary_error}",
                    "Consider retrying for better accuracy"
                ]
            )
            
        except Exception as fallback_error:
            logger.error(f"Fallback categorization also failed: {str(fallback_error)}")
            return self._format_error_response(
                request, 
                f"Both primary and fallback categorization failed: {primary_error}",
                start_time
            )
    
    def _format_success_response(
        self,
        result: Dict[str, Any],
        metrics: Dict[str, Any],
        request: CategorizationRequest,
        start_time: float
    ) -> CategorizationResponse:
        """
        Format a successful categorization response with PeerNest category structure.
        
        Args:
            result: Categorization result from Groq client
            metrics: Processing metrics
            request: Original request
            start_time: Processing start time
            
        Returns:
            CategorizationResponse: Formatted response with main category info
        """
        # Convert to response models with main category information
        categories = []
        for cat in result["categories"]:
            main_category = get_main_category_for_subcategory(cat["category"])
            
            category_confidence = CategoryConfidence(
                category=cat["category"],
                confidence=cat["confidence"],
                subcategories=[main_category] if main_category != "Unknown" else None
            )
            categories.append(category_confidence)
        
        processing_metrics = ProcessingMetrics(**metrics)
        
        # Generate room suggestions if requested
        suggested_rooms = None
        if request.include_suggestions:
            suggested_rooms = self._generate_room_suggestions(result["primary_category"])
        
        # Add main category information to notes
        primary_main_category = get_main_category_for_subcategory(result["primary_category"])
        notes = self._generate_response_notes(result, metrics)
        if primary_main_category != "Unknown":
            notes.append(f"Main category: {primary_main_category}")
        
        return CategorizationResponse(
            success=True,
            categories=categories,
            primary_category=result["primary_category"],
            overall_confidence=result["overall_confidence"],
            suggested_rooms=suggested_rooms,
            processing_metrics=processing_metrics,
            session_id=request.session_id,
            timestamp=datetime.now(),
            notes=notes
        )
    
    def _format_error_response(
        self,
        request: CategorizationRequest,
        error_message: str,
        start_time: float
    ) -> CategorizationResponse:
        """
        Format an error response with fallback data.
        
        Args:
            request: Original request
            error_message: Error description
            start_time: Processing start time
            
        Returns:
            CategorizationResponse: Error response with minimal categorization
        """
        total_time = time.time() - start_time
        
        # Provide minimal fallback categorization
        fallback_categories = [
            CategoryConfidence(category="General Support", confidence=0.5)
        ]
        
        processing_metrics = ProcessingMetrics(
            processing_time_ms=int(total_time * 1000),
            groq_api_time_ms=None,
            model_used="error_fallback",
            tokens_used=None,
            fallback_used=True,
            cache_hit=False
        )
        
        return CategorizationResponse(
            success=False,
            categories=fallback_categories,
            primary_category="General Support",
            overall_confidence=0.5,
            suggested_rooms=None,
            processing_metrics=processing_metrics,
            session_id=request.session_id,
            timestamp=datetime.now(),
            notes=[
                "Categorization failed",
                f"Error: {error_message}",
                "Using minimal fallback categorization",
                "Please try again or contact support"
            ]
        )
    
    def _generate_room_suggestions(self, primary_category: str) -> List[Dict[str, Any]]:
        """
        Generate room suggestions based on primary category.
        
        This is a placeholder implementation. In production, this would
        query your Express backend for actual room availability.
        
        Args:
            primary_category: The primary category to match rooms for
            
        Returns:
            List[Dict]: Room suggestions (placeholder data)
        """
        # TODO: Replace with actual room matching logic
        # This should call your Express backend to get real room data
        
        suggestions = [
            {
                "room_id": f"{primary_category.lower().replace(' ', '-')}-support-1",
                "room_title": f"{primary_category} Support #1",
                "category": primary_category,
                "current_participants": 3,
                "max_participants": 5,
                "estimated_wait": None,
                "match_reason": f"Best match for {primary_category} support"
            },
            {
                "room_id": f"{primary_category.lower().replace(' ', '-')}-support-2",
                "room_title": f"{primary_category} Support #2",
                "category": primary_category,
                "current_participants": 4,
                "max_participants": 5,
                "estimated_wait": 5,
                "match_reason": f"Alternative {primary_category} support room"
            }
        ]
        
        return suggestions
    
    def _generate_response_notes(
        self, 
        result: Dict[str, Any], 
        metrics: Dict[str, Any]
    ) -> List[str]:
        """
        Generate helpful notes for the response.
        
        Args:
            result: Categorization result
            metrics: Processing metrics
            
        Returns:
            List[str]: Response notes
        """
        notes = []
        
        # Confidence level notes
        confidence = result["overall_confidence"]
        if confidence >= 0.8:
            notes.append("High confidence categorization")
        elif confidence >= 0.6:
            notes.append("Moderate confidence categorization")
        else:
            notes.append("Low confidence categorization - consider providing more details")
        
        # Multiple categories note
        if len(result["categories"]) > 1:
            notes.append(f"Multiple categories detected ({len(result['categories'])} total)")
        
        # Performance notes
        if metrics["processing_time_ms"] > 5000:
            notes.append("Slower than usual processing time")
        
        # Model notes
        if not metrics["fallback_used"]:
            notes.append(f"Powered by {metrics['model_used']}")
        
        return notes
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check of the categorization service.
        
        Returns:
            Dict: Health check results
        """
        health_data = {
            "service_status": "healthy",
            "available_categories": len(self.available_categories),
            "fallback_enabled": self.settings.fallback_enabled,
            "groq_api_status": "unknown",
            "last_successful_categorization": None,
            "model_info": await self.groq_client.get_model_info()
        }
        
        # Test Groq API connectivity
        try:
            groq_healthy = await self.groq_client.test_connection()
            health_data["groq_api_status"] = "healthy" if groq_healthy else "unhealthy"
        except Exception as e:
            health_data["groq_api_status"] = f"error: {str(e)}"
        
        # TODO: Add more health checks:
        # - Database connectivity (if using cache)
        # - Recent error rates
        # - Performance metrics
        
        return health_data
    
    def get_available_categories(self) -> List[str]:
        """
        Get the list of available categories.
        
        Returns:
            List[str]: Available category names
        """
        return self.available_categories.copy()
    
    def set_categories(self, categories: List[str]) -> None:
        """
        Update the available categories list.
        
        This method allows you to update categories without restarting the service.
        
        Args:
            categories: New list of category names
        """
        if not categories or len(categories) == 0:
            raise ValueError("Categories list cannot be empty")
        
        self.available_categories = categories.copy()
        logger.info(f"Updated categories list to {len(categories)} categories")
    
    async def bulk_categorize(
        self, 
        requests: List[CategorizationRequest]
    ) -> List[CategorizationResponse]:
        """
        Process multiple categorization requests in parallel.
        
        Args:
            requests: List of categorization requests
            
        Returns:
            List[CategorizationResponse]: Results for each request
        """
        logger.info(f"Processing bulk categorization for {len(requests)} requests")
        
        # Process requests concurrently
        tasks = [self.categorize(request) for request in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions in the results
        formatted_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Create error response for failed requests
                error_response = self._format_error_response(
                    requests[i],
                    f"Bulk processing error: {str(result)}",
                    time.time()
                )
                formatted_results.append(error_response)
            else:
                formatted_results.append(result)
        
        return formatted_results