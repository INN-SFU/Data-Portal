# Component Architecture

## System Overview

High-level view of the AMS Data Portal components and their relationships.

```mermaid
graph TB
    subgraph "User Layer"
        User[User Browser]
        Admin[Admin User]
    end

    subgraph "Frontend Layer"
        ReactUI[React Frontend<br/>Port 3000]
    end

    subgraph "Application Layer"
        Backend[Backend API<br/>FastAPI<br/>Port 8000]

        subgraph "Core Components"
            Auth[Authentication<br/>Module]

            subgraph "Policy Manager"
                Policy[CasbinPolicy<br/>Manager]
            end

            subgraph "Instance Manager"
                Instance[Instance<br/>Manager]
                Storage[Storage Agents<br/>S3, Dummy]
            end
        end
    end

    subgraph "Authentication Layer"
        Keycloak[Keycloak<br/>OIDC Provider<br/>Port 8080]
    end

    subgraph "Storage Backends"
        S3[S3-Compatible<br/>Storage]
        Dummy[Dummy Storage<br/>Testing]
    end

    User -->|HTTPS| ReactUI
    Admin -->|HTTPS| ReactUI
    ReactUI -->|REST API<br/>Bearer Token| Backend
    Backend -->|Validates Tokens| Auth
    Auth -->|OIDC/OAuth2| Keycloak
    Backend -->|Enforces Policies| Policy
    Backend -->|Manages Instances| Instance
    Instance -->|Contains| Storage
    Storage -->|Filters via| Policy
    Storage -->|Presigned URLs| S3
    Storage -->|Mock Operations| Dummy

    style Backend fill:#4A90E2
    style Keycloak fill:#E94B3C
    style ReactUI fill:#61DAFB
    style Policy fill:#FFD700
    style Instance fill:#4A90E2
```

## Backend Core Components

Detailed view of the backend application structure.

```mermaid
graph LR
    subgraph "API Layer v0.1"
        AuthAPI[Auth Endpoints<br/>/api/auth]
        AssetsAPI[Assets API<br/>/api/assets]
        UsersAPI[Users API<br/>/api/users]
        PoliciesAPI[Policies API<br/>/api/policies]
        InstancesAPI[Instances API<br/>/api/instances]
        HealthAPI[Health API<br/>/api/health]
    end

    subgraph "Dependency Injection"
        Injection[Dependency<br/>Injection Layer<br/>core/injection]
    end

    subgraph "Core Business Logic"
        PolicyMgr[Policy<br/>Manager]
        InstanceMgr[Instance<br/>Manager]
        UserMgr[User<br/>Manager]
    end

    subgraph "Concrete Policy Manager"
        CasbinPolicyMgr[CasbinPolicy<br/>Manager]
        CasbinEnforcer[Casbin<br/>Enforcer]
    end

    subgraph "Concrete Instance Manager"
        ConcreteInstanceMgr[InstanceManager<br/>Implementation]
    end

    subgraph "Concrete User Manager"
        KeycloakUserMgr[KeycloakUser<br/>Manager]
    end

    subgraph "Storage Agents"
        AgentFactory[Agent<br/>Factory]
        AbstractAgent[Abstract Storage<br/>Agent Interface]
        S3Agent[S3 Storage<br/>Agent]
        DummyAgent[Dummy Storage<br/>Agent]
    end

    subgraph "External Services"
        KeycloakSvc[Keycloak<br/>Service]
        S3Backend[S3<br/>Backend]
    end

    AuthAPI --> Injection
    AssetsAPI --> Injection
    UsersAPI --> Injection
    PoliciesAPI --> Injection
    InstancesAPI --> Injection

    Injection --> PolicyMgr
    Injection --> InstanceMgr
    Injection --> UserMgr

    PolicyMgr -.->|implements| CasbinPolicyMgr
    InstanceMgr -.->|implements| ConcreteInstanceMgr
    UserMgr -.->|implements| KeycloakUserMgr

    CasbinPolicyMgr --> CasbinEnforcer
    CasbinEnforcer -.->|Enforces Rules| AbstractAgent

    ConcreteInstanceMgr --> AgentFactory
    AgentFactory -.->|Creates| AbstractAgent
    AbstractAgent --> S3Agent
    AbstractAgent --> DummyAgent

    AuthAPI -.->|Validates Tokens| KeycloakSvc
    UserMgr -.->|CRUD Operations| KeycloakSvc
    S3Agent -.->|Presigned URLs| S3Backend

    style Injection fill:#90EE90
    style PolicyMgr fill:#FFD700
    style InstanceMgr fill:#4A90E2
    style AbstractAgent fill:#95E1D3
```

## Storage Agent Architecture

