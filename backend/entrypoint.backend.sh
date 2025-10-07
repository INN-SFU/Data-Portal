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
python -Xfrozen_modules=off main.py &
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

# --- Run smoke tests (if enabled and pytest available) ---
RUN_SMOKE_TESTS="${RUN_SMOKE_TESTS:-true}"
if [ "$RUN_SMOKE_TESTS" = "true" ]; then
  log "Running backend smoke tests…"
  if python -c "import pytest" >/dev/null 2>&1; then
    export PYTHONPATH="/app:${PYTHONPATH:-}"
    # Run tests directly without capturing (avoids signal issues)
    python tests/run_smoke_tests.py
    TEST_RC=$?

    if [ $TEST_RC -ne 0 ]; then
      log "Smoke tests FAILED (exit $TEST_RC)."
      # Uncomment to fail the container on test failure:
      # exit $TEST_RC
    else
      log "All smoke tests passed."
    fi
  else
    log "WARN: pytest not installed or not importable; skipping tests."
  fi
else
  log "Skipping smoke tests (RUN_SMOKE_TESTS=${RUN_SMOKE_TESTS})."
fi

# --- Keep the app in the foreground ---
wait "$APP_PID"
