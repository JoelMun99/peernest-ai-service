# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Service
- **Development server**: `python run_dev.py` - Starts FastAPI with hot reload and development settings
- **Direct uvicorn**: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

### Environment Setup
- **Virtual environment required**: Activate with `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
- **Dependencies**: `pip install -r requirements.txt` (must be run inside activated venv)
- **API key**: Copy `.env` file and add your Groq API key - service requires `GROQ_API_KEY` to function
- **Redis**: Optional Redis server for distributed caching - defaults to in-memory cache if Redis unavailable

### API Endpoints
- **Service info**: `GET /api/v1/info` - Configuration and model details
- **Health check**: `GET /health` - Service health status
- **Categorization**: `POST /api/v1/categorize` - Single struggle categorization
- **Bulk processing**: `POST /api/v1/categorize/bulk` - Multiple requests
- **Documentation**: `GET /docs` - Interactive Swagger UI

## Architecture Overview

### Core Components
- **FastAPI Application** (`app/main.py`): Main application with CORS, middleware, and global exception handling
- **Groq LLM Client** (`app/core/groq_client.py`): Async client for AI categorization with retry logic and response parsing
- **Categorization Service** (`app/services/categorization_service.py`): Orchestrates LLM, fallback, caching, and monitoring
- **Redis Cache Service** (`app/services/redis_cache_service.py`): Distributed caching with Redis backend and in-memory fallback
- **Fallback Service** (`app/services/fallback_service.py`): Rule-based categorization when LLM fails
- **Settings Management** (`app/config/settings.py`): Pydantic settings with environment variable validation

### PeerNest Category System
- **95 subcategories** across 18 main categories defined in `app/utils/categories.py`
- **Hierarchical structure**: Main categories → Subcategories for precise user matching
- **Categories include**: Mental Health, Neurodivergence, LGBTQ+, Relationships, Work/School, Financial, etc.
- **Crisis categories**: Includes suicidal thoughts, self-harm, and trauma categories

### Data Flow
1. **Request validation** using Pydantic models (`app/models/`)
2. **Cache check** for previously categorized content
3. **Groq LLM categorization** with enhanced prompts and JSON parsing
4. **Fallback categorization** if LLM fails (keyword matching)
5. **Response formatting** with confidence scores and room suggestions
6. **Performance monitoring** and caching of results

### Service Features
- **Redis caching** with distributed storage and automatic in-memory fallback
- **Performance monitoring** with processing time and confidence tracking  
- **Bulk processing** with concurrent request handling
- **Fallback system** for reliability when AI fails
- **Enhanced prompting** with structured JSON responses
- **Health checks** including Groq API connectivity tests

## Configuration

### Environment Variables
- `GROQ_API_KEY`: Required for LLM access
- `MODEL_NAME`: Default "llama3-70b-8192" 
- `FALLBACK_ENABLED`: Default true for reliability
- `CACHE_TTL_SECONDS`: Default 300 (5 minutes)
- `REDIS_URL`: Default "redis://localhost:6379/0"
- `REDIS_ENABLED`: Default true (falls back to in-memory if Redis unavailable)
- `API_PORT`: Default 8000
- `LOG_LEVEL`: Default INFO

### Model Options
- `mixtral-8x7b-32768`: Balanced speed/accuracy (recommended)
- `llama3-8b-8192`: Fast inference for high volume
- `llama3-70b-8192`: Highest accuracy for complex cases

## Integration Notes

### Express Backend Integration
- **CORS configured** for `localhost:3000` and `localhost:5000`
- **Room suggestions** placeholder in responses (integrate with your room matching system)
- **Session tracking** via `session_id` in requests
- **Error handling** with structured HTTP responses

### Request/Response Models
- **Input**: `CategorizationRequest` with struggle_text, session_id, priority
- **Output**: `CategorizationResponse` with categories, confidence scores, processing metrics
- **Bulk**: `BulkCategorizationRequest/Response` for multiple items

### Monitoring Integration
- **Processing metrics** in all responses
- **Performance monitoring** service tracks success rates, response times
- **Cache metrics** for optimization insights
- **Health endpoints** for service monitoring