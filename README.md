# AMS Data Portal

**Policy-Driven Data Access Management Platform for Decentralized and Heterogeneous Storage Instances**

A modular platform that enables secure, policy-driven collaboration across institutional boundaries while preserving data sovereignty. Designed to support the full research lifecycle - from data collection and analysis to collaboration and external sharing - the system accommodates diverse organizational needs through flexible deployment models: institutions can participate in a shared governance instance for collaborative convenience, or self-host their own instance for complete control over authentication, authorization, and policy infrastructure.

Data never leaves the owner's storage infrastructure; the platform provides only the access control layer while data remains on owner-controlled systems. This separation of governance from storage enables multi-institutional research collaboration across heterogeneous storage backends, bridging diverse systems into a unified governance layer without requiring data migration or storage consolidation. Each data owner defines and enforces their own access policies through administrative tools, enabling controlled sharing and external system integration while maintaining compliance with institutional requirements for sensitive datasets. The architecture respects data sovereignty at both the deployment level (who operates the governance platform) and the data level (who controls access policies for their assets).

## Developed By

**Institute for Neuroscience and Neurotechnology (INN) & Research Computing Group (RCG)**
- Principal Architect: [pmahon@sfu.ca](mailto:pmahon@sfu.ca)
- Consultation: [jpeltier@sfu.ca](mailto:jpeltier@sfu.ca), [kshen@sfu.ca](mailto:kshen@sfu.ca)

