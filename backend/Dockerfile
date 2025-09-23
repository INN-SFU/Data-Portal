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

# Create entrypoint script
COPY --chown=${APP_USER}:${APP_USER} <<EOF ${APP_DIR}/entrypoint.sh
#!/bin/bash
set -e

# Generate config.yaml from environment variables
cat > ${APP_DIR}/config.yaml <<EOL
system:
  reset: \${SYSTEM_RESET:-false}

uvicorn:
  host: \${AMS_HOST:-0.0.0.0}
  port: \${AMS_PORT:-${APP_PORT}}
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
  config: \${LOG_CONFIG:-${APP_DIR}/loggers/log_config_processed.yaml}

app:
  version: \${API_VERSION:-"0_1"}
EOL

# Set up logging environment variables
export LOG_DIR=\${LOG_DIR:-${APP_DIR}/data/logs}
export LOG_LEVEL=\${LOG_LEVEL:-INFO}

# Process the log config template to substitute environment variables
envsubst '\${LOG_DIR} \${LOG_LEVEL}' < ${APP_DIR}/loggers/log_config.yaml > ${APP_DIR}/loggers/log_config_processed.yaml

# Generate .env file for internal paths
cat > ${APP_DIR}/core/settings/.env <<EOL
ENFORCER_MODEL=${APP_DIR}/core/settings/managers/policies/casbin/model.conf
ENFORCER_POLICY=${APP_DIR}/core/settings/managers/policies/casbin/policy.csv
USER_POLICIES=${APP_DIR}/data/policies
INSTANCE_CONFIGS=${APP_DIR}/data/configs
EOL

# Create empty policy file if it doesn't exist (for Casbin initialization)
touch ${APP_DIR}/core/settings/managers/policies/casbin/policy.csv

# Ensure required environment variables are set
: "\${KEYCLOAK_DOMAIN:?KEYCLOAK_DOMAIN environment variable is required}"
: "\${KEYCLOAK_ADMIN_CLIENT_SECRET:?KEYCLOAK_ADMIN_CLIENT_SECRET environment variable is required}"
: "\${KEYCLOAK_REDIRECT_URI:?KEYCLOAK_REDIRECT_URI environment variable is required}"

# Start the application
exec python main.py config.yaml
EOF

RUN chmod +x ${APP_DIR}/entrypoint.sh

# Default command
ENTRYPOINT ["sh", "-c", "${APP_DIR}/entrypoint.sh"]