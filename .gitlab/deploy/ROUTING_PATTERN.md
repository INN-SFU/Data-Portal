# Routing Pattern for Nomad Services

## Overview

This document explains the routing pattern used for Nomad services in this project. The pattern distinguishes between:
- **Frontend services**: Always need external access via Traefik
- **Backend services in Review Apps**: Need external access via Traefik (for testing)
- **Backend services in production/staging/development**: Internal access only via service discovery

## Service Tag Patterns

### Backend Services in Production/Staging/Development

Backend services in non-review environments use **simple tags** for service discovery:

```hcl
service {
  name     = "${__SERVICE__}-${__ENVIRONMENT__}"
  provider = "nomad"
  port     = "http"
  tags     = ["api"]  # Simple tag for service discovery
}
```

**Characteristics:**
- ✅ No Traefik tags
- ✅ Accessed via Nomad service discovery
- ✅ Used internally by other services (e.g., API Gateway discovering data-service)
- ✅ Example: `api-gateway` discovers `data-service` via `nomadService` template
- ✅ Not accessible from external internet

### Backend Services in Review Apps

Backend services in Review Apps need **Traefik tags** for external access (testing):

```hcl
service {
  name     = "${__SERVICE__}-${__ENVIRONMENT__}"
  provider = "nomad"
  port     = "http"
  tags = [
    "backend",
    "api",
    "traefik.enable=true",
    "traefik.http.routers.${__SERVICE__}-${__ENVIRONMENT__}.rule=Host(`${__HOSTNAME__}`) || PathPrefix(`/api/${__ENVIRONMENT__}`)",
    "traefik.http.routers.${__SERVICE__}-${__ENVIRONMENT__}.entrypoints=websecure",
    "traefik.http.routers.${__SERVICE__}-${__ENVIRONMENT__}.tls=true",
    "traefik.http.services.${__SERVICE__}-${__ENVIRONMENT__}.loadbalancer.server.port=${NOMAD_PORT_http}"
  ]
}
```

**Characteristics:**
- ✅ Full Traefik configuration
- ✅ External access for testing purposes
- ✅ Hostname and path-based routing
- ✅ TLS/HTTPS enabled
- ✅ Accessible from external internet (for Review App testing)

**Example from api-gateway template:**
```hcl
template {
  data = <<EOF
  DATA_SERVICE_URL={{- range nomadService "data-service-${__ENVIRONMENT__}" }}http://{{ .Address }}:{{ .Port }}{{- end }}
  EOF
  destination = "local/data-service-url.env"
  env         = true
  change_mode = "restart"
}
```

### Frontend Services

Frontend services use **Traefik tags** for external routing:

```hcl
service {
  name     = "${__SERVICE__}-${__ENVIRONMENT__}"
  provider = "nomad"
  port     = "http"
  tags = [
    "frontend",
    "traefik.enable=true",
    "traefik.http.routers.${__SERVICE__}-${__ENVIRONMENT__}.rule=Host(`${__HOSTNAME__}`)",
    "traefik.http.routers.${__SERVICE__}-${__ENVIRONMENT__}.entrypoints=websecure",
    "traefik.http.routers.${__SERVICE__}-${__ENVIRONMENT__}.tls=true",
    "traefik.http.services.${__SERVICE__}-${__ENVIRONMENT__}.loadbalancer.server.port=80"
  ]
}
```

**Characteristics:**
- ✅ Full Traefik configuration
- ✅ Hostname-based routing
- ✅ TLS/HTTPS enabled
- ✅ External access via domain name

## Service Discovery Flow

```
┌─────────────┐
│   Client    │
│  (Browser)  │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────┐
│   Traefik   │  ← Discovers frontend via Traefik tags
│  (Ingress)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Frontend   │  ← Discovers api-gateway via Nomad service discovery
│  Service    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ API Gateway │  ← Discovers data-service via Nomad service discovery
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Data Service│
└─────────────┘
```

## Template Files

### Backend Services
- `.gitlab/deploy/nomad-templates/backend.template.nomad` - For backend/data services
- `.gitlab/deploy/nomad-templates/api-gateway.template.nomad` - For API gateway

### Frontend Services
- `.gitlab/deploy/nomad-templates/frontend.template.nomad` - For frontend services

## Environment Variables

### Backend Services
- `__HOSTNAME__` is **not required** (set to empty string)
- `NOMAD_ENVIRONMENT_URL` is **not set** (no external URL)

### Frontend Services
- `__HOSTNAME__` is **required** (e.g., `frontend-review-pr-123.example.com`)
- `NOMAD_ENVIRONMENT_URL` is **set** (e.g., `https://frontend-review-pr-123.example.com`)

## Hostname Generation

Hostnames are only generated for frontend services:

```bash
if [ "$SERVICE_NAME" = "frontend" ]; then
  if [ "$NOMAD_ENVIRONMENT" = "review" ]; then
    __HOSTNAME__="${SERVICE_NAME}-${CI_COMMIT_REF_SLUG}.${NOMAD_DOMAIN}"
  else
    __HOSTNAME__="${SERVICE_NAME}-${NOMAD_ENVIRONMENT}.${NOMAD_DOMAIN}"
  fi
else
  __HOSTNAME__=""  # Backend services don't need hostname
fi
```

## Examples

### Review App (Frontend)
- **Service Name**: `frontend-review-pr-123`
- **Hostname**: `frontend-feature-branch.example.com`
- **URL**: `https://frontend-feature-branch.example.com`
- **Tags**: Full Traefik tags
- **Access**: External (via Traefik)

### Review App (Backend)
- **Service Name**: `data-service-review-pr-123`
- **Hostname**: `data-service-feature-branch.example.com`
- **URL**: `https://data-service-feature-branch.example.com`
- **Tags**: Full Traefik tags
- **Access**: External (via Traefik) - **for testing purposes**

### Production (Frontend)
- **Service Name**: `frontend-production`
- **Hostname**: `frontend-production.example.com`
- **URL**: `https://frontend-production.example.com`
- **Tags**: Full Traefik tags
- **Access**: External (via Traefik)

### Production (Backend)
- **Service Name**: `data-service-production`
- **Hostname**: (not set)
- **URL**: (not set)
- **Tags**: `["api"]`
- **Access**: Internal only (via service discovery)

## References

- [Nomad Service Discovery](https://www.nomadproject.io/docs/service-discovery)
- [Traefik Service Discovery](https://doc.traefik.io/traefik/routing/providers/nomad/)
- [Nomad Service Templates](https://www.nomadproject.io/docs/job-specification/template)

