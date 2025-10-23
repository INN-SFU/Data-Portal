# AMS Complete System - Docker Setup

## Quick Start (One Command!)

```bash
./start.sh
```

This will start **all AMS services**:
- ✅ Keycloak (authentication) + automatic configuration
- ✅ Backend API + smoke tests
- ✅ Frontend (React UI)

## Manual Start

```bash
# Create network (first time only)
docker network create ams-network

# Start all services
docker compose -f docker-compose.dev-all.yml up -d --build
```

## Access Services

Once started (takes ~60-90 seconds):

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | - |
| Backend API | http://localhost:8000/docs | - |
| Keycloak Admin | http://keycloak.local:8080/admin | admin/admin123 |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     ams-network (Docker)                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐                                            │
│  │   Frontend   │──┐                                         │
│  │    :3000     │  │                                         │
│  └──────────────┘  │                                         │
│                    ▼                                         │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │   Backend    │─▶│   Keycloak   │                         │
│  │   API:8000   │  │    :8080     │                         │
│  └──────────────┘  └──────────────┘                         │
│         ▲                                                    │
│         │                                                    │
│  ┌──────────────┐                                           │
│  │ Keycloak-Init│  (runs once, configures Keycloak)        │
│  └──────────────┘                                           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Key Features

### 🎯 Automated Keycloak Configuration
- `keycloak-init` container runs automatically
- Configures service account permissions
- Backend waits for init to complete before starting
- **No manual steps required!**

### 🧪 Automatic Smoke Tests
- Backend runs smoke tests on startup
- Tests Keycloak integration
- Tests user management APIs
- Tests policy management APIs
- Container stays running even if 1-2 tests fail

### 🔗 Proper Service Dependencies
- Services start in correct order
- Health checks ensure readiness
- Automatic retry logic

## Viewing Logs

```bash
# All services
docker compose -f docker-compose.dev-all.yml logs -f

# Specific service
docker compose -f docker-compose.dev-all.yml logs -f backend
docker compose -f docker-compose.dev-all.yml logs -f keycloak
```

## Stopping Services

```bash
# Stop all services
docker compose -f docker-compose.dev-all.yml down

# Stop and remove volumes
docker compose -f docker-compose.dev-all.yml down -v
```

## Troubleshooting

### Backend smoke tests failing?
- Check Keycloak logs: `docker compose -f docker-compose.dev-all.yml logs keycloak`
- Check init logs: `docker compose -f docker-compose.dev-all.yml logs keycloak-init`
- Verify keycloak-init completed successfully

### Services not starting?
```bash
# Check service status
docker compose -f docker-compose.dev-all.yml ps

# Check specific service health
docker inspect ams-backend --format='{{.State.Health.Status}}'
```

### Clean start?
```bash
# Stop everything
docker compose -f docker-compose.dev-all.yml down -v

# Remove all containers
docker ps -a --filter "name=ams" -q | xargs docker rm -f

# Start fresh
./start.sh
```

## For Deployment Engineers

This setup demonstrates:
- ✅ All services containerized
- ✅ Proper orchestration with dependencies
- ✅ Init containers for configuration
- ✅ Health checks and readiness probes
- ✅ Automated testing on startup
- ✅ Single command deployment

**Ready to port to Kubernetes/production environment!**

The orchestration patterns used here (init containers, health checks, depends_on with conditions) map directly to Kubernetes concepts.
