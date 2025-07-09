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

**🚀 FULLY AUTOMATED SETUP (Recommended for New Developers)**

```bash
# 1. Clone the repository
git clone <repository-url>
cd AMS

# 2. Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Run FULL automated setup (does everything!)
python scripts/setup.py --full-setup

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
- ✅ Validates the entire setup
- ✅ Runs tests to ensure everything works
- ✅ **Provides clear instructions for creating admin user**

**⚠️ Note:** You still need to manually start the application with `python main.py config.yaml` and create the admin user through Keycloak.

## Creating the Admin User

After running the setup script, you need to manually create the admin user through Keycloak:

### Steps:
1. **Start the application**: `python main.py config.yaml`
2. **Go to Keycloak Admin Console**: http://localhost:8080
3. **Login with admin credentials**: admin / admin123
4. **Navigate to**: ams-portal realm > Users
5. **Click 'Add user'** and fill in:
   - Username: `admin`
   - Email: `admin@localhost`
   - First name: `Admin`
   - Last name: `User`
   - Email verified: `ON`
   - Enabled: `ON`
6. **Click 'Save'**
7. **Go to 'Credentials' tab** and set password:
   - Password: `admin123`
   - Password confirmation: `admin123`
   - Temporary: `OFF`
8. **Click 'Set password'**
9. **Go to 'Role mappings' tab** and assign admin role
10. **Now you can login** to the application at http://localhost:8000

### Why Manual Creation?
The admin user must be created manually because the application's user management system requires the app to be running to function properly. The setup script handles all the infrastructure (Keycloak, realm, client secrets) but user creation needs the full application stack.

**Manual Setup (Legacy)**
```bash
# If you prefer step-by-step control:
python scripts/setup.py --create-dirs
python scripts/setup.py --generate-secrets  
python scripts/setup.py --start-keycloak
python scripts/setup.py --create-admin  # Shows instructions only
python scripts/setup.py --validate
```

**🎯 Development Credentials (Create manually through Keycloak):**
- Username: `admin`
- Password: `admin123`  
- Email: `admin@localhost`

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

# Show admin user creation instructions
python scripts/setup.py --create-admin

# Run validation tests
python scripts/setup.py --run-tests

# Validate configuration
python scripts/setup.py --validate
```

### 2. Manual Configuration (Advanced Users)

**⚠️ Not recommended for new developers - use `--full-setup` instead**

If you need manual control:
```bash
# Copy templates and edit manually
cp config/config.template.yaml config.yaml
cp config/.env.template core/settings/.env
# Edit config.yaml as needed
```

## Storage Endpoints

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

1. **Virtual Environment Issues**
   - Error: `ModuleNotFoundError: No module named 'xyz'`
   - Solution: Ensure virtual environment is activated: `source .venv/bin/activate`
   - Reinstall dependencies: `pip install -r requirements.txt`
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
   - Verify endpoint configurations in `core/settings/managers/endpoints/configs/`
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
