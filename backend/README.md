# AMS Backend Service

The backend service is the core API server for the AMS Data Portal, providing authentication, storage management, and policy enforcement.

## Quick Start

### Option 1: Complete System (Recommended)

See [DOCKER_SETUP.md](./DOCKER_SETUP.md) for the simplified one-command deployment that starts all services together.

### Option 2: Backend Development Mode

Start just the backend service for local development:

```bash
# Create shared network (first time only)
docker network create ams-network

# Start Keycloak
docker compose -p ams-keycloak -f docker-compose.keycloak.yml up -d

# Configure Keycloak (ONE-TIME ONLY - after first Keycloak start)
docker exec ams-backend-dev bash /app/init_keycloak.sh

# Start Backend
docker compose -p ams-backend -f docker-compose.backend.yml up -d --build

# Restart backend to apply Keycloak config
docker restart ams-backend-dev
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  ams-network (Docker)                    │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐         ┌──────────────┐              │
│  │   Backend    │────────▶│   Keycloak   │              │
│  │   API:8000   │         │    :8080     │              │
│  └──────────────┘         └──────────────┘              │
│         │                                                │
│         ▼                                                │
│  ┌──────────────┐                                       │
│  │  S3 Storage  │                                       │
│  │   Backends   │                                       │
│  └──────────────┘                                       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Service Communication:**
- Backend API → Keycloak: `http://keycloak.local:8080` (authentication)
- Backend API → S3 Storage: Presigned URLs for secure file access

## Project Structure

```
backend/
├── api/v0_1/              # FastAPI application and endpoints
│   ├── endpoints/         # API route handlers
│   └── app.py             # FastAPI app initialization
├── core/                  # Core business logic
│   ├── connectivity/      # Storage agent implementations
│   │   ├── agents/        # S3 and storage agent abstractions
│   │   └── manager.py     # Storage connectivity manager
│   ├── management/        # Policy and instance management
│   │   ├── instances/     # Storage instance management
│   │   ├── policies/      # Casbin policy enforcement
│   │   └── users/         # User management via Keycloak
│   └── settings/          # Configuration and secrets
├── config/                # Configuration templates and realm exports
├── tests/                 # Test suite
├── docker-compose.*.yml   # Docker orchestration files
├── Dockerfile             # Backend container image
├── server.py              # Main application entry point
└── start.sh               # Quick start script
```

## Service URLs

- **Backend API**: http://localhost:8000/docs (Swagger UI)
- **Keycloak Admin**: http://keycloak.local:8080/admin (admin/admin123)

## Key Features

### Storage Agent Architecture
The backend uses an Abstract Factory pattern for storage backends:
- **S3 Agent**: AWS S3 and S3-compatible storage (presigned URLs)
- **Dummy Agent**: Testing and development mock storage

### Authentication & Authorization
- **Keycloak Integration**: OAuth2/OIDC authentication
- **JWT Bearer Tokens**: React-friendly token-based auth
- **Casbin RBAC**: Policy-based access control

### API Endpoints

All endpoints use the `/api` prefix:

**Authentication:**
- `GET /api/auth/validate` - Validate JWT token

**Asset Management:**
- `PUT /api/asset/upload` - Upload asset
- `PUT /api/asset/download` - Download asset
- `GET /api/asset/user-home-data` - Get user home data
- `GET /api/asset/user-assets-data` - Get user assets

**Administration (all require admin privileges):**
- `GET /api/users/` - List users
- `POST /api/users/` - Create user
- `DELETE /api/users/{username}` - Delete user
- `GET /api/policies/` - List policies
- `POST /api/policies/` - Add policy
- `DELETE /api/policies/` - Remove policy
- `GET /api/instances/` - List storage instances
- `POST /api/instances/` - Create storage instance
- `GET /api/instances/{uuid}` - Get instance details
- `DELETE /api/instances/{uuid}` - Delete storage instance

**Health & Monitoring:**
- `GET /api/health/` - Basic health check
- `GET /api/health/detailed` - Detailed health info
- `GET /api/health/ready` - Readiness probe
- `GET /api/health/live` - Liveness probe

## Configuration

### Environment Variables

Key environment variables in `docker-compose.backend.yml`:

| Variable | Description | Default |
|----------|-------------|---------|
| `KEYCLOAK_DOMAIN` | Keycloak server URL | `http://keycloak.local:8080` |
| `KEYCLOAK_REALM` | Keycloak realm name | `ams-portal` |
| `AMS_HOST` | Backend bind address | `0.0.0.0` |
| `AMS_PORT` | Backend port | `8000` |
| `RUN_SMOKE_TESTS` | Run tests on startup | `true` |

### Docker Networking

All services use the `ams-network` for service discovery:

- Services communicate using Docker DNS names
- No manual IP configuration needed
- Production-like isolation and security
- External access via `host-gateway` for Keycloak

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
