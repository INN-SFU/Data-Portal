# External Access Control for Nomad Services

## Overview

External access (via Traefik) is controlled **per service** using the `NOMAD_EXTERNAL_ACCESS` variable. This allows different services to have different access requirements based on their specific needs, not just based on environment.

## Configuration

### Variable: `NOMAD_EXTERNAL_ACCESS`

**Values:**
- `"true"`: Always enable external access via Traefik
- `"false"`: Always disable external access (internal service discovery only)
- Not set (default): Uses environment-based defaults

### Default Behavior (when `NOMAD_EXTERNAL_ACCESS` is not set)

| Environment | Service Type | External Access |
|------------|--------------|-----------------|
| Review Apps | Any | ✅ Enabled (for testing) |
| Production/Staging/Dev | Frontend | ✅ Enabled (typically needed) |
| Production/Staging/Dev | Backend | ❌ Disabled (internal only) |

## Examples

### Example 1: Frontend Service (Always External)

```yaml
variables:
  SERVICE_NAME: "frontend"
  NOMAD_EXTERNAL_ACCESS: "true"  # Explicitly enable
```

**Result:**
- ✅ External access in all environments
- ✅ Hostname: `frontend-production.example.com`
- ✅ Traefik tags configured

### Example 2: Backend API (Review Only)

```yaml
variables:
  SERVICE_NAME: "api-gateway"
  # NOMAD_EXTERNAL_ACCESS not set - uses defaults
```

**Result:**
- ✅ External access in Review Apps (for testing)
- ❌ Internal only in Production/Staging/Development
- Review: `api-gateway-feature-branch.example.com`
- Production: Internal service discovery only

### Example 3: Internal Service (Never External)

```yaml
variables:
  SERVICE_NAME: "data-service"
  NOMAD_EXTERNAL_ACCESS: "false"  # Always internal
```

**Result:**
- ❌ No external access in any environment
- ✅ Internal service discovery only
- ✅ Simple tags: `["api"]`

### Example 4: Backend Service (Always External)

```yaml
variables:
  SERVICE_NAME: "public-api"
  NOMAD_EXTERNAL_ACCESS: "true"  # Always external
```

**Result:**
- ✅ External access in all environments
- ✅ Hostname: `public-api-production.example.com`
- ✅ Traefik tags configured

## Service Tags

### External Access Enabled

**Frontend:**
```json
[
  "frontend",
  "traefik.enable=true",
  "traefik.http.routers.service-env.rule=Host(`hostname.example.com`)",
  "traefik.http.routers.service-env.entrypoints=websecure",
  "traefik.http.routers.service-env.tls=true",
  "traefik.http.services.service-env.loadbalancer.server.port=80"
]
```

**Backend:**
```json
[
  "backend",
  "api",
  "traefik.enable=true",
  "traefik.http.routers.service-env.rule=Host(`hostname.example.com`) || PathPrefix(`/api/env`)",
  "traefik.http.routers.service-env.entrypoints=websecure",
  "traefik.http.routers.service-env.tls=true",
  "traefik.http.services.service-env.loadbalancer.server.port=${NOMAD_PORT_http}"
]
```

### External Access Disabled

```json
["api"]
```

## Decision Matrix

Use this matrix to determine the right configuration:

| Service Type | Review Apps | Production | Configuration |
|--------------|-------------|------------|---------------|
| Frontend/UI | ✅ External | ✅ External | `NOMAD_EXTERNAL_ACCESS: "true"` |
| Public API | ✅ External | ✅ External | `NOMAD_EXTERNAL_ACCESS: "true"` |
| Internal API (Review Only) | ✅ External | ❌ Internal | Not set (use defaults) |
| Internal Service | ❌ Internal | ❌ Internal | `NOMAD_EXTERNAL_ACCESS: "false"` |
| Database/Queue | ❌ Internal | ❌ Internal | `NOMAD_EXTERNAL_ACCESS: "false"` |

## Benefits

1. **Flexibility**: Each service can have different access requirements
2. **Security**: Internal services can be explicitly marked as internal-only
3. **Testing**: Review Apps can expose services that are normally internal
4. **Explicit Control**: No guessing - set `NOMAD_EXTERNAL_ACCESS` to be explicit

## Migration Guide

If you have existing services:

1. **Frontend services**: Set `NOMAD_EXTERNAL_ACCESS: "true"` (explicit)
2. **Backend services in Review Apps**: Leave unset (uses default: enabled in review)
3. **Internal services**: Set `NOMAD_EXTERNAL_ACCESS: "false"` (explicit)

## See Also

- [Routing Pattern](./ROUTING_PATTERN.md) - How routing works
- [Review Apps Accessibility](./REVIEW_APPS_ACCESSIBILITY.md) - Review Apps details

