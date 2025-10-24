# AMS Data Portal

**Policy-Driven Data Access Management Platform for Heterogeneous Storage Instances**

A FastAPI-based web application providing policy-driven access control across multiple storage backends with enterprise authentication and fine-grained authorization.

## Developed By

**Institute for Neuroscience and Neurotechnology (INN) & Research Computing Group (RCG)**
- Consultation: [jpeltier@sfu.ca](mailto:jpeltier@sfu.ca), [kshen@sfu.ca](mailto:kshen@sfu.ca)
- Deployment Engineer: [aensan@sfu.ca](mailto:aensan@sfu.ca)
- Principal Architect: [pmahon@sfu.ca](mailto:pmahon@sfu.ca)

For detailed information, see the [project wiki](https://github.com/INN-SFU/Data-Portal/wiki).

## Documentation

📐 **[Architecture Diagrams](./docs/diagrams/)** - Visual system documentation
- [Component Architecture](./docs/diagrams/component-architecture.md) - System structure and relationships
- [Authentication Sequences](./docs/diagrams/sequence-authentication.md) - Login, token validation, admin operations
- [Storage Access Sequences](./docs/diagrams/sequence-storage-access.md) - File operations and access control

## Features

- **S3-Compatible Storage**: Presigned URL support for secure, time-limited file access
- **Policy-Based Access Control**: Casbin RBAC for fine-grained permissions
- **Keycloak Authentication**: Enterprise-grade OIDC/OAuth2 authentication
- **RESTful API**: FastAPI with automatic OpenAPI documentation
- **Bearer Token Support**: React-ready JWT authentication
- **Containerized Deployment**: Docker Compose orchestration with automatic setup
- **Service Discovery**: Docker networking for seamless inter-service communication
- **Health Checks**: Readiness and liveness probes for all services
- **Automated Testing**: Speed-first testing framework with <30s feedback loop

## Quick Start

**Prerequisites:**
- Docker & Docker Compose V2
- Git

**One-command start:**

```bash
# Clone repository
git clone <repository-url>
cd AMS/backend

# Start all services
./start.sh
```

This starts the complete system (Backend, Keycloak, Frontend) with automatic configuration.

**Access:**
- **Backend API:** http://localhost:8000/docs
- **Frontend:** http://localhost:3000
- **Keycloak Admin:** http://keycloak.local:8080/admin

**Default Credentials:**
- Username: `admin`
- Password: `admin123`

**What's Running:**
- ✅ Automated Keycloak realm import and configuration
- ✅ Backend API with automatic smoke tests
- ✅ Frontend web application
- ✅ Service health checks and dependencies
- ✅ Docker network with service discovery

**Next Steps:**
- See [backend/DOCKER_SETUP.md](backend/DOCKER_SETUP.md) for detailed deployment options
- See [backend/README.md](backend/README.md) for backend development guide

## Architecture

### System Components

```
┌─────────────────────────────────────────────────┐
│         AMS Data Portal Architecture             │
├─────────────────────────────────────────────────┤
│                                                   │
│  ┌──────────┐      ┌──────────┐      ┌────────┐│
│  │ Frontend │─────▶│ Backend  │─────▶│Keycloak││
│  │  :3000   │      │  API     │      │ :8080  ││
│  └──────────┘      │  :8000   │      └────────┘│
│                    └─────┬────┘                 │
│                          │                      │
│                          ▼                      │
│                    ┌──────────┐                │
│                    │ S3 Store │                │
│                    │ (presign)│                │
│                    └──────────┘                │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Flow:**
1. User authenticates via Keycloak (OAuth2/OIDC)
2. Backend validates JWT tokens and enforces Casbin policies
3. Storage agents generate presigned URLs for authorized access
4. Users download files directly from S3 via time-limited URLs

### Project Structure

```
AMS/
├── backend/             # Main backend service
│   ├── api/v0_1/       # FastAPI application
│   ├── core/           # Business logic
│   │   ├── connectivity/   # Storage agents
│   │   ├── management/     # Policies & users
│   │   └── settings/       # Configuration
│   ├── config/         # Templates and realm exports
│   ├── tests/          # Test suite
│   ├── server.py       # Entry point
│   └── start.sh        # Docker startup script
├── frontend/           # React application
├── deployment/         # Production configs
└── docs/              # Documentation
    └── diagrams/      # Architecture diagrams
```

## API Reference

### Endpoints

All endpoints use the `/api` prefix.

**Authentication:**
- `GET /api/auth/validate` - Validate JWT token

**Asset Management:**
- `PUT /api/asset/upload` - Upload file
- `PUT /api/asset/download` - Download file
- `GET /api/asset/user-home-data` - User home directory
- `GET /api/asset/user-assets-data` - User assets list

**Administration:**
- `GET /api/admin/user/` - List users
- `PUT /api/admin/user/` - Create user
- `DELETE /api/admin/user/` - Delete user
- `GET /api/admin/policies` - List policies
- `PUT /api/admin/policy` - Add policy
- `DELETE /api/admin/policy` - Remove policy
- `POST /api/admin/endpoints/` - Create storage instance
- `DELETE /api/admin/endpoints/` - Delete storage instance

**Health Monitoring:**
- `GET /api/health/` - Basic health
- `GET /api/health/detailed` - Detailed status
- `GET /api/health/ready` - Readiness probe
- `GET /api/health/live` - Liveness probe

### Authentication Flow

**React Frontend Integration:**

```javascript
// 1. Authenticate with Keycloak
const token = await keycloak.getToken();

// 2. Call API with Bearer token
const response = await fetch('/api/admin/user/', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
```

**Token Claims Available:**
- `preferred_username` - Username
- `sub` - User UUID
- `email` - Email address
- `realm_access.roles` - User roles
- `exp`, `iat` - Token expiration

## Development

### Running Tests

```bash
# Fast unit tests (<30s)
cd backend
python -m pytest tests/unit/ -v

# Integration tests (requires Docker services)
python -m pytest tests/integration/ -v

# All tests with coverage
python -m pytest tests/ --cov=. --cov-report=html
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
bandit -r backend/
```

### Environment Variables

Key configuration variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `AMS_HOST` | Backend bind address | `0.0.0.0` |
| `AMS_PORT` | Backend port | `8000` |
| `KEYCLOAK_DOMAIN` | Keycloak URL | `http://localhost:8080` |
| `KEYCLOAK_REALM` | Realm name | `ams-portal` |

## Deployment

### Docker Compose (Development)

```bash
# Start all services
cd backend
docker compose -f docker-compose.dev-all.yml up -d

# View logs
docker compose -f docker-compose.dev-all.yml logs -f

# Stop services
docker compose -f docker-compose.dev-all.yml down
```

### Production

See `deployment/` directory for production configurations:
- `docker-compose.yml` - Production orchestration
- `docker-compose.prod.yml` - Production overrides

**Production checklist:**
- [ ] Configure HTTPS/SSL certificates
- [ ] Set secure passwords (not default `admin123`)
- [ ] Configure external PostgreSQL for Keycloak
- [ ] Set up log aggregation
- [ ] Configure backup strategy for policies and user data
- [ ] Enable container security scanning

## Troubleshooting

### Common Issues

**Backend won't start**
```bash
# Check Keycloak is running
docker ps | grep keycloak

# View backend logs
docker logs ams-backend

# Verify network exists
docker network ls | grep ams-network
```

**Authentication failing**
```bash
# Check Keycloak initialization
docker logs ams-backend | grep "Keycloak configured"

# Restart backend
docker restart ams-backend
```

**Storage access denied**
- Verify user has appropriate Casbin policies
- Check storage instance configuration
- Confirm S3 credentials are valid

**Docker issues**
```bash
# Clean restart
docker compose -f backend/docker-compose.dev-all.yml down -v
docker network create ams-network
cd backend && ./start.sh
```

### Logs

- **Docker**: `docker compose -f backend/docker-compose.dev-all.yml logs -f`
- **Local**: `backend/logs/`

## Security

- **Secrets Management**: Base64-encoded secrets stored separately
- **Authentication**: OAuth2/OIDC via Keycloak
- **Authorization**: RBAC with Casbin policy engine
- **Presigned URLs**: Time-limited, signature-validated storage access
- **Container Security**: Non-root users, minimal base images
- **Network Isolation**: Docker networking for service isolation

## Contributing

1. Create feature branch from `main`
2. Follow code quality guidelines (Black, isort, Flake8)
3. Write tests for new features
4. Ensure all tests pass
5. Submit pull request with clear description

## License

Apache 2.0 License - see [LICENSE](LICENSE) file for details.
