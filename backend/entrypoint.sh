#!/usr/bin/env bash
set -Eeuo pipefail

# shellcheck source=/app/entrypoint_helpers.sh
source /app/entrypoint_helpers.sh

require_all_backend_envs
wait_for_realm
fetch_admin_token
get_client_uuid
get_client_secret
derive_helper_urls

log "Starting application…"
exec python -Xfrozen_modules=off main.py
