#!/usr/bin/env bash
# Start Keycloak service with realm auto-import
set -Eeuo pipefail

echo "=== Starting Keycloak Service ==="

# Navigate to keycloak directory
cd "$(dirname "$0")"

# Load environment variables
if [ -f .env.development ]; then
    set -a
    source .env.development
    set +a
    echo "✓ Loaded .env.development"
else
    echo "ERROR: .env.development not found"
    exit 1
fi

# Create network if it doesn't exist
if ! docker network inspect ams-network >/dev/null 2>&1; then
    echo "Creating ams-network..."
    docker network create ams-network
fi

# Build the Keycloak image with realm export
echo "Building Keycloak image with realm export..."
docker build -t ams-keycloak:dev .

# Start Keycloak container with auto-import
echo "Starting Keycloak container..."
docker run -d \
    --name ams-keycloak \
    --network ams-network \
    -p 8080:8080 \
    -e KEYCLOAK_ADMIN="${KEYCLOAK_ADMIN}" \
    -e KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD}" \
    -e KC_DB="${KC_DB}" \
    -e KC_HEALTH_ENABLED="${KC_HEALTH_ENABLED}" \
    -e KC_METRICS_ENABLED="${KC_METRICS_ENABLED}" \
    -e KC_LOG_LEVEL="${KC_LOG_LEVEL}" \
    -e KC_HOSTNAME="${KC_HOSTNAME}" \
    -e KC_HOSTNAME_STRICT="${KC_HOSTNAME_STRICT}" \
    ams-keycloak:dev \
    start-dev --import-realm

echo ""
echo "=== Keycloak Service Started ==="
echo "Container: ams-keycloak"
echo "URL: http://localhost:8080"
echo "Admin Console: http://localhost:8080/admin"
echo "Credentials: ${KEYCLOAK_ADMIN} / ${KEYCLOAK_ADMIN_PASSWORD}"
echo ""
echo "Keycloak is starting and importing realm..."
echo "Wait 30-60 seconds for startup to complete"
echo ""
echo "Check status: docker logs -f ams-keycloak"
echo "Stop: docker stop ams-keycloak"
echo ""
echo "Note: Additional configuration (service accounts, scopes) will be"
echo "automatically applied when you start the backend with start_backend.sh"
echo "=========================="
