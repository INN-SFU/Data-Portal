#!/usr/bin/env bash
# One-time Keycloak configuration script
# Run this after Keycloak starts to configure service account permissions and scopes
set -Eeuo pipefail
source /app/entrypoint_helpers.sh

log "=== Keycloak Configuration Script ==="

# --- Verify environment and wait for Keycloak ---
require_all_backend_envs
wait_for_realm

# --- Get admin access ---
fetch_admin_token
get_client_uuid

# --- Configure service account and scopes ---
log "Configuring service account roles and scopes..."
ensure_service_account_roles
ensure_scope_mappings_for_admin_client
ensure_roles_scope_exists
attach_roles_scope_to_admin_client

log "=== Keycloak configuration complete ==="
log "Backend can now connect using client ID: ${KEYCLOAK_ADMIN_CLIENT_ID}"
