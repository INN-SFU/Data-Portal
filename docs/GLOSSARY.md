# AMS Data Portal - Technical Glossary

A comprehensive dictionary of technical terms, concepts, and components used throughout the AMS Data Portal system.

---

## Authentication & Authorization

### **Keycloak**
Open-source Identity and Access Management (IAM) solution providing OAuth2/OIDC authentication for the AMS Portal. Manages user accounts, roles, and token issuance.

### **OAuth2 / OIDC**
- **OAuth2**: Authorization framework enabling secure delegated access
- **OIDC (OpenID Connect)**: Authentication layer built on top of OAuth2, used for user login flows

### **JWT (JSON Web Token)**
Compact, URL-safe token format used for securely transmitting user claims between parties. Contains three parts: header, payload (claims), and signature.

### **Access Token**
Short-lived JWT issued by Keycloak after successful authentication. Used to authenticate API requests by including in the `Authorization: Bearer {token}` header.

### **Refresh Token**
Long-lived token used to obtain new access tokens without re-authentication. More sensitive than access tokens and should be stored securely.

### **Keycloak Realm**
An isolated administrative domain in Keycloak. The AMS Portal uses the `ams-portal` realm to manage its users and clients.

### **Keycloak Admin Role**
A role assigned within the Keycloak realm (checked in `realm_access.roles` or `resource_access.{client}.roles` for "admin"). Grants access to administrative API endpoints.

**Allowed Operations:**
- **User Management:**
  - List all users (`GET /api/users/`)
  - Create users (`POST /api/users/`) - Creates user in Keycloak
  - View user dashboard (`GET /api/users/dashboard`)
  - View/delete any user (owner-or-admin endpoints)

- **Storage Instance Management:**
  - List all instances (`GET /api/instances/`)
  - Get instance details (`GET /api/instances/{id}`)
  - Create instances (`POST /api/instances/`) - Auto-grants creator Casbin admin policy
  - Delete instances (`DELETE /api/instances/{id}`) - **Requires Casbin admin with `.*` resource on instance**
  - View instance dashboard (`GET /api/instances/dashboard`)

- **Policy Management:**
  - List all policies (`GET /api/policies/`)
  - Create policies (`POST /api/policies/`) - **Requires Casbin admin on target instance/resource**
  - Delete policies (`DELETE /api/policies/`) - **Requires Casbin admin on target instance/resource**
  - Validate policies (`POST /api/policies/validate`)
  - View policy dashboard (`GET /api/policies/dashboard`) - Filtered by Casbin admin access

- **Asset Management:**
  - View asset dashboard (`GET /api/assets/dashboard`)

**Important Distinctions:**
1. **Two-Tier Authorization:** Most admin operations require BOTH Keycloak admin role AND appropriate Casbin permissions
   - Instance deletion: Keycloak admin + Casbin admin (`.*` resource) on instance
   - Policy CRUD: Keycloak admin + Casbin admin on target instance/resource
   - Instance creation: Keycloak admin only (auto-grants creator Casbin admin)
   - User management: Keycloak admin only (users are system-wide, not per-instance)

2. **File Access:** Keycloak admin does NOT grant file read/write/delete access. File operations require Casbin `read`, `write`, or `delete` actions.

3. **Instance Admin vs System Admin:** Keycloak admin is a system role providing API access; Casbin admin is an instance/resource-level permission for delegation.

**Separate from Casbin Admin:** This is a Keycloak realm role (system-wide), distinct from Casbin "admin" action (instance/resource-level policy management permission).

### **Casbin**
Open-source authorization library implementing Role-Based Access Control (RBAC). Used for fine-grained, resource-level access control in the AMS Portal.

### **Casbin Policy**
A rule defining access permissions in the format: `p, user_uuid, instance_uuid, resource_pattern, action`

Example: `p, abc-123, def-456, data/reports/.*, read`

### **Casbin Admin Action**
The "admin" action in Casbin policies grants **policy management** permissions for specific resources/instances. It does NOT grant file read/write/delete access.

**Use case:** Allows a user to manage (view/modify) access policies for resources they have admin action on.

**Example:** User with `p, user_uuid, instance_uuid, data/reports/.*, admin` can manage policies for files under `data/reports/` but cannot read/write those files without separate read/write policies.

**Important:** This is instance/resource-level permission, distinct from Keycloak realm admin role.

### **Policy Store**
Database-agnostic term for where user policies are persisted. Currently implemented as individual `.policies` files per user UUID in `backend/data/policies/`.

### **RBAC (Role-Based Access Control)**
Access control paradigm where permissions are assigned based on roles. The AMS Portal uses Casbin to implement RBAC at the resource level.

---

## Storage & Data Access

### **Storage Instance**
A configured connection to a storage backend (e.g., S3-compatible storage). Each instance has:
- Unique UUID (generated via `uuid5(NAMESPACE_DNS, instance_name)`)
- Name (user-friendly identifier)
- Flavour (storage backend type: "s3", "dummy", etc.)
- Agent (handles backend-specific operations)

### **Storage Agent**
Pluggable component implementing the `AbstractStorageAgent` interface. Handles backend-specific operations like:
- Generating presigned URLs
- Loading file trees
- Managing connections

