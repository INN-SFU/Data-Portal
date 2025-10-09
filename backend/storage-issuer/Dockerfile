# Storage Issuer Service Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
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
