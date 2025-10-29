# AMS Backend - Quick Start

## Prerequisites

**1. Create shared Docker network:**
```bash
docker network create ams-network
```

**2. Add to `/etc/hosts`:**
```
127.0.0.1 keycloak.local
127.0.0.1 backend.local
127.0.0.1 frontend.local
```

## Architecture

The AMS system consists of multiple microservices:

```
┌─────────────────────────────────────────────────────────────┐
│                      ams-network (Docker)                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Backend    │───▶│   Storage    │───▶│   Storage    │  │
│  │   API:8000   │    │  Issuer:8001 │    │ Gateway:9000 │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                                                     │
│         ▼                                                     │
│  ┌──────────────┐                                            │
│  │  Keycloak    │                                            │
│  │    :8080     │                                            │
│  └──────────────┘                                            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Service Communication:**
- Backend API → Storage Issuer: `http://storage-issuer:8001` (JWT token generation)
- Backend API → Keycloak: `http://keycloak.local:8080` (authentication)
- Storage Gateway → Storage Issuer: `http://storage-issuer:8001/.well-known/jwks.json` (public key)
- Users → Storage Gateway: Direct file downloads via presigned URLs

## Startup (Complete System)

```bash
# 1. Start Keycloak (authentication service)
cd backend
docker compose -p ams-keycloak -f docker-compose.keycloak.yml up -d

# 2. Start Backend API
docker compose -p ams-backend -f docker-compose.backend.yml up -d --build

# 3. Configure Keycloak (ONE-TIME ONLY - after first Keycloak start)
docker exec ams-backend-dev bash /app/init_keycloak.sh

# 4. Restart backend to apply Keycloak config
docker restart ams-backend-dev

# 5. Start Storage Issuer (for POSIX storage JWT tokens)
cd storage-issuer
docker compose -p ams-storage-issuer up -d --build

# 6. Start Storage Gateway (for POSIX file streaming)
cd ../../storage-gateway
docker compose -p ams-storage-gateway up -d --build

# 7. Start Frontend (optional)
cd ../frontend
docker compose -p ams-frontend -f docker-compose.frontend.yml up -d
```

## Access

- **Keycloak**: http://keycloak.local:8080/admin (admin/admin123)
- **Backend API**: http://backend.local:8000/docs
- **Storage Issuer**: http://localhost:8001/docs (internal service)
- **Storage Gateway**: http://localhost:9000/docs (internal service)
- **Frontend**: http://frontend.local:3000

## Shutdown

```bash
docker compose -p ams-keycloak -f docker-compose.keycloak.yml down
docker compose -p ams-backend -f docker-compose.backend.yml down
docker compose -p ams-storage-issuer -f backend/storage-issuer/docker-compose.yml down
docker compose -p ams-storage-gateway -f storage-gateway/docker-compose.yml down
docker compose -p ams-frontend -f frontend/docker-compose.frontend.yml down
```

## Configuration

### Storage Issuer Integration

The backend automatically configures Storage Issuer credentials for POSIX storage instances:

- **Issuer URL**: Set via `STORAGE_ISSUER_URL` (default: `http://storage-issuer:8001`)
- **API Key**: Auto-generated and stored in `/run/secrets/storage_issuer_api_key`
- **User Experience**: Users only need to provide Gateway URL when creating POSIX instances

This simplifies POSIX storage instance creation - issuer credentials are backend-internal and not user-facing.

### Environment Variables

Key environment variables in `docker-compose.backend.yml`:

| Variable | Description | Default |
|----------|-------------|---------|
| `STORAGE_ISSUER_URL` | Storage Issuer service URL | `http://storage-issuer:8001` |
| `STORAGE_ISSUER_API_KEY_FILE` | Path to issuer API key | `/run/secrets/storage_issuer_api_key` |
| `KEYCLOAK_DOMAIN` | Keycloak server URL | `http://keycloak.local:8080` |

## Docker Networking

All services use the `ams-network` for service discovery:

- Services communicate using Docker DNS (service names resolve to container IPs)
- No manual `/etc/hosts` management needed for service-to-service communication
- Production-like architecture with proper service isolation
- External access via `host-gateway` for Keycloak

**Benefits:**
- Closer to production Kubernetes/network setup
- Simpler configuration (no hardcoded IPs)
- Better security (isolated network)

## Development

### Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific test suite
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v

# With coverage
python -m pytest tests/ --cov=. --cov-report=html
```

### Local Development (No Docker)

```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Start Keycloak in Docker (required)
docker compose -p ams-keycloak -f docker-compose.keycloak.yml up -d

# Run backend locally
cd backend
python server.py
```

### Code Quality

```bash
# Format code
black .
isort .

# Lint
flake8 .
mypy .

# Security scan
bandit -r .
```

## Stopping Services

```bash
# Stop backend
docker compose -p ams-backend -f docker-compose.backend.yml down

# Stop Keycloak
docker compose -p ams-keycloak -f docker-compose.keycloak.yml down

# Stop everything and remove volumes
docker compose -p ams-backend -f docker-compose.backend.yml down -v
docker compose -p ams-keycloak -f docker-compose.keycloak.yml down -v
```

## Troubleshooting

### Backend won't start
- Check Keycloak is running: `docker ps | grep keycloak`
- Check logs: `docker compose -p ams-backend logs backend`
- Verify network exists: `docker network ls | grep ams-network`

### Authentication failing
- Verify Keycloak configuration ran: `docker logs ams-backend-dev | grep "Keycloak"`
- Check client secret is configured
- Try restarting backend: `docker restart ams-backend-dev`

### Storage operations failing
- Check storage instance configuration in `/app/core/settings/managers/instances/configs/`
- Verify S3 credentials are valid
- Check Casbin policies for user permissions

## Additional Documentation

- **[Backend Initialization](./docs/INITIALIZATION.md)** - Startup sequence and service account setup
- **[Complete System Setup](./DOCKER_SETUP.md)** - One-command deployment guide
- **[Architecture Diagrams](../docs/diagrams/)** - Visual system documentation
- **[Main README](../README.md)** - Project overview and features
