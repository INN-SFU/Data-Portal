# AMS Data Portal - Developer Guide

This guide provides detailed information for developers working on the AMS Data Portal.

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Architecture](#project-architecture)
3. [Configuration System](#configuration-system)
4. [Authentication & Authorization](#authentication--authorization)
5. [Storage Adapters](#storage-adapters)
6. [API Development](#api-development)
7. [Testing](#testing)
8. [Deployment](#deployment)
9. [Troubleshooting](#troubleshooting)

## Development Environment Setup

### Prerequisites

- Python 3.12+
- Git
- Docker & Docker Compose (optional but recommended)
- IDE with Python support (VS Code, PyCharm, etc.)

### Quick Setup

```bash
# Clone and navigate to project
git clone <repository-url>
cd AMS

# Set up Python virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Initialize configuration
python scripts/setup.py --environment development

# Start development server
python main.py config.yaml
```

### IDE Configuration

#### VS Code
Create `.vscode/settings.json`:
```json
{
    "python.pythonPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"]
}
```

## Project Architecture

### Directory Structure

```
AMS/
├── api/v0_1/                    # FastAPI application layer
│   ├── endpoints/               # API endpoints
│   │   ├── interface/           # Web interface endpoints
│   │   ├── service/             # REST API endpoints
│   │   └── dependencies/        # Dependency injection
│   ├── static/                  # Static web assets
│   └── templates/               # Jinja2 templates
├── core/                        # Core business logic
│   ├── connectivity/            # Storage adapter framework
│   │   └── agents/              # Storage-specific implementations
│   ├── management/              # Domain management
│   │   ├── endpoints/           # Endpoint management
│   │   ├── policies/            # Policy management
│   │   └── users/               # User management
│   └── settings/                # Configuration management
├── loggers/                     # Logging configuration
├── scripts/                     # Utility scripts
└── main.py                      # Application entry point
```

### Key Design Patterns

#### 1. Factory Pattern
Storage agents are created using the factory pattern:
```python
# core/connectivity/agents/agent_factory.py
class AgentFactory:
    @staticmethod
    def create_agent(agent_type: str, config: dict):
        if agent_type == "s3":
            return S3Agent(config)
        elif agent_type == "posix":
            return PosixAgent(config)
        # ...
```

#### 2. Abstract Base Classes
All storage agents inherit from `AbstractStorageAgent`:
```python
# core/connectivity/abstract_storage_agent.py
class AbstractStorageAgent(ABC):
    @abstractmethod
    def upload(self, local_path: str, remote_path: str) -> bool:
        pass
    
    @abstractmethod
    def download(self, remote_path: str, local_path: str) -> bool:
        pass
```

#### 3. Dependency Injection
FastAPI dependency injection for managers:
```python
# api/v0_1/endpoints/dependencies/managers.py
def get_user_manager() -> AbstractUserManager:
    return KeycloakUserManager()
```

## Configuration System

### Configuration Hierarchy

1. **config.yaml** - Main configuration file
2. **Environment Variables** - Override config.yaml values  
3. **.env** - Path configurations
4. **.secrets** - Cryptographic secrets

### Environment Variable Override Pattern

```python
# Example: KEYCLOAK_DOMAIN overrides config['keycloak']['domain']
domain = os.getenv('KEYCLOAK_DOMAIN', config['keycloak']['domain'])
```

### Adding New Configuration

1. Add to `config.template.yaml`
2. Add environment variable support in `main.py`
3. Update documentation

## Authentication & Authorization

### Keycloak Integration

The system uses Keycloak for authentication with two client types:

1. **UI Client** (Public) - For web interface authentication
2. **Admin Client** (Confidential) - For administrative operations

```python
# Example authentication check
from api.v0_1.endpoints.service.auth import verify_token

@app.get("/protected")
async def protected_endpoint(token: str = Depends(verify_token)):
    return {"user": token.user_id}
```

### Casbin Policy Engine

Authorization uses Casbin RBAC model:

```
# Model: core/settings/managers/policies/casbin/model.conf
[request_definition]
r = sub, obj, act

[policy_definition]  
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
```

## Storage Adapters

### Creating a New Storage Adapter

1. **Inherit from AbstractStorageAgent**:
```python
from core.connectivity.abstract_storage_agent import AbstractStorageAgent

class MyStorageAgent(AbstractStorageAgent):
    def __init__(self, config: dict):
        self.config = config
    
    def upload(self, local_path: str, remote_path: str) -> bool:
        # Implementation
        pass
```

2. **Register in AgentFactory**:
```python
# core/connectivity/agents/agent_factory.py
if agent_type == "mystorage":
    return MyStorageAgent(config)
```

3. **Add configuration template**:
```json
{
    "agent_type": "mystorage",
    "connection_params": {
        "endpoint": "https://my-storage.com",
        "credentials": {...}
    }
}
```

### Existing Storage Adapters

- **S3Agent**: AWS S3 and S3-compatible storage
- **PosixAgent**: Local and network filesystems
- **SwiftAgent**: OpenStack Swift object storage

## API Development

### Adding New Endpoints

1. **Create endpoint file**:
```python
# api/v0_1/endpoints/service/my_endpoint.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/my-endpoint", tags=["My Endpoint"])

@router.get("/")
async def get_items():
    return {"items": []}
```

2. **Register router**:
```python
# api/v0_1/endpoints/__init__.py
from .service.my_endpoint import router as my_endpoint_router

application_router.include_router(my_endpoint_router)
```

### API Conventions

- Use proper HTTP status codes
- Include comprehensive error handling
- Add input validation with Pydantic models
- Include OpenAPI documentation strings

```python
@router.post("/", status_code=201, response_model=ItemResponse)
async def create_item(item: ItemCreate):
    """
    Create a new item.
    
    - **name**: Item name (required)
    - **description**: Item description (optional)
    """
    try:
        # Implementation
        return created_item
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

## Testing

### Test Structure

```
tests/
├── unit/                   # Unit tests
│   ├── test_agents.py      # Storage agent tests
│   ├── test_managers.py    # Manager tests
│   └── test_endpoints.py   # Endpoint tests
├── integration/            # Integration tests
└── fixtures/               # Test fixtures
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/test_agents.py

# Run with verbose output
pytest -v
```

### Writing Tests

```python
import pytest
from core.connectivity.agents.s3_agent import S3Agent

@pytest.fixture
def s3_config():
    return {
        "endpoint": "http://localhost:9000",
        "access_key": "minioadmin",
        "secret_key": "minioadmin"
    }

def test_s3_agent_upload(s3_config):
    agent = S3Agent(s3_config)
    result = agent.upload("/local/file.txt", "bucket/remote/file.txt")
    assert result is True
```

## Deployment

### Docker Development

```bash
# Build development image
docker build -t ams-portal:dev .

# Start with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f ams-portal
```

### Production Deployment

```bash
# Production build with multi-stage Dockerfile
docker build -t ams-portal:prod -f Dockerfile.prod .

# Deploy with production compose
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Environment-Specific Configuration

- **Development**: Auto-reload enabled, debug logging
- **Staging**: Production-like with debug access
- **Production**: Optimized builds, restricted access

## Troubleshooting

### Common Development Issues

#### 1. Import Errors
```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH=/path/to/AMS:$PYTHONPATH
```

#### 2. Keycloak Connection Issues
```bash
# Check if Keycloak is running
curl http://localhost:8080/realms/ams-portal/.well-known/openid-configuration

# Verify client configuration
# Admin Console: http://localhost:8080
```

#### 3. Storage Agent Failures
```python
# Debug storage connections
from core.connectivity.agents.agent_factory import AgentFactory

config = {...}
agent = AgentFactory.create_agent("s3", config)
# Test connection manually
```

#### 4. Permission Denied Errors
```bash
# Check Casbin policies
cat core/settings/managers/policies/casbin/test_policies.csv

# Verify user roles in Keycloak
```

### Debug Mode

Enable debug logging in `config.yaml`:
```yaml
logging:
  level: DEBUG
```

Or set environment variable:
```bash
export LOG_LEVEL=DEBUG
```

### Performance Profiling

```python
# Add to main.py for profiling
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Your code here

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative').print_stats(10)
```

## Contributing Guidelines

1. **Code Style**: Follow PEP 8, use Black formatter
2. **Type Hints**: Add type hints to all functions
3. **Documentation**: Include docstrings for all public methods
4. **Testing**: Write tests for new functionality
5. **Security**: Never commit secrets or credentials

### Pre-commit Checklist

```bash
# Format code
black .
isort .

# Lint
flake8 .
mypy .

# Security scan
bandit -r .
safety check

# Run tests
pytest
```

### Git Workflow

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and commit with clear messages
3. Push branch: `git push origin feature/my-feature`
4. Create pull request with description
5. Address review feedback
6. Merge after approval

This completes the developer onboarding documentation. The guide provides comprehensive information for developers to understand, contribute to, and extend the AMS Data Portal.