"""
Configuration settings for the AI Categorization Service.

This module handles all environment variables and configuration management
using Pydantic Settings for type safety and validation.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Pydantic automatically validates types and provides defaults.
    """
    
    # Groq API Configuration
    groq_api_key: str = Field(..., description="Groq API key for LLM access")
    model_name: str = Field(
        default="llama3-70b-8192",
        description="Groq model to use for categorization"
    )
    max_tokens: int = Field(
        default=1000,
        ge=100,
        le=4000,
        description="Maximum tokens in LLM response"
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="LLM temperature for response consistency"
    )
    timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Timeout for Groq API calls"
    )
    
    # Service Configuration
    fallback_enabled: bool = Field(
        default=True,
        description="Enable fallback categorization when Groq fails"
    )
    cache_ttl_seconds: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Cache time-to-live for categorization results"
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for failed API calls"
    )
    
    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    
    # API Configuration
    api_host: str = Field(
        default="0.0.0.0",
        description="Host to bind the API server"
    )
    api_port: int = Field(
        default=8000,
        ge=1000,
        le=65535,
        description="Port to bind the API server"
    )
    api_reload: bool = Field(
        default=True,
        description="Enable auto-reload in development"
    )
    
    # CORS Configuration
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5000"],
        description="Allowed CORS origins for API access"
    )
    
    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    redis_enabled: bool = Field(
        default=True,
        description="Enable Redis caching (fallback to in-memory if disabled)"
    )
    redis_max_connections: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum Redis connection pool size"
    )
    redis_timeout_seconds: int = Field(
        default=5,
        ge=1,
        le=30,
        description="Redis connection timeout"
    )
    
    # Application Metadata
    app_name: str = Field(
        default="AI Categorization Service",
        description="Application name for documentation"
    )
    app_version: str = Field(
        default="1.0.0",
        description="Application version"
    )
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Allow extra environment variables from Coolify
        case_sensitive = False
        
        # Allow environment variables to override defaults
        # Example: GROQ_API_KEY -> groq_api_key
        env_prefix = ""
    
    def get_groq_config(self) -> dict:
        """
        Get Groq-specific configuration as a dictionary.
        
        Returns:
            dict: Configuration for Groq client initialization
        """
        return {
            "api_key": self.groq_api_key,
            "model": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "timeout": self.timeout_seconds,
            "max_retries": self.max_retries
        }
    
    def get_api_config(self) -> dict:
        """
        Get API server configuration as a dictionary.
        
        Returns:
            dict: Configuration for FastAPI/Uvicorn server
        """
        return {
            "host": self.api_host,
            "port": self.api_port,
            "reload": self.api_reload,
            "log_level": self.log_level.lower()
        }
    
    def get_redis_config(self) -> dict:
        """
        Get Redis-specific configuration as a dictionary.
        
        Returns:
            dict: Configuration for Redis client initialization
        """
        return {
            "url": self.redis_url,
            "enabled": self.redis_enabled,
            "max_connections": self.redis_max_connections,
            "timeout": self.redis_timeout_seconds,
            "decode_responses": True,
            "retry_on_timeout": True
        }
    
    def is_development(self) -> bool:
        """
        Check if running in development mode.
        
        Returns:
            bool: True if in development mode
        """
        return self.api_reload or self.log_level.upper() == "DEBUG"


# Global settings instance
# This creates a singleton that can be imported throughout the app
settings = Settings()


def get_settings() -> Settings:
    """
    Dependency function to get settings instance.
    
    This is used with FastAPI's dependency injection system.
    
    Returns:
        Settings: Application settings instance
    """
    return settings