**Available Flavours:**
- **S3 Agent**: AWS S3-compatible storage (MinIO, S3, etc.)
- **Dummy Agent**: Mock storage for testing

### **Storage Flavour**
The type/implementation of storage backend. Currently supported: `s3`, `dummy`.

### **Presigned URL**
Temporary URL with embedded authentication allowing direct client access to storage resources without exposing credentials. Generated by storage agents with configurable TTL (Time-To-Live).

**Security:** URLs are signed with storage credentials and expire after TTL, limiting exposure window.

### **File Tree**
In-memory hierarchical representation of files/folders in a storage instance, implemented using `treelib.Tree`. Used for:
- Displaying directory structure to users
- Filtering accessible resources based on policies
- Generating access links

### **Resource Pattern**
Regular expression pattern used in Casbin policies to match file paths. Examples:
- `.*` - matches all resources
- `data/project1/.*` - matches all files under `data/project1/`
- `data/reports/2024/.*` - matches files under `data/reports/2024/`

---

## API & Backend Architecture

### **FastAPI**
Modern Python web framework used for the AMS Portal backend. Provides:
- Automatic API documentation (OpenAPI/Swagger)
- Type validation via Pydantic
- Dependency injection system
- Async request handling

### **Dependency Injection**
Design pattern where components receive their dependencies rather than creating them. Implemented in `core/injection/managers.py` to provide managers to API endpoints.

**Example:** `instance_manager: AbstractInstanceManager = Depends(get_instance_manager)`

### **API Endpoint**
HTTP route handling specific operations. AMS Portal endpoints follow pattern: `/api/{resource}/`

**Examples:**
- `/api/auth/` - Authentication operations
- `/api/users/` - User management
- `/api/instances/` - Storage instance management
- `/api/policies/` - Policy management
- `/api/assets/` - File access operations

### **Manager (Abstract)**
Interface defining core business logic operations. Abstract managers define contracts:
- `AbstractUserManager` - User CRUD operations
- `AbstractPolicyManager` - Policy enforcement and management
- `AbstractInstanceManager` - Storage instance lifecycle

### **Manager (Concrete Implementation)**
Specific implementation of an abstract manager:
- `KeycloakUserManager` - Implements `AbstractUserManager` using Keycloak API
- `CasbinPolicyManager` - Implements `AbstractPolicyManager` using Casbin
- `InstanceManager` - Implements `AbstractInstanceManager`

---

## Security Concepts

### **XSS (Cross-Site Scripting)**
Security vulnerability where attackers inject malicious scripts into web applications. Scripts execute in victims' browsers, potentially stealing tokens, cookies, or performing unauthorized actions.

**Types:**
- **Stored XSS**: Malicious script stored on server (e.g., in database)
- **Reflected XSS**: Malicious script in URL/request, reflected in response
- **DOM-based XSS**: Vulnerability in client-side JavaScript

**Mitigation:** Input sanitization, output encoding, CSP headers, HttpOnly cookies.

### **HTTPS**
Encrypted HTTP protocol using TLS/SSL. Protects data in transit from network-level attacks (eavesdropping, tampering) but does NOT prevent application-layer attacks like XSS.

### **HttpOnly Cookie**
Cookie with `HttpOnly` flag preventing JavaScript access via `document.cookie`. Protects session tokens from XSS attacks even if malicious script executes.

**Example:** `Set-Cookie: session=abc; HttpOnly; Secure; SameSite=Strict`

### **Content Security Policy (CSP)**
HTTP header restricting what resources browsers can load/execute. Prevents XSS by blocking inline scripts and unauthorized resource loading.

**Example:** `Content-Security-Policy: default-src 'self'; script-src 'self'`

### **CORS (Cross-Origin Resource Sharing)**
Browser security mechanism controlling which origins can access resources. Required when frontend and backend are on different domains/ports.

### **Token Introspection**
Process of validating a token by querying the authorization server (Keycloak). Provides real-time validation but adds network overhead.

**Alternative:** JWKS-based validation using public keys (faster, no per-request network call).

### **JWKS (JSON Web Key Set)**
Set of public keys published by Keycloak at `/.well-known/jwks.json`. Used by backend to verify JWT signatures without contacting Keycloak for each request.

---

## Development & Infrastructure

### **Docker Compose**
Tool for defining and running multi-container Docker applications. AMS Portal uses compose files:
- `local/docker-compose.yaml` - Main orchestration
- `keycloak/docker-compose.keycloak.yml` - Keycloak service
- `minio/docker-compose.yaml` - MinIO (S3-compatible storage)
- `backend/docker-compose.backend.yml` - FastAPI backend
- `frontend/docker-compose.frontend-prod.yml` - React frontend (production)
- `frontend/docker-compose.frontend.yml` - React frontend (development)

### **MinIO**
S3-compatible object storage server used for local development and testing. Provides AWS S3 API compatibility without requiring AWS account.

### **React**
JavaScript library for building user interfaces. Used for the AMS Portal frontend with built-in XSS protection via automatic escaping in JSX.

