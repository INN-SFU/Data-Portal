# AMS Data Portal

**Policy-Derived Data Access Management Platform for Heterogeneous Storage Endpoints**

A FastAPI-based web application that provides policy-driven access control across multiple storage backends including S3, POSIX filesystems, and OpenStack Swift.

## Developed By

**Institute for Neuroscience and Neurotechnology (INN) & Research Computing Group (RCG)**
- Principal Architect: [pmahon@sfu.ca](mailto:pmahon@sfu.ca)
- Consultation: [jpeltier@sfu.ca](mailto:jpeltier@sfu.ca), [kshen@sfu.ca](mailto:kshen@sfu.ca)

For detailed information, see the [project wiki](https://github.com/INN-SFU/Data-Portal/wiki).

## Features

- **Multi-Storage Support**: S3, POSIX, OpenStack Swift
- **Policy-Based Access Control**: Casbin integration for fine-grained permissions
- **Keycloak Authentication**: Enterprise-grade OIDC/OAuth2 authentication
- **RESTful API**: FastAPI with automatic OpenAPI documentation
- **Web Interface**: HTML templates for user-friendly data management
- **Containerized Deployment**: Docker and Docker Compose support

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd AMS

# Set up configuration
python scripts/setup.py --all

# Start with Docker Compose
docker compose -f deployment/docker-compose.yml up -d
```

### Option 2: Local Development

```bash
# 1. Clone and setup Python environment
git clone <repository-url>
cd AMS
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Initialize configuration files
python3 scripts/setup.py --all

# 3. Start Keycloak service
docker compose -f deployment/docker-compose.yml up keycloak -d

# 4. Configure Keycloak (one-time setup)
#    a) Go to http://localhost:8080 (admin/admin123)
#    b) Add realm → Import config/keycloak-realm-export.json
#    c) Get client secret: Clients → ams-portal-admin → Credentials
#    d) Update config.yaml with the secret (see example below)

# 5. Start the application
python3 main.py config.yaml

# 6. Access the application
#    - Main app: http://localhost:8000
#    - API docs: http://localhost:8000/docs
```

**Example config.yaml update:**
```yaml
keycloak:
  admin_client_secret: "your-copied-secret-here"  # Replace this line only
```

## Detailed Setup

### Prerequisites

- Python 3.12+
- Docker & Docker Compose V2 (for containerized deployment)
- Keycloak server (included in Docker setup)

**Note:** If you have Docker Compose V1, use `docker-compose` (with hyphen) instead of `docker compose`.

### 1. Configuration Setup

The setup script automates initial configuration:

```bash
# Development setup
python scripts/setup.py --environment development

# Production setup  
python scripts/setup.py --environment production

# Generate new secrets only
python scripts/setup.py --generate-secrets

# Validate configuration
python scripts/setup.py --validate
```

### 2. Manual Configuration

If you prefer manual setup:

1. **Copy configuration templates:**
   ```bash
   cp config.template.yaml config.yaml
   cp .env.template core/settings/.env
   cp .secrets.template core/settings/security/.secrets
   ```

2. **Update `config.yaml`** with your Keycloak settings:
   ```yaml
   keycloak:
     domain: "https://your-keycloak-domain.com"
     realm: "your-realm"
     ui_client_id: "your-ui-client"
     admin_client_id: "your-admin-client"
     admin_client_secret: "your-admin-secret"
   ```

3. **Generate secrets:**
   ```bash
   python -c "from core.settings.security._generate_secrets import _generate_secrets; _generate_secrets()"
   ```

### 3. Keycloak Configuration

**Import Pre-configured Realm:**
1. Go to http://localhost:8080 (admin/admin123)
2. Click dropdown next to "Master" → "Add realm"
3. Click "Select file" → Choose `config/keycloak-realm-export.json`
4. Click "Create"

**Get Admin Client Secret:**
1. Go to Clients → `ams-portal-admin`
2. Click "Credentials" tab
3. Copy the Secret value

**Update config.yaml:**
```yaml
keycloak:
  admin_client_secret: "paste-your-copied-secret-here"
```

**What gets configured automatically:**
- ✅ Realm: `ams-portal`
- ✅ UI Client: `ams-portal-ui` (public, for web interface)
- ✅ Admin Client: `ams-portal-admin` (confidential, for backend)
- ✅ Roles: `admin`, `user`, `data-manager`

**Create Test Users:**
- Users → Add user → Set username, email, password
- Role Mappings tab → Assign `admin` or `user` role

### 4. Storage Endpoints

Configure storage endpoints in `core/settings/managers/endpoints/configs/`:
- S3 endpoints: Configure with bucket and credentials
- POSIX endpoints: Set local filesystem paths
- Swift endpoints: OpenStack Swift configuration

## Deployment

### Development
```bash
# Local development server
python main.py config.yaml

# With auto-reload
# Set uvicorn.reload: true in config.yaml
```

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

### Project Structure
```
AMS/
├── api/v0_1/              # FastAPI application
├── core/                  # Core business logic
│   ├── connectivity/      # Storage adapters
│   ├── management/        # Policy & user management
│   └── settings/          # Configuration management
├── config/                # Configuration templates
│   ├── config.template.yaml
│   ├── .env.template
│   └── .secrets.template
├── deployment/            # Docker and deployment files
│   ├── docker-compose.yml
│   └── docker-compose.prod.yml
├── loggers/               # Logging configuration
└── scripts/               # Setup and utility scripts
```

## Troubleshooting

### Common Issues

1. **Keycloak Connection Failed**
   - Verify `KEYCLOAK_DOMAIN` is accessible
   - Check client configuration in Keycloak admin console

2. **Secrets Generation Failed**  
   - Ensure `core/settings/security/` directory exists
   - Run: `python scripts/setup.py --generate-secrets`

3. **Storage Endpoint Issues**
   - Verify endpoint configurations in `core/settings/managers/endpoints/configs/`
   - Check network connectivity to storage services

4. **Permission Denied**
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
