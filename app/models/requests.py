"""
Request models for the AI Categorization Service.

These Pydantic models define and validate the structure of incoming API requests.
They provide automatic validation, serialization, and documentation.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
import re


class CategorizationRequest(BaseModel):
    """
    Request model for struggle categorization.
    
    This model validates and structures the incoming categorization requests
    from the Express backend.
    """
    
    struggle_text: str = Field(
        ...,  # Required field
        min_length=10,
        max_length=2000,
        description="User's description of their struggle or challenge",
        example="I've been feeling really anxious about work lately. I can't sleep and feel overwhelmed."
    )
    
    user_agent: Optional[str] = Field(
        None,
        max_length=500,
        description="User agent string for analytics and debugging",
        example="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    
    ip_address: Optional[str] = Field(
        None,
        description="User's IP address (hashed/encrypted) for fraud prevention",
        example="192.168.1.1"
    )
    
    session_id: Optional[str] = Field(
        None,
        min_length=10,
        max_length=100,
        description="Anonymous session identifier from Express backend",
        example="sess_abc123def456"
    )
    
    priority: Optional[str] = Field(
        "normal",
        description="Request priority level",
        example="normal"
    )
    
    include_confidence: bool = Field(
        True,
        description="Whether to include confidence scores in response"
    )
    
    include_suggestions: bool = Field(
        True,
        description="Whether to include room suggestions in response"
    )
    
    @validator('struggle_text')
    def validate_struggle_text(cls, v):
        """
        Validate and clean the struggle text input.
        
        Args:
            v: The struggle text string
            
        Returns:
            str: Cleaned struggle text
            
        Raises:
            ValueError: If text contains invalid content
        """
        if not v or not v.strip():
            raise ValueError("Struggle text cannot be empty")
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', v.strip())
        
        # Basic content validation (you can expand this)
        if len(cleaned.split()) < 3:
            raise ValueError("Struggle text must contain at least 3 words")
        
        # Check for obviously spam content
        spam_indicators = ['click here', 'buy now', 'www.', 'http://', 'https://']
        if any(indicator in cleaned.lower() for indicator in spam_indicators):
            raise ValueError("Text appears to contain spam content")
        
        return cleaned
    
    @validator('priority')
    def validate_priority(cls, v):
        """Validate priority field."""
        valid_priorities = ['low', 'normal', 'high', 'urgent']
        if v not in valid_priorities:
            raise ValueError(f"Priority must be one of: {valid_priorities}")
        return v
    
    class Config:
        """Pydantic configuration."""
        # Generate example JSON for API documentation
        schema_extra = {
            "example": {
                "struggle_text": "I've been feeling really overwhelmed at work lately. I can't sleep and my heart races whenever I think about Monday morning. I feel like I'm failing at everything and don't know how to cope.",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "ip_address": "192.168.1.1",
                "session_id": "sess_abc123def456",
                "priority": "normal",
                "include_confidence": True,
                "include_suggestions": True
            }
        }


class HealthCheckRequest(BaseModel):
    """
    Request model for enhanced health checks.
    
    Optional model for health check endpoints that want to test
    specific functionality.
    """
    
    test_categorization: bool = Field(
        False,
        description="Whether to test the categorization pipeline"
    )
    
    test_groq_api: bool = Field(
        False,
        description="Whether to test Groq API connectivity"
    )


class BulkCategorizationRequest(BaseModel):
    """
    Request model for bulk categorization operations.
    
    For processing multiple struggle texts in a single request.
    Useful for batch processing or testing.
    """
    
    requests: List[CategorizationRequest] = Field(
        ...,
        min_items=1,
        max_items=10,  # Limit to prevent abuse
        description="List of categorization requests to process"
    )
    
    batch_id: Optional[str] = Field(
        None,
        description="Optional batch identifier for tracking"
    )
    
    @validator('requests')
    def validate_requests_list(cls, v):
        """Validate the list of requests."""
        if len(v) == 0:
            raise ValueError("At least one request is required")
        return v