# AMS Data Portal Dockerfile
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/loggers/logs && \
    mkdir -p /app/core/settings/security && \
    mkdir -p /app/core/settings/managers/endpoints/configs

# Create non-root user
RUN adduser --disabled-password --gecos '' --uid 1000 ams && \
    chown -R ams:ams /app
USER ams

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/test')" || exit 1

# Default command
CMD ["python", "main.py", "config.yaml"]