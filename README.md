# PeerNest AI Categorization Service

FastAPI service for AI-powered categorization of user struggles using Groq LLM API.

## Technology Stack
- **Runtime**: Python 3.11
- **Framework**: FastAPI
- **AI**: Groq LLM API (Llama models)
- **Caching**: Redis (optional)
- **Container**: Docker with Distroless

## Quick Start

### Development
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run development server
python run_dev.py
```

### Production (Docker)
```bash
docker build -t peernest-ai-service .
docker run -p 8000:8000 -e GROQ_API_KEY=your_key peernest-ai-service
```

## Environment Variables
Create `.env` file:
```env
GROQ_API_KEY="your-groq-api-key"
MODEL_NAME="llama3-70b-8192"
REDIS_URL="redis://localhost:6379/0"
CACHE_TTL_SECONDS=300
LOG_LEVEL="INFO"
```

## API Endpoints
- **Health**: `GET /health` - Service health check
- **Info**: `GET /api/v1/info` - Service configuration
- **Categorize**: `POST /api/v1/categorize` - Single categorization
- **Bulk**: `POST /api/v1/categorize/bulk` - Multiple categorizations
- **Docs**: `GET /docs` - Interactive API documentation

## Features
- **95 subcategories** across 18 main mental health categories
- **Crisis detection** for urgent situations
- **Fallback system** when AI fails (keyword-based)
- **Redis caching** with in-memory fallback
- **Bulk processing** up to 10 concurrent requests

## Integration
Called by PeerNest Backend API for user struggle categorization and room matching.

## Deployment (Coolify)
1. Set `GROQ_API_KEY` in environment variables
2. Use Docker build pack
3. Port: 8000
4. Health check: `/health`
5. Optional: Set up Redis for caching