For detailed information, see the [project wiki](https://github.com/INN-SFU/Data-Portal/wiki).

## Features

**Governance & Access Control:**
- **Policy-Based Authorization**: Fine-grained access control enabling data owners to define and enforce custom access policies for their assets, supporting delegation and role-based permissions
- **Heterogeneous Storage Support**: Unified access layer across diverse storage backends (S3-compatible, POSIX filesystems, object storage) without requiring data migration or centralization
- **Presigned URL Access**: Secure, time-limited direct access to files via JWT tokens (POSIX) and signed URLs (S3), enabling controlled external sharing while maintaining audit trails

**Authentication & Identity:**
- **Institutional Identity Integration**: Standards-based authentication (OIDC/OAuth2) allowing organizations to integrate with existing identity providers and authentication infrastructure
- **Flexible Deployment Models**: Support for both shared governance instances and self-hosted deployments with complete control over authentication and authorization infrastructure

**Storage Architecture:**
- **Microservices Design**: Modular architecture with specialized services (Backend API, Storage Issuer, Storage Gateway) enabling independent scaling and deployment flexibility
- **POSIX Storage Support**: Direct filesystem access through presigned JWT tokens with automatic credential management and secure token validation
- **S3-Compatible Storage**: Native support for AWS S3 and S3-compatible object storage with presigned URL generation

**Developer & Operations:**
- **RESTful API**: Well-documented API with automatic OpenAPI specification, enabling integration with institutional workflows and custom applications
- **Containerized Architecture**: Production-ready Docker deployment with service orchestration, health monitoring, and automated configuration
- **Rapid Development Workflow**: Comprehensive testing framework with fast feedback loops (<30s) for reliable development and CI/CD integration

## Quick Start

**🚀 FULLY AUTOMATED SETUP (Recommended for New Developers)**

```bash
# 1. Clone the repository
git clone <repository-url>
cd AMS

# 2. Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements-dev.txt

# 4. Run FULL automated setup (does everything!)
python backend/scripts/setup.py --full-setup

# 5. Start the application (Keycloak is already running!)
python main.py config.yaml

# 6. Login and start developing!
#    - Main app: http://localhost:8000
#    - Use the admin credentials printed by setup script
#    - Default: admin / admin123
```

**What `--full-setup` does automatically:**
- ✅ Creates all required directories
- ✅ Generates configuration files from templates  
- ✅ Generates cryptographic secrets
- ✅ Starts Keycloak service and waits for readiness
- ✅ **Imports Keycloak realm and extracts client secret**
- ✅ **Updates config.yaml with the actual client secret**
- ✅ **Imports realm with pre-configured admin user (admin/admin123)**
- ✅ Validates the entire setup
- ✅ Runs tests to ensure everything works

**✅ Fully Automated:** No manual Keycloak configuration needed! Just start the application and login.

## Admin User Access

The setup script automatically configures TWO different admin users:

### 1. App Admin User (for AMS Data Portal Application)
**Purpose:** Login to the AMS Data Portal application at http://localhost:8000  
**Realm:** `ams-portal`  
**Credentials:**
- Username: `admin`
- Password: `admin123`
- Roles: `admin`, `user`

**To Login to Application:**
1. Start the application: `python main.py config.yaml`
2. Open: http://localhost:8000
3. Login with the app admin credentials above

### 2. Keycloak Admin User (for Keycloak Management)
**Purpose:** Access Keycloak Admin Console for realm/user management  
**Realm:** `master`  
**Credentials:**
- Username: `admin`
- Password: `admin123`

**To Access Keycloak Admin Console:**
- URL: http://localhost:8080
- Login: admin / admin123

**Manual Setup (Legacy)**
```bash
# If you prefer step-by-step control:
python scripts/setup.py --create-dirs
python scripts/setup.py --generate-secrets  
python scripts/setup.py --start-keycloak
python scripts/setup.py --create-admin  # Shows instructions only
python scripts/setup.py --validate
```

**🎯 Development Credentials (Pre-configured by setup script):**

**App Admin (for application login at :8000):**
- Username: `admin`
- Password: `admin123`  
- Email: `admin@localhost`
- Roles: `admin`, `user`

**Keycloak Admin (for Keycloak console at :8080):**
- Username: `admin`
- Password: `admin123`

**💡 Virtual Environment Notes:**
- The repository does **not** include a virtual environment (this was cleaned up for repo size)
- You **must** create your own virtual environment as shown above
- Always activate your virtual environment before running scripts: `source .venv/bin/activate`
- To deactivate: `deactivate`

**Local Development Setup:**
If you're developing locally (not using Docker):
```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt
```

## Detailed Setup

### Prerequisites

- Python 3.12+
- Docker & Docker Compose V2 (for containerized deployment)
- Keycloak server (included in Docker setup)

**Note:** If you have Docker Compose V1, use `docker-compose` (with hyphen) instead of `docker compose`.

### 1. Automated Setup (Recommended)

The setup script provides full automation for new developers:

```bash
# Full automated setup (recommended)
python scripts/setup.py --full-setup

# Full setup for production environment
python scripts/setup.py --full-setup --environment production
```

**Individual setup commands (if needed):**
```bash
# Create required directories only
python scripts/setup.py --create-dirs

# Generate new secrets only
python scripts/setup.py --generate-secrets

# Start Keycloak service
python scripts/setup.py --start-keycloak

# Configure Keycloak realm and get client secret
python scripts/setup.py --configure-keycloak

# Verify app admin user (created during realm import)
python scripts/setup.py --create-admin

# Run validation tests
python scripts/setup.py --run-tests

# Validate configuration
python scripts/setup.py --validate
```

## Deployment

### Development (Local Python)
```bash
# Local development server (backend only)
python main.py config.yaml

# With auto-reload
# Set uvicorn.reload: true in config.yaml
```

### Development with Docker (Full Stack)

For complete system with POSIX storage support:

```bash
# Prerequisites: Create shared network for service discovery
docker network create ams-network

# 1. Start Keycloak (authentication service)
cd backend
docker compose -p ams-keycloak -f docker-compose.keycloak.yml up -d

# 2. Configure Keycloak (ONE-TIME ONLY - after first Keycloak start)
docker exec ams-backend-dev bash /app/init_keycloak.sh

# 3. Start Backend API
docker compose -p ams-backend -f docker-compose.backend.yml up -d --build

# 4. Start Storage Issuer (JWT token generation)
cd storage-issuer
docker compose -p ams-storage-issuer up -d --build

# 5. Start Storage Gateway (file streaming)
cd ../../storage-gateway
docker compose -p ams-storage-gateway up -d --build

# 6. Start Frontend (optional)
cd ../frontend
docker compose -p ams-frontend -f docker-compose.frontend.yml up -d

# Access points:
# - Backend API: http://backend.local:8000/docs
# - Keycloak: http://keycloak.local:8080
# - Frontend: http://frontend.local:3000
```

**Docker Network Architecture:**
- All services communicate via `ams-network` for service discovery
- Services use internal DNS names (e.g., `storage-issuer:8001`, `storage-gateway:9000`)
- No manual host file management needed
- Production-like architecture with proper service isolation

### Production with Docker
```bash
# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# With PostgreSQL and Nginx
docker-compose --profile production --profile nginx up -d
```

### Environment Variables

Key environment variables (can override config.yaml):

| Variable | Description | Default |
|----------|-------------|---------|
| `AMS_HOST` | Server bind address | `0.0.0.0` |
| `AMS_PORT` | Server port | `8000` |
| `KEYCLOAK_DOMAIN` | Keycloak server URL | `http://localhost:8080` |
| `KEYCLOAK_REALM` | Keycloak realm name | `ams-portal` |

## API Documentation

Once running, access the API documentation at:
- Interactive docs: http://localhost:8000/docs
- OpenAPI spec: http://localhost:8000/openapi.json

### API Endpoints

All service API endpoints use the `/api` prefix:

**Authentication:**
- `GET /api/auth/validate` - Validate JWT token

**Asset Management:**
- `PUT /api/asset/upload` - Upload asset
- `PUT /api/asset/download` - Download asset
- `GET /api/asset/user-home-data` - Get user home data
- `GET /api/asset/user-assets-data` - Get user assets data

**Administration:**
- `GET /api/admin/user/` - Get users
- `PUT /api/admin/user/` - Add user
- `DELETE /api/admin/user/` - Remove user
- `GET /api/admin/policies` - Get policies
- `PUT /api/admin/policy` - Add policy
- `DELETE /api/admin/policy` - Remove policy
- `POST/DELETE /api/admin/endpoints/` - Manage storage instances

**Health & Monitoring:**
- `GET /api/health/` - Basic health check
- `GET /api/health/detailed` - Detailed health information
- `GET /api/health/ready` - Readiness probe
- `GET /api/health/live` - Liveness probe

### React Frontend Integration

The API supports bearer token authentication for React frontends:

**Authentication Flow:**
1. React frontend authenticates with Keycloak
2. Keycloak returns JWT access token
3. React sends `Authorization: Bearer <token>` header
4. API validates JWT and extracts user info

**Example API Call:**
```javascript
// React frontend example
const response = await fetch('/api/admin/user/', {
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  }
});
```

**User Info Available:**
- `preferred_username` - Username
- `sub` - User UUID
- `email` - Email address
- `realm_access.roles` - User roles
- `exp`, `iat` - Token timing

The API automatically prioritizes Authorization headers over cookies, making it seamless for both React frontends and traditional web UI.

## Development

### Installing Development Dependencies
```bash
pip install -r requirements-dev.txt
```

### Code Quality Tools
```bash
# Format code
black .
isort .

# Lint code
flake8 .
mypy .

# Security scan
bandit -r .
safety check
```

### Testing

The project uses a **speed-first testing framework** designed for rapid development feedback and reliable CI.

**Quick Testing:**
```bash
# Fast development feedback (<30s)
./run-tests fast

# Authentication tests (unit + integration)
./run-tests auth  

# Integration tests with Docker services
./run-tests slow --setup

# Full CI suite
./run-tests all --ci
```

**Test Structure:**
```
backend/tests/
├── fast/                    # <30s, no external deps
│   ├── unit/               # Pure logic tests (mocked)
│   └── contract/           # API behavior tests (mocked services)
├── slow/                   # >30s, requires services
│   ├── integration/        # Real service integration
│   └── system/            # Full system tests
├── infra/                  # Test infrastructure
│   └── docker/            # Docker test services
└── legacy/                 # Existing tests (gradually migrating)
```

**Development Workflow:**
```bash
# Daily development
./run-tests fast           # Quick validation (20 tests, 30s)

# Before commits
./run-tests auth           # Auth-specific validation

# Before merge
./run-tests slow --setup   # Full integration testing
```

**Key Benefits:**
- **🚀 Fast Feedback**: 30-second development loop
- **🔧 Zero Setup**: Fast tests work immediately
- **🎯 Focused Testing**: Run specific test categories
- **📊 Clear Results**: Simple pass/fail with counts

### Project Structure
```
AMS/
├── backend/                  # Main backend service
│   ├── api/v0_1/            # FastAPI application
│   ├── core/                # Core business logic
│   │   ├── connectivity/    # Storage adapters (S3, POSIX, etc.)
│   │   ├── management/      # Policy & user management
│   │   └── settings/        # Configuration management
│   ├── storage-issuer/      # JWT token issuer for POSIX storage
│   ├── config/              # Configuration templates
│   ├── scripts/             # Setup and utility scripts
│   └── tests/               # Test suite
├── storage-gateway/         # File streaming service for POSIX storage
├── frontend/                # React frontend application
└── deployment/              # Docker and deployment files
```

## POSIX Storage Architecture

For POSIX filesystems, the system uses a microservices architecture with presigned URL support:

```
User → AMS Backend (auth + policy check)
         ↓
      Storage Issuer (generates JWT tokens)
         ↓
      User receives presigned URL
         ↓
      Storage Gateway (validates JWT + streams file)
```

**Key Components:**

1. **Backend API** (`backend/`) - Handles authentication, authorization, and coordinates storage access
2. **Storage Issuer** (`backend/storage-issuer/`) - Generates time-limited JWT tokens for file access
3. **Storage Gateway** (`storage-gateway/`) - Validates tokens and streams files from POSIX filesystem

**User Experience:**
- Users create POSIX storage instances by providing only the Gateway URL
- Backend automatically manages issuer credentials (no manual configuration needed)
- System generates presigned URLs for secure, direct file downloads
- Tokens are time-limited and single-use for enhanced security

For detailed information, see [backend/POSIX_IMPLEMENTATION_PLAN.md](backend/POSIX_IMPLEMENTATION_PLAN.md)

## Troubleshooting

### Common Issues

1. **Virtual Environment Issues**
   - Error: `ModuleNotFoundError: No module named 'xyz'`
   - Solution: Ensure virtual environment is activated: `source .venv/bin/activate`
   - Reinstall dependencies: `pip install -r requirements-dev.txt`
   - If still having issues, delete `.venv` and recreate: `rm -rf .venv && python3 -m venv .venv`

2. **Python Command Not Found**
   - Error: `command not found: python`
   - Solution: Use `python3` instead of `python` on most systems
   - Or ensure Python is properly installed and in your PATH

3. **Keycloak Connection Failed**
   - Verify `KEYCLOAK_DOMAIN` is accessible
   - Check client configuration in Keycloak admin console

4. **Environment Variables Not Found**
   - Error: `TypeError: expected str, bytes or os.PathLike object, not NoneType`
   - Solution: Copy `.env.template` to `core/settings/.env`
   - Run: `cp config/.env.template core/settings/.env`

5. **Secrets Generation Failed**  
   - Ensure `core/settings/security/` directory exists
   - Run: `python scripts/setup.py --generate-secrets`

6. **Storage Endpoint Issues**
   - Verify instance configurations in `core/settings/managers/instances/configs/`
   - Check network connectivity to storage services

7. **Permission Denied**
   - Review Casbin policies in `core/settings/managers/policies/casbin/`
   - Check user assignments and roles

### Logs

Application logs are available in:
- Development: `loggers/logs/`
- Docker: `docker-compose logs ams-portal`

## Security Considerations

- **Secrets Management**: All secrets are base64 encoded and stored separately
- **Authentication**: Keycloak integration with OIDC/OAuth2
- **Authorization**: Casbin RBAC policy enforcement  
- **HTTPS**: Configure reverse proxy with SSL certificates for production
- **Container Security**: Non-root user in Docker containers

## Contributing

1. Follow the development setup instructions
2. Create feature branches from `main`  
3. Run code quality checks before committing
4. Submit pull requests with clear descriptions

## License

Apache 2.0 License - see LICENSE file for details.
