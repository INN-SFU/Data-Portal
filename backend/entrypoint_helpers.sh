#!/usr/bin/env bash
set -Eeuo pipefail

# ---------- tiny logger ----------
now() { date -Is; }
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

# Placeholder for future storage credential setup if needed

ensure_service_account_roles() {
  require_env KEYCLOAK_ADMIN_CLIENT_ID
  require_env KEYCLOAK_REALM
  log "Ensuring service account roles for '${KEYCLOAK_ADMIN_CLIENT_ID}'…"

  # realm-management client id
  local rm_uuid svc_user_id status
  status=$(curl -sS -o /tmp/rm.json -w '%{http_code}' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/clients?clientId=realm-management")
  [ "$status" = "200" ] || { log "ERROR: lookup realm-management HTTP $status"; head -c 300 /tmp/rm.json; echo; exit 1; }
  rm_uuid="$(python3 - <<'PY'
import json; d=json.load(open("/tmp/rm.json")); print(d[0]["id"] if d else "", end="")
PY
)"
  [ -n "$rm_uuid" ] || { log "ERROR: missing realm-management UUID"; exit 1; }

  # service-account user
  status=$(curl -sS -o /tmp/svc.json -w '%{http_code}' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/clients/${CLIENT_UUID}/service-account-user")
  [ "$status" = "200" ] || { log "ERROR: service-account-user HTTP $status"; head -c 300 /tmp/svc.json; echo; exit 1; }
  svc_user_id="$(python3 - <<'PY'
import json; print(json.load(open("/tmp/svc.json"))["id"], end="")
PY
)"
  [ -n "$svc_user_id" ] || { log "ERROR: empty service account id"; exit 1; }

  # current assigned roles (client-side)
  status=$(curl -sS -o /tmp/mappings.json -w '%{http_code}' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/users/${svc_user_id}/role-mappings/clients/${rm_uuid}")
  [ "$status" = "200" ] || { log "ERROR: get mappings HTTP $status"; head -c 300 /tmp/mappings.json; echo; exit 1; }

  python3 - <<'PY'
import json,sys
roles = {r["name"] for r in json.load(open("/tmp/mappings.json"))}
want = {"realm-admin"}  # or granular set
open("/tmp/_have_roles","w").write("yes" if roles & want else "no")
PY

  if [ "$(cat /tmp/_have_roles)" = "yes" ]; then
    log "Service account roles already present."
    return
  fi

  # assign realm-admin (or build granular set instead)
  status=$(curl -sS -o /tmp/radmin.json -w '%{http_code}' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/clients/${rm_uuid}/roles/realm-admin")
  [ "$status" = "200" ] || { log "ERROR: get realm-admin role HTTP $status"; head -c 300 /tmp/radmin.json; echo; exit 1; }
  python3 - <<'PY'
import json; r=json.load(open("/tmp/radmin.json"))
open("/tmp/assign.json","w").write(json.dumps([{"id":r["id"],"name":r["name"]}]))
PY

  status=$(curl -sS -o /tmp/assign_out.json -w '%{http_code}' \
    -X POST -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
    -d @/tmp/assign.json \
    "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/users/${svc_user_id}/role-mappings/clients/${rm_uuid}")
  if [[ "$status" != "200" && "$status" != "204" ]]; then
    log "ERROR: assign roles HTTP $status"; head -c 300 /tmp/assign_out.json; echo; exit 1
  fi

  log "Service account roles ensured."
}

# include realm-management roles in the token by client scope-mapping (belt-and-suspenders)
ensure_scope_mappings_for_admin_client() {
  log "Ensuring scope-mappings (realm-management -> ${KEYCLOAK_ADMIN_CLIENT_ID})…"

  local status rm_uuid
  status=$(curl -sS -o /tmp/sc_rm.json -w '%{http_code}' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/clients?clientId=realm-management")
  [ "$status" = "200" ] || { log "ERROR: lookup realm-management HTTP $status"; head -c 300 /tmp/sc_rm.json; echo; exit 1; }
  rm_uuid="$(python3 - <<'PY'
import json; arr=json.load(open("/tmp/sc_rm.json")); print(arr[0]["id"] if arr else "", end="")
PY
)"

  status=$(curl -sS -o /tmp/sc_cur.json -w '%{http_code}' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/clients/${CLIENT_UUID}/scope-mappings/clients/${rm_uuid}")
  [ "$status" = "200" ] || { log "ERROR: get scope-mappings HTTP $status"; head -c 300 /tmp/sc_cur.json; echo; exit 1; }

  python3 - <<'PY'
import json
roles={r["name"] for r in json.load(open("/tmp/sc_cur.json"))}
want={"realm-admin"}
open("/tmp/_has_sc","w").write("yes" if roles & want else "no")
PY

  if [ "$(cat /tmp/_has_sc)" = "yes" ]; then
    log "Scope-mappings already present."
    return
  fi

  status=$(curl -sS -o /tmp/radmin2.json -w '%{http_code}' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/clients/${rm_uuid}/roles/realm-admin")
  [ "$status" = "200" ] || { log "ERROR: get realm-admin role HTTP $status"; head -c 300 /tmp/radmin2.json; echo; exit 1; }
  python3 - <<'PY'
import json; r=json.load(open("/tmp/radmin2.json"))
open("/tmp/sc_payload.json","w").write(json.dumps([{"id":r["id"],"name":r["name"]}]))
PY

  status=$(curl -sS -o /tmp/sc_apply.json -w '%{http_code}' \
    -X POST -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
    -d @/tmp/sc_payload.json \
    "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/clients/${CLIENT_UUID}/scope-mappings/clients/${rm_uuid}")
  if [[ "$status" != "200" && "$status" != "204" ]]; then
    log "ERROR: add scope-mappings HTTP $status"; head -c 300 /tmp/sc_apply.json; echo; exit 1
  fi
  log "Scope-mappings ensured."
}

# dev-friendly: guarantee roles appear in token
maybe_set_full_scope_allowed() {
  log "Setting fullScopeAllowed=true on ${KEYCLOAK_ADMIN_CLIENT_ID}…"
  local status
  status=$(curl -sS -o /tmp/client.json -w '%{http_code}' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/clients/${CLIENT_UUID}")
  [ "$status" = "200" ] || { log "ERROR: get client rep HTTP $status"; head -c 300 /tmp/client.json; echo; exit 1; }

  python3 - <<'PY'
import json
d=json.load(open("/tmp/client.json"))
d["fullScopeAllowed"]=True
open("/tmp/client_upd.json","w").write(json.dumps(d))
PY

  status=$(curl -sS -o /tmp/client_upd_out.json -w '%{http_code}' \
    -X PUT -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
    -d @/tmp/client_upd.json \
    "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/clients/${CLIENT_UUID}")
  if [[ "$status" != "200" && "$status" != "204" ]]; then
    log "ERROR: set fullScopeAllowed HTTP $status"; head -c 300 /tmp/client_upd_out.json; echo; exit 1
  fi
  log "fullScopeAllowed set."
}

# optional, non-fatal
ensure_roles_client_scope() {
  log "Ensuring 'roles' client scope is attached to ${KEYCLOAK_ADMIN_CLIENT_ID}…"

  local status scope_id

  status=$(curl -sS -o /tmp/scopes.json -w '%{http_code}' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/client-scopes")
  if [ "$status" != "200" ]; then
    log "WARN: list client-scopes HTTP $status; skipping"
    return
  fi

  scope_id=$(python3 - <<'PY'
import json
print(next((s["id"] for s in json.load(open("/tmp/scopes.json")) if s.get("name")=="roles"), ""), end="")
PY
)
  if [ -z "$scope_id" ]; then
    log "WARN: no 'roles' scope found; skipping"
    return
  fi

  status=$(curl -sS -o /tmp/defsc.json -w '%{http_code}' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/clients/${CLIENT_UUID}/default-client-scopes")
  if [ "$status" != "200" ]; then
    log "WARN: get default-client-scopes HTTP $status; skipping"
    return
  fi

  have=$(python3 - <<'PY'
import json
print("yes" if any(s.get("name")=="roles" for s in json.load(open("/tmp/defsc.json"))) else "no", end="")
PY
)
  if [ "$have" = "yes" ]; then
    log "'roles' scope already attached."
    return
  fi

  status=$(curl -sS -o /tmp/addscope.json -w '%{http_code}' \
    -X PUT -H "Authorization: Bearer $ADMIN_TOKEN" \
    "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/clients/${CLIENT_UUID}/default-client-scopes/${scope_id}")
  if [[ "$status" != "204" && "$status" != "201" ]]; then
    log "WARN: add 'roles' scope HTTP $status; continuing"
    return
  fi

  log "'roles' scope attached."
}


derive_helper_urls() {
  export KEYCLOAK_LOGIN_URL="${KEYCLOAK_DOMAIN}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/auth?client_id=${KEYCLOAK_UI_CLIENT_ID}&redirect_uri=${KEYCLOAK_REDIRECT_URI}&response_type=code"
}

# ---------- smoke test (arg-free) ----------
run_keycloak_smoke_tests() {
  log "Running Keycloak smoke tests…"
  if [ ! -x /app/tests/test_keycloak.sh ]; then
    log "WARN: tests/test_keycloak.sh not found or not executable, skipping."
    return
  fi
  set +e
  /app/tests/test_keycloak.sh
  local rc=$?
  set -e
  if [ $rc -ne 0 ]; then
    log "Smoke tests FAILED (exit $rc)."
    # exit 1  # uncomment to hard-fail container on auth breakage
  else
    log "Smoke tests passed."
  fi
}

ensure_roles_scope_exists() {
  log "Ensuring 'roles' client scope exists…"
  local status
  status=$(curl -sS -o /tmp/scopes.json -w '%{http_code}' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/client-scopes")
  [ "$status" = "200" ] || { log "ERROR: list client-scopes HTTP $status"; head -c 300 /tmp/scopes.json; echo; exit 1; }

  local have_id
  have_id=$(python3 - <<'PY'
import json; print(next((s["id"] for s in json.load(open("/tmp/scopes.json")) if s.get("name")=="roles"), ""), end="")
PY
)
  if [ -n "$have_id" ]; then
    log "'roles' scope already present: $have_id"
    return
  fi

  # Create minimal 'roles' scope with the two standard mappers
  cat >/tmp/roles_scope.json <<'JSON'
{
  "name": "roles",
  "description": "Standard roles scope (realm + client roles)",
  "protocol": "openid-connect",
  "attributes": {
    "include.in.token.scope": "true",
    "display.on.consent.screen": "false"
  },
  "protocolMappers": [
    {
      "name": "realm roles",
      "protocol": "openid-connect",
      "protocolMapper": "oidc-usermodel-realm-role-mapper",
      "consentRequired": false,
      "config": {
        "userinfo.token.claim": "true",
        "id.token.claim": "true",
        "access.token.claim": "true",
        "claim.name": "realm_access.roles",
        "jsonType.label": "String",
        "multivalued": "true"
      }
    },
    {
      "name": "client roles",
      "protocol": "openid-connect",
      "protocolMapper": "oidc-usermodel-client-role-mapper",
      "consentRequired": false,
      "config": {
        "userinfo.token.claim": "true",
        "id.token.claim": "true",
        "access.token.claim": "true",
        "claim.name": "resource_access.${client_id}.roles",
        "jsonType.label": "String",
        "multivalued": "true"
      }
    }
  ]
}
JSON

  status=$(curl -sS -o /tmp/roles_scope_out.json -w '%{http_code}' \
    -X POST -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
    -d @/tmp/roles_scope.json \
    "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/client-scopes")
  if [[ "$status" != "201" && "$status" != "204" ]]; then
    log "ERROR: create 'roles' client scope HTTP $status"; head -c 400 /tmp/roles_scope_out.json; echo; exit 1
  fi
  log "Created 'roles' client scope."
}

attach_roles_scope_to_admin_client() {
  log "Attaching 'roles' client scope to ${KEYCLOAK_ADMIN_CLIENT_ID}…"
  local status scope_id
  status=$(curl -sS -o /tmp/scopes2.json -w '%{http_code}' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/client-scopes")
  [ "$status" = "200" ] || { log "ERROR: list client-scopes HTTP $status"; head -c 300 /tmp/scopes2.json; echo; exit 1; }

  scope_id=$(python3 - <<'PY'
import json; print(next((s["id"] for s in json.load(open("/tmp/scopes2.json")) if s.get("name")=="roles"), ""), end="")
PY
)
  if [ -z "$scope_id" ]; then
    log "ERROR: 'roles' scope still missing; cannot attach"
    exit 1
  fi

  # Are defaults already attached?
  status=$(curl -sS -o /tmp/defsc.json -w '%{http_code}' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/clients/${CLIENT_UUID}/default-client-scopes")
  [ "$status" = "200" ] || { log "ERROR: get default-client-scopes HTTP $status"; head -c 300 /tmp/defsc.json; echo; exit 1; }

  have=$(python3 - <<'PY'
import json; print("yes" if any(s.get("name")=="roles" for s in json.load(open("/tmp/defsc.json"))) else "no", end="")
PY
)
  if [ "$have" = "yes" ]; then
    log "'roles' scope already attached to client."
    return
  fi

  status=$(curl -sS -o /tmp/add_def_scope.json -w '%{http_code}' \
    -X PUT -H "Authorization: Bearer $ADMIN_TOKEN" \
    "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/clients/${CLIENT_UUID}/default-client-scopes/${scope_id}")
  if [[ "$status" != "204" && "$status" != "201" ]]; then
    log "ERROR: attach 'roles' default scope HTTP $status"; head -c 300 /tmp/add_def_scope.json; echo; exit 1
  fi
  log "Attached 'roles' scope to client."
}

