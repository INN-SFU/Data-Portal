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

```bash
# 1. Clone and setup Python environment
git clone <repository-url>
cd AMS
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Initialize configuration files
#    Option A: Automated setup (recommended)
python3 scripts/setup.py --all

#    Option B: Manual setup
#    cp config/config.template.yaml config.yaml
#    cp config/.env.template core/settings/.env
#    cp config/.secrets.template core/settings/security/.secrets

# 3. Start Keycloak service
docker compose -f deployment/docker-compose.yml up keycloak -d

# 4. Configure Keycloak (one-time setup)
#    a) Go to http://localhost:8080 (admin/admin123)
#    b) Add realm → Import config/keycloak-realm-export.json
#    c) Get client secret: Clients → ams-portal-admin → Credentials
#    d) Update config.yaml with the secret (see example below)

# 5. Start the application
#    Choose one:
#    Docker: docker compose -f deployment/docker-compose.yml up -d
#    Local:  python3 main.py config.yaml

# 6. Create your first admin user
python scripts/create_admin_user.py

# 7. Access the application
#    - Main app: http://localhost:8000
#    - API docs: http://localhost:8000/docs
```

**Example config.yaml update:**
```yaml
keycloak:
  admin_client_secret: $KEYCLOAK_ADMIN_CLIENT_SECRET|<paste-your-copied-secret-here>
```

**Local Development Setup:**
If running locally (not Docker), also install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
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
  admin_client_secret: $KEYCLOAK_ADMIN_CLIENT_SECRET|<paste-your-copied-secret-here>
```

**What gets configured automatically:**
- ✅ Realm: `ams-portal`
- ✅ UI Client: `ams-portal-ui` (public, for web interface)
- ✅ Admin Client: `ams-portal-admin` (confidential, for backend)
- ✅ Roles: `admin`, `user`, `data-manager`

## Initial User Setup

After Keycloak is configured, create your first admin user with the automated script:

```bash
# Run the admin user creation script
python scripts/create_admin_user.py

# The script will prompt you to enter:
# - Username (e.g., 'admin')
# - Email (e.g., 'admin@localhost')  
# - First/Last Name (e.g., 'Admin', 'User')
# - Password (e.g., 'admin123')
# - Password confirmation
```

The script will:
- ✅ Create the user in Keycloak
- ✅ Set a permanent password
- ✅ Assign admin role automatically
- ✅ Verify the setup worked

**Suggested Development Credentials:**
- Username: `admin`
- Password: `admin123`
- Email: `admin@localhost`

**Troubleshooting:**
- Ensure Keycloak is running at http://localhost:8080
- Check that the `ams-portal` realm exists
- Verify your `config.yaml` has correct Keycloak settings

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

### Testing

The project uses a comprehensive testing framework with unit tests, integration tests, and BDD (Behavior-Driven Development) tests.

**Setup:**
```bash
# Install test dependencies
pip install -r requirements-dev.txt
```

**Running Tests:**
```bash
# BDD tests (behavioral scenarios)
behave tests/features/

# BDD tests with verbose output
behave tests/features/ -v

# BDD tests with captured output (useful for debugging)
behave tests/features/ -s

# Run specific feature
behave tests/features/configuration.feature

# Unit tests (when available)
pytest tests/unit/

# Integration tests (when available)  
pytest tests/integration/

# Run all pytest tests
pytest tests/
```

**Test Structure:**
- `tests/unit/` - Fast unit tests for individual functions/classes
- `tests/integration/` - API and database integration tests
- `tests/features/` - BDD acceptance tests using Gherkin syntax

**Current Test Status:**
- Configuration tests are available and reveal type conversion issues in EnvYAML
- Tests use temporary config files for isolation
- Failing tests are expected and guide development fixes

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
├── scripts/               # Setup and utility scripts
└── tests/                 # Test suite
    ├── unit/              # Unit tests
    ├── integration/       # Integration tests
    └── features/          # BDD tests (Gherkin/behave)
```

## Troubleshooting

### Common Issues

1. **Keycloak Connection Failed**
   - Verify `KEYCLOAK_DOMAIN` is accessible
   - Check client configuration in Keycloak admin console

2. **Environment Variables Not Found**
   - Error: `TypeError: expected str, bytes or os.PathLike object, not NoneType`
   - Solution: Copy `.env.template` to `core/settings/.env`
   - Run: `cp config/.env.template core/settings/.env`

3. **Secrets Generation Failed**  
   - Ensure `core/settings/security/` directory exists
   - Run: `python scripts/setup.py --generate-secrets`

4. **Storage Endpoint Issues**
   - Verify endpoint configurations in `core/settings/managers/endpoints/configs/`
   - Check network connectivity to storage services

5. **Permission Denied**
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
