#!/usr/bin/env bash
# One-time Keycloak configuration script
# Run this after Keycloak starts to configure service account permissions and scopes
set -Eeuo pipefail

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
BACKEND_DIR="$PROJECT_ROOT/backend"

# Source helper functions
source "$SCRIPT_DIR/entrypoint_helpers.sh"

# Load backend environment variables
if [ -f "$BACKEND_DIR/.env.development" ]; then
    set -a
    source "$BACKEND_DIR/.env.development"
    set +a
    log "Loaded backend/.env.development"
else
    log "ERROR: backend/.env.development not found"
    exit 1
fi

log "=== Keycloak Configuration Script ==="

# Override KEYCLOAK_DOMAIN for local access (outside Docker network)
export KEYCLOAK_DOMAIN="http://localhost:8080"

# --- Verify environment and wait for Keycloak ---
require_all_backend_envs
wait_for_realm

# --- Get admin access ---
fetch_admin_token
get_client_uuid
fetch_and_save_client_secret

# --- Configure service account and scopes ---
log "Configuring service account roles and scopes..."
ensure_service_account_roles
ensure_scope_mappings_for_admin_client
ensure_roles_scope_exists
attach_roles_scope_to_admin_client

log "=== Keycloak configuration complete ==="
log "Backend can now connect using client ID: ${KEYCLOAK_ADMIN_CLIENT_ID}"
