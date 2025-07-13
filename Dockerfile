  # Use an official slim Python image for smaller size
  FROM python:3.13-slim

  # Install system dependencies if needed
  RUN apt-get update && apt-get install -y \
      gcc \
      && rm -rf /var/lib/apt/lists/*

  # Set working directory
  WORKDIR /app

  # Copy requirements first (for better caching during build)
  COPY requirements.txt .

  # Install dependencies
  RUN pip install --no-cache-dir -r requirements.txt

  # Copy the rest of the app
  COPY . .

  # Expose the port FastAPI will run on
  EXPOSE 8000

  # Health check
  HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python healthcheck.py || exit 1

  # Start the app with Uvicorn (fixed import path)
  CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]