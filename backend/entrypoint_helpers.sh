#!/usr/bin/env bash
set -Eeuo pipefail

# -------- helpers --------
now() { date +"%Y-%m-%dT%H:%M:%S%z"; }
log() { echo "$(now) $*"; }

require_env() {
  # usage: require_env VAR_NAME [example]
  local name="${1}"; local example="${2:-}"
  if [ -z "${!name:-}" ]; then
    if [ -n "$example" ]; then
      log "ERROR: missing env $name (e.g. $example)"; exit 1
    else
      log "ERROR: missing env $name"; exit 1
    fi
  fi
}

# -------- checks --------
require_all_backend_envs() {
  require_env KEYCLOAK_DOMAIN "http://keycloak:8080"
  require_env KEYCLOAK_REALM "ams-portal"
  require_env KEYCLOAK_ADMIN_CLIENT_ID "ams-portal-admin"
  require_env KEYCLOAK_ADMIN "admin"
  require_env KEYCLOAK_ADMIN_PASSWORD "admin123"
}

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
  log "Realm is ready."
  # expose for callers
  export KEYCLOAK_WELL_KNOWN_URL="$wk"
}

# -------- API calls (write responses to temp files) --------
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
    log "ERROR: admin token HTTP $status"; head -c 200 /tmp/admin.json; echo; exit 1
  fi
  ADMIN_TOKEN="$(python3 - <<'PY'
import json; print(json.load(open("/tmp/admin.json")).get("access_token",""))
PY
)"
  if [ -z "${ADMIN_TOKEN:-}" ]; then
    log "ERROR: empty admin token"; head -c 200 /tmp/admin.json; echo; exit 1
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
    log "ERROR: list clients HTTP $status"; head -c 200 /tmp/clients.json; echo; exit 1
  fi
  CLIENT_UUID="$(python3 - <<'PY'
import json; arr=json.load(open("/tmp/clients.json")); print(arr[0]["id"] if arr else "", end="")
PY
)"
  if [ -z "${CLIENT_UUID:-}" ]; then
    log "ERROR: client '${KEYCLOAK_ADMIN_CLIENT_ID}' not found"; head -c 200 /tmp/clients.json; echo; exit 1
  fi
  export CLIENT_UUID
  log "Client UUID: ${CLIENT_UUID}"
}

get_client_secret() {
  log "Fetching client secret…"
  local url="${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/clients/${CLIENT_UUID}/client-secret"
  local status
  status=$(curl -sS -o /tmp/secret.json -w '%{http_code}' \
    -H "Authorization: Bearer $ADMIN_TOKEN" "$url")
  if [ "$status" != "200" ]; then
    log "ERROR: get client-secret HTTP $status"; head -c 200 /tmp/secret.json; echo; exit 1
  fi
  KEYCLOAK_ADMIN_CLIENT_SECRET="$(python3 - <<'PY'
import json; print(json.load(open("/tmp/secret.json")).get("value",""))
PY
)"
  if [ -z "$KEYCLOAK_ADMIN_CLIENT_SECRET" ] || [ "$KEYCLOAK_ADMIN_CLIENT_SECRET" = "null" ]; then
    log "ERROR: empty client secret (is client confidential + service accounts enabled?)"
    head -c 200 /tmp/secret.json; echo; exit 1
  fi
  export KEYCLOAK_ADMIN_CLIENT_SECRET
  log "Fetched secret length: ${#KEYCLOAK_ADMIN_CLIENT_SECRET}"
}

derive_helper_urls() {
  export KEYCLOAK_LOGIN_URL="${KEYCLOAK_DOMAIN}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/auth?client_id=${KEYCLOAK_UI_CLIENT_ID}&redirect_uri=${KEYCLOAK_REDIRECT_URI}&response_type=code"
}
