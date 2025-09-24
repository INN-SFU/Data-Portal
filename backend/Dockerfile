# AMS Backend Service Dockerfile
FROM python:3.12-slim

# Build arguments for full portability
ARG APP_DIR=/app
ARG APP_USER=ams
ARG APP_UID=1000
ARG APP_PORT=8000

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=${APP_DIR} \
    APP_DIR=${APP_DIR} \
    APP_USER=${APP_USER} \
    APP_PORT=${APP_PORT}

# Set work directory
WORKDIR ${APP_DIR}

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    gettext-base \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p ${APP_DIR}/data/logs \
    ${APP_DIR}/data/configs \
    ${APP_DIR}/data/policies \
    ${APP_DIR}/data/secrets \
    && adduser --disabled-password --gecos '' --uid ${APP_UID} ${APP_USER} \
    && chown -R ${APP_USER}:${APP_USER} ${APP_DIR}

# Switch to non-root user
USER ${APP_USER}

# Expose port
EXPOSE ${APP_PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${APP_PORT}/api/health/ready || exit 1

# Copy and setup entrypoint script
COPY --chown=${APP_USER}:${APP_USER} entrypoint.sh ${APP_DIR}/entrypoint.sh
RUN chmod +x ${APP_DIR}/entrypoint.sh

# Default command
ENTRYPOINT ["sh", "-c", "${APP_DIR}/entrypoint.sh"]