"""
Response models for the AI Categorization Service.

These Pydantic models define the structure of API responses, ensuring
consistent output format and automatic JSON serialization.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class CategoryConfidence(BaseModel):
    """
    Individual category with confidence score.
    
    Represents a single categorization result with its confidence level.
    """
    
    category: str = Field(
        ...,
        description="The category name",
        example="Anxiety"
    )
    
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0",
        example=0.85
    )
    
    subcategories: Optional[List[str]] = Field(
        None,
        description="Related subcategories if applicable",
        example=["Work Anxiety", "Social Anxiety"]
    )


class RoomSuggestion(BaseModel):
    """
    Suggested chat room based on categorization.
    
    Provides room recommendations with reasoning.
    """
    
    room_id: str = Field(
        ...,
        description="Room identifier",
        example="anxiety-support-1"
    )
    
    room_title: str = Field(
        ...,
        description="Human-readable room title",
        example="Anxiety Support #1"
    )
    
    category: str = Field(
        ...,
        description="Primary category this room serves",
        example="Anxiety"
    )
    
    current_participants: int = Field(
        ...,
        ge=0,
        description="Current number of participants in the room",
        example=3
    )
    
    max_participants: int = Field(
        ...,
        ge=1,
        description="Maximum room capacity",
        example=5
    )
    
    estimated_wait: Optional[int] = Field(
        None,
        description="Estimated wait time in minutes if room is full",
        example=5
    )
    
    match_reason: str = Field(
        ...,
        description="Why this room was suggested",
        example="Best match for anxiety and work stress"
    )


class ProcessingMetrics(BaseModel):
    """
    Performance and processing metrics for the categorization.
    
    Useful for monitoring and optimization.
    """
    
    processing_time_ms: int = Field(
        ...,
        ge=0,
        description="Total processing time in milliseconds",
        example=234
    )
    
    groq_api_time_ms: Optional[int] = Field(
        None,
        ge=0,
        description="Time spent calling Groq API in milliseconds",
        example=189
    )
    
    model_used: str = Field(
        ...,
        description="LLM model used for categorization",
        example="mixtral-8x7b-32768"
    )
    
    tokens_used: Optional[int] = Field(
        None,
        ge=0,
        description="Number of tokens consumed in the API call",
        example=156
    )
    
    fallback_used: bool = Field(
        ...,
        description="Whether fallback categorization was used",
        example=False
    )
    
    cache_hit: bool = Field(
        default=False,
        description="Whether the response was served from cache"
    )


class CategorizationResponse(BaseModel):
    """
    Main response model for struggle categorization.
    
    This is the primary response format returned by the categorization endpoint.
    """
    
    success: bool = Field(
        ...,
        description="Whether the categorization was successful"
    )
    
    categories: List[CategoryConfidence] = Field(
        ...,
        description="List of detected categories with confidence scores"
    )
    
    primary_category: str = Field(
        ...,
        description="The highest-confidence category",
        example="Anxiety"
    )
    
    overall_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall confidence in the categorization",
        example=0.85
    )
    
    suggested_rooms: Optional[List[RoomSuggestion]] = Field(
        None,
        description="Recommended chat rooms based on categorization"
    )
    
    processing_metrics: ProcessingMetrics = Field(
        ...,
        description="Performance and processing information"
    )
    
    session_id: Optional[str] = Field(
        None,
        description="Session identifier from the request",
        example="sess_abc123def456"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Response timestamp"
    )
    
    notes: Optional[List[str]] = Field(
        None,
        description="Additional notes or warnings",
        example=["High confidence categorization", "Multiple categories detected"]
    )


class ErrorResponse(BaseModel):
    """
    Standardized error response model.
    
    Used for all error conditions across the API.
    """
    
    success: bool = Field(
        default=False,
        description="Always false for error responses"
    )
    
    error_code: str = Field(
        ...,
        description="Machine-readable error code",
        example="GROQ_API_TIMEOUT"
    )
    
    error_message: str = Field(
        ...,
        description="Human-readable error message",
        example="The AI service is temporarily unavailable"
    )
    
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )
    
    fallback_available: bool = Field(
        default=False,
        description="Whether fallback categorization is available"
    )
    
    retry_after: Optional[int] = Field(
        None,
        description="Suggested retry delay in seconds"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Error timestamp"
    )
    
    session_id: Optional[str] = Field(
        None,
        description="Session identifier from the request"
    )


class HealthCheckResponse(BaseModel):
    """
    Enhanced health check response model.
    
    Provides detailed service health information.
    """
    
    status: str = Field(
        ...,
        description="Overall service status",
        example="healthy"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Health check timestamp"
    )
    
    service_info: Dict[str, Any] = Field(
        ...,
        description="Basic service information"
    )
    
    groq_api_status: Optional[str] = Field(
        None,
        description="Groq API connectivity status",
        example="healthy"
    )
    
    last_successful_categorization: Optional[datetime] = Field(
        None,
        description="Timestamp of last successful categorization"
    )
    
    performance_metrics: Optional[Dict[str, Any]] = Field(
        None,
        description="Recent performance metrics"
    )


class BulkCategorizationResponse(BaseModel):
    """
    Response model for bulk categorization requests.
    
    Contains results for multiple categorization requests.
    """
    
    success: bool = Field(
        ...,
        description="Whether the bulk operation was successful"
    )
    
    total_requests: int = Field(
        ...,
        description="Total number of requests processed"
    )
    
    successful_requests: int = Field(
        ...,
        description="Number of successfully processed requests"
    )
    
    failed_requests: int = Field(
        ...,
        description="Number of failed requests"
    )
    
    results: List[CategorizationResponse] = Field(
        ...,
        description="Individual categorization results"
    )
    
    batch_id: Optional[str] = Field(
        None,
        description="Batch identifier from the request"
    )
    
    processing_time_ms: int = Field(
        ...,
        description="Total batch processing time in milliseconds"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Batch completion timestamp"
    )