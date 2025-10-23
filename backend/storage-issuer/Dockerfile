# Storage Issuer Service Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY . /app/

# Create directories for keys
RUN mkdir -p /run/secrets

# Expose port
EXPOSE 8001

# Run server
CMD ["python", "server.py"]