Pluggable storage backend system using the Abstract Factory pattern.

```mermaid
classDiagram
    class AbstractStorageAgent {
        <<abstract>>
        +FLAVOUR: str
        +file_tree: Tree
        +instance_url: str
        +config(secrets) dict
        +generate_access_link(resource, method, ttl) Tuple
        +filter_file_tree(node_filter) Tree
        +partition_file_tree_by_access() Dict
        +refresh_file_tree()
        +smart_refresh_file_tree()*
        +refresh_connection()*
        +close()*
    }

    class S3StorageAgent {
        +FLAVOUR = "s3"
        -s3_client: boto3.Client
        +generate_access_link(resource, method, ttl) Tuple
        +smart_refresh_file_tree()
        +refresh_connection()
        +close()
        -fetch_all_buckets() List
        -fetch_all_bucket_keys(bucket) List
    }

    class DummyStorageAgent {
        +FLAVOUR = "dummy"
        -mock_data: dict
        +generate_access_link(resource, method, ttl) Tuple
        +smart_refresh_file_tree()
        +refresh_connection()
        +close()
    }

    class AgentFactory {
        +agent_factory(config) AbstractStorageAgent
        +AVAILABLE_FLAVOURS: dict
    }

    AbstractStorageAgent <|-- S3StorageAgent
    AbstractStorageAgent <|-- DummyStorageAgent
    AgentFactory ..> AbstractStorageAgent : creates
    AgentFactory ..> S3StorageAgent : instantiates
    AgentFactory ..> DummyStorageAgent : instantiates
```

## Policy Management Architecture

Casbin-based RBAC system with flexible policy enforcement.

```mermaid
graph TB
    subgraph "Policy Layer"
        CasbinEnforcer[Casbin Enforcer<br/>RBAC Model]
        ModelConf[model.conf<br/>RBAC Definition]
    end

    subgraph "Policy Manager"
        PolicyMgr[CasbinPolicy Manager]
        PolicyStore[User Policy Store]
    end

    subgraph "Access Control"
        CheckAccess[Check Access]
        GrantAccess[Grant Access]
        RevokeAccess[Revoke Access]
    end

    ModelConf --> CasbinEnforcer
    PolicyMgr --> CasbinEnforcer
    PolicyMgr --> PolicyStore
    PolicyStore -.->|Loads at init| PolicyMgr

    CheckAccess --> CasbinEnforcer
    GrantAccess --> PolicyMgr
    RevokeAccess --> PolicyMgr

    BackendAPI[Backend API] --> CheckAccess
    AdminAPI[Admin API] --> GrantAccess
    AdminAPI --> RevokeAccess

    style CasbinEnforcer fill:#FFD700
    style PolicyMgr fill:#4A90E2
```

## Data Flow

How data moves through the system for a typical file download request.

```mermaid
graph LR
    User[User] -->|1. Request File| Frontend
    Frontend -->|2. API Call + JWT| Backend
    Backend -->|3. Validate Token| Keycloak
    Keycloak -->|4. User Info| Backend
    Backend -->|5. Check Policy| PolicyMgr
    PolicyMgr -->|6. Enforce via Casbin| PolicyMgr
    PolicyMgr -->|7. ALLOW| Backend
    Backend -->|8. Get Instance| InstanceMgr
    InstanceMgr -->|9. Return Instance.agent| Backend
    Backend -->|10. Generate Presigned URL| StorageAgent
    StorageAgent -->|11. Create URL| S3
    S3 -->|12. Presigned URL| StorageAgent
    StorageAgent -->|13. URL| Backend
    Backend -->|14. URL Response| Frontend
    Frontend -->|15. Redirect| User
    User -->|16. Direct Download| S3

    style Backend fill:#4A90E2
    style Keycloak fill:#E94B3C
    style PolicyMgr fill:#FFD700
    style InstanceMgr fill:#4A90E2
    style S3 fill:#FF9900
```

---

## Component Responsibilities

### Frontend (React)
- User interface and interaction
- Authentication flow (OAuth2/OIDC)
- API communication with Bearer tokens
- File upload/download UI
- Admin dashboard

### Backend (FastAPI)
- REST API endpoints
- JWT token validation
- Policy enforcement (Casbin)
- Storage agent coordination
- User and instance management

### Keycloak
- User authentication (OIDC)
- Token issuance (JWT)
- User management
- Role-based access control
- SSO support

### Storage Agents
- Abstract storage interface
- S3 presigned URL generation
- File tree loading
- Backend-specific operations

### Casbin Policy Engine
- RBAC policy enforcement
- Fine-grained access control
- Dynamic policy management
- Resource-level permissions

---

**Last Updated:** 2025-10-23
