#!/usr/bin/env bash
set -euo pipefail

REALM="${KEYCLOAK_REALM:-ams-portal}"
DOMAIN="${KEYCLOAK_DOMAIN:-http://keycloak:8080}"
CLIENT_ID="${KEYCLOAK_ADMIN_CLIENT_ID:-ams-portal-admin}"
SECRET="$(cat /run/secrets/kc_admin_client_secret 2>/dev/null || true)"

log() { echo "[$(date -Is)] $*"; }

pretty_json() {
  if command -v python3 >/dev/null; then
    python3 -m json.tool
  else
    cat
  fi
}

get_token() {
  log "Requesting client_credentials token for ${CLIENT_ID}…"
  curl -sS -o /tmp/tok.json -w '%{http_code}' \
    -X POST "$DOMAIN/realms/$REALM/protocol/openid-connect/token" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -d "grant_type=client_credentials" \
    -d "client_id=$CLIENT_ID" \
    -d "client_secret=$SECRET"
}

case "${1:-}" in
  token)
    status=$(get_token)
    echo; log "Token HTTP $status"
    TOKEN=$(python3 -c 'import json; print(json.load(open("/tmp/tok.json")).get("access_token",""))')
    if [ -n "$TOKEN" ]; then
      echo "TOKEN prefix: ${TOKEN:0:20}..."
      python3 - <<'PY' /tmp/tok.json
import json,sys
claims=json.load(open(sys.argv[1]))
print("iss:", claims.get("iss"))
print("azp:", claims.get("azp"))
PY
    else
      echo "ERROR: no token"
      head -c 200 /tmp/tok.json; echo
      exit 1
    fi
    ;;

  users)
    TOKEN=$(python3 -c 'import json; print(json.load(open("/tmp/tok.json")).get("access_token",""))' 2>/dev/null || true)
    [ -n "$TOKEN" ] || { log "ERROR: no token available, run 'token' first"; exit 1; }
    log "Calling /users API…"
    curl -sS -H "Authorization: Bearer $TOKEN" \
      "$DOMAIN/admin/realms/$REALM/users?max=3" | pretty_json
    ;;

  all|"")
    "$0" token
    echo
    "$0" users
    ;;

  *)
    echo "Usage: $0 [token|users|all]" >&2
    exit 1
    ;;
esac
