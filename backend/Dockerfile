# AMS Backend Service Dockerfile
FROM python:3.12-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p /app/data/logs \
    /app/data/configs \
    /app/data/policies \
    /app/data/secrets \
    && adduser --disabled-password --gecos '' --uid 1000 ams \
    && chown -R ams:ams /app

# Switch to non-root user
USER ams

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${AMS_PORT:-8000}/api/health || exit 1

# Create entrypoint script
COPY --chown=ams:ams <<EOF /app/entrypoint.sh
#!/bin/bash
set -e

# Generate config.yaml from environment variables
cat > /app/config.yaml <<EOL
system:
  reset: \${SYSTEM_RESET:-false}

uvicorn:
  host: \${AMS_HOST:-0.0.0.0}
  port: \${AMS_PORT:-8000}
  reload: \${AMS_RELOAD:-false}

keycloak:
  domain: \${KEYCLOAK_DOMAIN}
  realm: \${KEYCLOAK_REALM:-ams-portal}
  ui_client_id: \${KEYCLOAK_UI_CLIENT_ID:-ams-portal-ui}
  ui_client_secret: \${KEYCLOAK_UI_CLIENT_SECRET:-}
  admin_client_id: \${KEYCLOAK_ADMIN_CLIENT_ID:-ams-portal-admin}
  admin_client_secret: \${KEYCLOAK_ADMIN_CLIENT_SECRET}
  redirect_uri: \${KEYCLOAK_REDIRECT_URI}

logging:
  config: \${LOG_CONFIG:-/app/loggers/log_config.yaml}

app:
  version: \${API_VERSION:-"0_1"}
EOL

# Generate .env file for internal paths
cat > /app/core/settings/.env <<EOL
ENFORCER_MODEL=/app/core/settings/managers/policies/casbin/model.conf
ENFORCER_POLICY=/app/core/settings/managers/policies/casbin/policy.csv
USER_POLICIES=/app/data/policies
INSTANCE_CONFIGS=/app/data/configs
EOL

# Ensure required environment variables are set
: "\${KEYCLOAK_DOMAIN:?KEYCLOAK_DOMAIN environment variable is required}"
: "\${KEYCLOAK_ADMIN_CLIENT_SECRET:?KEYCLOAK_ADMIN_CLIENT_SECRET environment variable is required}"
: "\${KEYCLOAK_REDIRECT_URI:?KEYCLOAK_REDIRECT_URI environment variable is required}"

# Start the application
exec python main.py config.yaml
EOF

RUN chmod +x /app/entrypoint.sh

# Default command
ENTRYPOINT ["/app/entrypoint.sh"]