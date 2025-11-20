#!/usr/bin/env bash
# Backend entrypoint - assumes Keycloak is already configured via init_keycloak.sh
set -Eeuo pipefail
source /app/entrypoint_helpers.sh

log "=== Backend Startup ==="

# --- Connect to Keycloak and fetch credentials ---
require_all_backend_envs
wait_for_realm
fetch_admin_token
get_client_uuid
get_client_secret

# --- Start backend in background ---
log "Starting backend app…"
python server.py &
APP_PID=$!

# Forward signals to child, and reap on exit
cleanup() {
  log "Shutting down (signal) …"
  kill "$APP_PID" 2>/dev/null || true
  wait "$APP_PID" 2>/dev/null || true
}
trap cleanup TERM INT EXIT

# --- Wait for /api/health/ready ---
HEALTH_URL="http://localhost:${AMS_PORT:-8000}/api/health/ready"
log "Waiting for backend health: ${HEALTH_URL}"
for i in {1..60}; do
  if curl -fsS "$HEALTH_URL" >/dev/null; then
    log "Backend is healthy."
    break
  fi
  sleep 1
done

# --- Keep the app in the foreground ---
wait "$APP_PID"
