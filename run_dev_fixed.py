#!/usr/bin/env python3
"""
Fixed development server startup script that ensures correct model is used.
"""

import os
import uvicorn

# Clear any old MODEL_NAME environment variable
if 'MODEL_NAME' in os.environ:
    print(f"🔧 Clearing old MODEL_NAME environment variable: {os.environ['MODEL_NAME']}")
    del os.environ['MODEL_NAME']

# Import after clearing environment
from app.main import app
from app.config.settings import settings

if __name__ == "__main__":
    print(f"🚀 Starting AI Categorization Service v{settings.app_version}")
    print(f"📋 Model: {settings.model_name}")
    print(f"🌐 Server: http://{settings.api_host}:{settings.api_port}")
    print(f"📚 Docs: http://{settings.api_host}:{settings.api_port}/docs")
    print(f"🔧 Environment: {'Development' if settings.is_development() else 'Production'}")
    print("=" * 50)
    
    # Start the server
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
        app_dir=".",
        access_log=settings.is_development()
    )