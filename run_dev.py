#!/usr/bin/env python3
"""
Development server runner for AI Categorization Service.

This script starts the FastAPI server with development-friendly settings.
Use this for local development and testing.
"""

import uvicorn
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.config.settings import get_settings


def main():
    """
    Start the development server with hot reloading.
    """
    settings = get_settings()
    
    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    print(f"📋 Model: {settings.model_name}")
    print(f"🌐 Server: http://{settings.api_host}:{settings.api_port}")
    print(f"📚 Docs: http://{settings.api_host}:{settings.api_port}/docs")
    print(f"🔧 Environment: {'Development' if settings.is_development() else 'Production'}")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = project_root / ".env"
    if not env_file.exists():
        print("⚠️  Warning: .env file not found!")
        print("   Copy .env.example to .env and add your Groq API key")
        print("   The service will start but categorization won't work without the API key")
        print()
    
    # Start the server
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
        access_log=True,
        reload_dirs=[str(project_root / "app")]
    )


if __name__ == "__main__":
    main()