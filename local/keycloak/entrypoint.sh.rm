#!/usr/bin/env bash
# Custom entrypoint for Keycloak that handles both startup and initialization
set -Eeuo pipefail

log() { echo "$(date -Is) $*"; }

log "=== Keycloak Container Starting ==="

# Start Keycloak in the background
log "Starting Keycloak server..."
/opt/keycloak/bin/kc.sh start-dev --import-realm &
KC_PID=$!

# Wait for Keycloak to be ready
log "Waiting for Keycloak to become ready..."
sleep 10  # Initial wait for Keycloak to begin startup

READY=false
for i in {1..60}; do
    if curl -fsS http://localhost:8080/health/ready >/dev/null 2>&1; then
        log "Keycloak is ready!"
        READY=true
        break
    fi
    sleep 2
done

if [ "$READY" = false ]; then
    log "ERROR: Keycloak failed to become ready within timeout"
    kill $KC_PID 2>/dev/null || true
    exit 1
fi

# Run initialization script
log "Running Keycloak initialization..."
if [ -f /opt/keycloak/init_keycloak.sh ]; then
    cd /opt/keycloak
    bash /opt/keycloak/init_keycloak.sh || {
        log "ERROR: Keycloak initialization failed"
        kill $KC_PID 2>/dev/null || true
        exit 1
    }
    log "Keycloak initialization completed successfully"
else
    log "WARN: init_keycloak.sh not found, skipping initialization"
fi

# Signal handling for graceful shutdown
cleanup() {
    log "Shutting down Keycloak..."
    kill $KC_PID 2>/dev/null || true
    wait $KC_PID 2>/dev/null || true
}
trap cleanup TERM INT EXIT

# Keep Keycloak running in foreground
log "=== Keycloak is ready and initialized ==="
wait $KC_PID
