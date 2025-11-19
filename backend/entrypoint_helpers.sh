#!/usr/bin/env bash
set -Eeuo pipefail

# ---------- tiny logger ----------
now() { date +"%Y-%m-%dT%H:%M:%S%z"; }
log() { echo "$(now) $*"; }

# ---------- env guards ----------
require_env() {
  local name="${1}"; local example="${2:-}"
  if [ -z "${!name:-}" ]; then
    if [ -n "$example" ]; then
      log "ERROR: missing env $name (e.g. $example)"; exit 1
    else
      log "ERROR: missing env $name"; exit 1
    fi
  fi
}

require_all_backend_envs() {
  require_env KEYCLOAK_DOMAIN "http://keycloak:8080"
  require_env KEYCLOAK_REALM "ams-portal"
  require_env KEYCLOAK_ADMIN_CLIENT_ID "ams-portal-admin"
  require_env KEYCLOAK_ADMIN "admin"
  require_env KEYCLOAK_ADMIN_PASSWORD "admin123"
}

# ---------- readiness ----------
wait_for_realm() {
  local wk="${KEYCLOAK_DOMAIN}/realms/${KEYCLOAK_REALM}/.well-known/openid-configuration"
  log "Waiting for Keycloak realm well-known: $wk"
  local ready=0
  for _ in {1..60}; do
    if curl -fsS --connect-timeout 3 --max-time 5 "$wk" >/dev/null; then
      ready=1; break
    fi
    sleep 2
  done
  if [ "$ready" -ne 1 ]; then
    log "ERROR: realm well-known never became available at $wk"
    exit 1
  fi
  export KEYCLOAK_WELL_KNOWN_URL="$wk"
  log "Realm is ready."
}

# ---------- admin API helpers ----------
fetch_admin_token() {
  log "Fetching admin access token via admin-cli…"
  local url="${KEYCLOAK_DOMAIN}/realms/master/protocol/openid-connect/token"
  local status
  status=$(curl -sS -o /tmp/admin.json -w '%{http_code}' -X POST \
    "$url" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=admin-cli" \
    -d "username=${KEYCLOAK_ADMIN}" \
    -d "password=${KEYCLOAK_ADMIN_PASSWORD}" \
    -d "grant_type=password")
  if [ "$status" != "200" ]; then
    log "ERROR: admin token HTTP $status"; head -c 300 /tmp/admin.json; echo; exit 1
  fi
  ADMIN_TOKEN="$(python3 - <<'PY'
import json; print(json.load(open("/tmp/admin.json")).get("access_token",""))
PY
)"
  if [ -z "${ADMIN_TOKEN:-}" ]; then
    log "ERROR: empty admin token"; head -c 300 /tmp/admin.json; echo; exit 1
  fi
  export ADMIN_TOKEN
  log "Admin token acquired."
}

get_client_uuid() {
  log "Resolving client UUID for '${KEYCLOAK_ADMIN_CLIENT_ID}'…"
  local url="${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/clients?clientId=${KEYCLOAK_ADMIN_CLIENT_ID}"
  local status
  status=$(curl -sS -o /tmp/clients.json -w '%{http_code}' \
    -H "Authorization: Bearer $ADMIN_TOKEN" "$url")
  if [ "$status" != "200" ]; then
    log "ERROR: list clients HTTP $status"; head -c 300 /tmp/clients.json; echo; exit 1
  fi
  CLIENT_UUID="$(python3 - <<'PY'
import json; arr=json.load(open("/tmp/clients.json")); print(arr[0]["id"] if arr else "", end="")
PY
)"
  if [ -z "${CLIENT_UUID:-}" ]; then
    log "ERROR: client '${KEYCLOAK_ADMIN_CLIENT_ID}' not found"; head -c 300 /tmp/clients.json; echo; exit 1
  fi
  export CLIENT_UUID
  log "CLIENT_UUID=${CLIENT_UUID}"
}

get_client_secret() {
  log "Fetching client secret…"
  local url="${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/clients/${CLIENT_UUID}/client-secret"
  local status
  status=$(curl -sS -o /tmp/secret.json -w '%{http_code}' \
    -H "Authorization: Bearer $ADMIN_TOKEN" "$url")
  if [ "$status" != "200" ]; then
    log "ERROR: get client-secret HTTP $status"; head -c 300 /tmp/secret.json; echo; exit 1
  fi
  KEYCLOAK_ADMIN_CLIENT_SECRET="$(python3 - <<'PY'
import json; print(json.load(open("/tmp/secret.json")).get("value",""))
PY
)"
  if [ -z "$KEYCLOAK_ADMIN_CLIENT_SECRET" ] || [ "$KEYCLOAK_ADMIN_CLIENT_SECRET" = "null" ]; then
    log "ERROR: empty client secret (is client confidential + service accounts enabled?)"
    head -c 300 /tmp/secret.json; echo; exit 1
  fi
  export KEYCLOAK_ADMIN_CLIENT_SECRET
  log "Fetched secret length: ${#KEYCLOAK_ADMIN_CLIENT_SECRET}"

  # surface it as a file for the app (Docker secret path)
  if [ -d /run/secrets ] && [ -w /run/secrets ]; then
    echo -n "$KEYCLOAK_ADMIN_CLIENT_SECRET" > /run/secrets/kc_admin_client_secret
    log "Wrote client secret to /run/secrets/kc_admin_client_secret"
  else
    log "WARN: /run/secrets not writable; skipping file write"
  fi
}

# Note: Keycloak initialization functions have been moved to local/keycloak/init_keycloak.sh
# This file only contains functions needed by the backend to connect to an already-configured Keycloak

