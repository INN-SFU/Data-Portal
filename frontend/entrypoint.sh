#!/bin/sh
set -eu

API_GATEWAY="${API_GATEWAY:-}"
if [ -z "$API_GATEWAY" ]; then
  echo "ERROR: API_GATEWAY must be set (e.g., http://api-gateway.service.consul:8000)"
  exit 1
fi

SERVER_NAME="${SERVER_NAME:-_}"

# Render the template with only the vars we use
envsubst '${SERVER_NAME} ${API_GATEWAY}' \
  < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Run Nginx in foreground
exec nginx -g 'daemon off;'
