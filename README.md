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
# Clone the repository
git clone <repository-url>
cd AMS

# Set up Python environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up configuration
python3 scripts/setup.py --all

# Start Keycloak (required for app startup)
docker compose -f deployment/docker-compose.yml up keycloak -d

# Configure Keycloak (first time only)
# 1. Wait for Keycloak to start (check: http://localhost:8080)
# 2. Login to admin console: admin/admin123
# 3. Import realm: config/keycloak-realm-export.json
# 4. Get admin client secret and update config.yaml

# Start the application
python3 main.py config.yaml
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

### 3. Keycloak Setup

#### Quick Setup (Recommended)

1. **Start Keycloak:**
   ```bash
   docker compose -f deployment/docker-compose.yml up keycloak -d
   ```

2. **Access Admin Console:**
   - URL: http://localhost:8080
   - Username: `admin`
   - Password: `admin123`

3. **Import Pre-configured Realm:**
   - Click the dropdown next to "Master" realm
   - Select "Add realm"
   - Click "Select file" and choose `config/keycloak-realm-export.json`
   - Click "Create"

4. **Get Admin Client Secret:**
   - Go to Clients → `ams-portal-admin`
   - Click "Credentials" tab
   - Copy the "Secret" value

5. **Update config.yaml:**
   ```yaml
   keycloak:
     domain: "http://localhost:8080"
     realm: "ams-portal"
     ui_client_id: "ams-portal-ui"
     ui_client_secret: ""  # Leave empty for public client
     admin_client_id: "ams-portal-admin"
     admin_client_secret: "paste-your-copied-secret-here"
     redirect_uri: "http://localhost:8000/auth/callback"
   ```

6. **Create Test Users (Optional):**
   - Go to Users → Add user
   - Set username, email, and password
   - Go to Role Mappings tab
   - Assign roles: `admin` or `user`

**Pre-configured Roles:**
- `admin` - Full administrative access
- `user` - Standard user access  
- `data-manager` - Data management capabilities

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
