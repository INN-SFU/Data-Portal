#!/usr/bin/env bash
set -Eeuo pipefail
source /app/entrypoint_helpers.sh

# --- Keycloak prep ---
require_all_backend_envs
wait_for_realm
fetch_admin_token
get_client_uuid
get_client_secret
derive_helper_urls
ensure_service_account_roles
ensure_scope_mappings_for_admin_client
ensure_roles_scope_exists
attach_roles_scope_to_admin_client

# --- start backend in background ---
log "Starting backend app…"
python -Xfrozen_modules=off main.py &
APP_PID=$!

# forward signals to child, and reap on exit
cleanup() {
  log "Shutting down (signal) …"
  kill "$APP_PID" 2>/dev/null || true
  wait "$APP_PID" 2>/dev/null || true
}
trap cleanup TERM INT EXIT

# --- wait for /api/health/ready ---
HEALTH_URL="http://localhost:${AMS_PORT:-8000}/api/health/ready"
log "Waiting for backend health: ${HEALTH_URL}"
for i in {1..60}; do
  if curl -fsS "$HEALTH_URL" >/dev/null; then
    log "Backend is healthy."
    break
  fi
  sleep 1
done

# --- run auth smoke tests (if pytest available) ---
log "Running backend auth smoke tests…"
if python -c "import pytest" >/dev/null 2>&1; then
  export PYTHONPATH="/app:${PYTHONPATH:-}"
  python -m pytest -q tests/test_auth_smoke.py
  TEST_RC=$?
  if [ $TEST_RC -ne 0 ]; then
    log "Auth smoke tests FAILED (exit $TEST_RC)."
    # Uncomment to fail the container on test failure:
    # exit $TEST_RC
  else
    log "Auth smoke tests passed."
  fi
else
  log "WARN: pytest not installed or not importable; skipping tests."
fi

# --- keep the app in the foreground ---
wait "$APP_PID"