### **Vite**
Modern frontend build tool providing fast development server with hot module replacement (HMR). Used in the React frontend.

---

## Data Models

### **User UUID**
Universally Unique Identifier for users, provided by Keycloak in JWT claims as the `sub` (subject) field. Used as subject in Casbin policies.

### **Instance UUID**
Universally Unique Identifier for storage instances, generated deterministically via `uuid5(NAMESPACE_DNS, instance_name)`. Ensures same name always generates same UUID.

### **Policy Model**
```python
Policy(
    user_uuid: UUID,
    instance_uuid: UUID,
    resource: str,        # Regex pattern
    action: str          # 'read', 'write', 'admin'
)
```

### **Instance Model**
```python
Instance(
    uuid: UUID,
    name: str,
    flavour: str,
    agent: AbstractStorageAgent
)
```

---

## Common Actions

### **read**
Permission to download/view files. Implemented via presigned GET URLs.

### **write**
Permission to upload/modify files. Implemented via presigned PUT/POST URLs.

### **admin** (Casbin action)
Permission to manage policies for resources. Does NOT grant read/write access to files.

### **list**
Permission to view file tree structure. Required for browsing directories.

### **delete**
Permission to remove files. Implemented via presigned DELETE URLs.

---

## Authentication Flows

### **Authorization Code Flow**
OAuth2 flow used for user authentication:
1. User clicks login → redirected to Keycloak
2. User enters credentials
3. Keycloak redirects back with authorization code
4. Frontend exchanges code for tokens (access + refresh)
5. Frontend stores tokens and uses access token for API calls

**Security:** Most secure OAuth2 flow, prevents token interception via code exchange.

### **Client Credentials Flow**
OAuth2 flow for machine-to-machine authentication. Backend uses this to obtain admin token for Keycloak Admin API operations.

**Use case:** Backend startup, user creation, role assignment.

### **Token Refresh Flow**
Process of obtaining new access token using refresh token when access token expires:
1. API returns 401 (token expired)
2. Frontend sends refresh token to Keycloak
3. Keycloak returns new access + refresh tokens
4. Frontend retries original request with new access token

---

## File Operations

### **File Upload**
Process:
1. Frontend requests upload URL from backend
2. Backend validates user has 'write' permission via Casbin
3. Backend generates presigned POST URL (TTL: 900s, max size: 100MB)
4. Frontend uploads directly to S3 using presigned URL
5. Frontend confirms upload to backend for audit logging

### **File Download**
Process:
1. User requests file download
2. Backend validates user has 'read' permission via Casbin
3. Backend generates presigned GET URL (TTL: 3600s)
4. Frontend redirects user to presigned URL
5. User downloads directly from S3

### **Folder Download (ZIP)**
Process:
1. Backend lists all files in folder (with permission filtering)
2. Backend generates presigned URL for each accessible file
3. Frontend fetches files and creates ZIP archive client-side (JSZip)
4. User downloads generated ZIP

---

## System Initialization

### **Backend Initialization**
Process when backend starts:
1. Load environment variables
2. Initialize Keycloak connection
3. Load storage instance configurations
4. Initialize Casbin enforcer with policy model
5. Load user policies from Policy Store
6. Start FastAPI application

### **Policy Loading**
At startup, `CasbinPolicyManager`:
1. Reads `model.conf` (RBAC definition)
2. Creates empty `policy.csv` (placeholder for enforcer)
3. Loads individual `.policies` files for each user UUID
4. Adds all policies to Casbin enforcer in-memory

---

## Configuration Files

### **model.conf**
Casbin RBAC model definition:
```
[request_definition]
r = sub, dom, obj, act

[policy_definition]
p = sub, dom, obj, act

[matchers]
m = r.sub == p.sub && r.dom == p.dom && regexMatch(r.obj, p.obj) && regexMatch(r.act, p.act)
```

### **policy.csv**
Empty placeholder file (0 bytes) required by Casbin enforcer initialization. Actual policies loaded from individual user `.policies` files.

### **.policies files**
Per-user policy storage format: `{user_uuid}.policies`

**Format:** Each line contains comma-separated policy fields:
```
p, user_uuid, instance_uuid, resource_pattern, action
```

---

## Architecture Patterns

### **Abstract Factory Pattern**
Used for storage agent creation. `agent_factory()` returns appropriate concrete agent based on flavour configuration.

### **Dependency Injection Pattern**
FastAPI dependencies provide managers to endpoints, enabling loose coupling and testability.

### **Repository Pattern**
Managers act as repositories abstracting data access from business logic.

---

## Limitations & Known Issues

### **File Tree Pagination**
Currently NOT implemented. S3 agent only fetches first 1000 objects per bucket via `list_objects_v2()`. Buckets with >1000 objects will have incomplete file trees.

**Impact:** Users may not see all files in large buckets.
**Status:** Documented limitation, pagination implementation pending.

### **Token Storage**
Current implementation uses sessionStorage/memory for JWT tokens. While better than localStorage, still vulnerable to XSS attacks.

**Recommended improvement:** Migrate to HttpOnly cookies for better XSS protection.

---

**Last Updated:** 2025-01-27
**Version:** 0.1
