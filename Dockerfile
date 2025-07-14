# Dockerfile for a Python application using Uvicorn
    FROM python:3.13-slim

  WORKDIR /app/app

  # Install system dependencies if needed
  RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt

  COPY . .

  EXPOSE 8000

  # Direct command without shell
  CMD ["sh", "-c",  "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]