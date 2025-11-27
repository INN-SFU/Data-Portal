# Authentication Sequence Diagrams

## User Login Flow

Complete OAuth2/OIDC authentication flow with Keycloak.

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant Frontend
    participant Backend
    participant Keycloak

    User->>Browser: Navigate to App
    Browser->>Frontend: Load React App
    Frontend->>Browser: Show Login Button

    User->>Frontend: Click Login
    Frontend->>Keycloak: Redirect to /auth<br/>(OAuth2 Authorization)
    Note over Keycloak: Authorization Endpoint

    Keycloak->>User: Show Login Form
    User->>Keycloak: Enter Credentials<br/>(username/password)

    Keycloak->>Keycloak: Validate Credentials
    Keycloak->>Frontend: Redirect with Auth Code
    Note over Frontend,Keycloak: Redirect URI with code parameter

    Frontend->>Keycloak: Exchange Code for Token<br/>(Token Endpoint)
    Note over Frontend,Keycloak: POST /token<br/>grant_type=authorization_code

    Keycloak->>Frontend: JWT Access Token<br/>+ Refresh Token

    Frontend->>Frontend: Store Token<br/>(Memory/SessionStorage)

    Note over Frontend,Backend: Authenticated API Request

    Frontend->>Backend: API Request<br/>Authorization: Bearer {token}
    Backend->>Backend: Extract JWT from Header
    Backend->>Keycloak: Validate Token<br/>(Introspection or JWKS)
    Keycloak->>Backend: Token Valid + User Info
    Backend->>Backend: Extract User Claims<br/>(sub, email, roles)
    Backend->>Backend: Check Casbin Policies
    Backend->>Frontend: API Response
    Frontend->>Browser: Update UI
```

## Token Validation Flow

How the backend validates JWT tokens from Keycloak.

```mermaid
sequenceDiagram
    participant Frontend
    participant Backend
    participant JWTModule
    participant Keycloak
    participant Casbin

    Frontend->>Backend: API Request<br/>Authorization: Bearer {jwt}

    Backend->>JWTModule: Extract and Validate Token
    JWTModule->>JWTModule: Decode JWT Header<br/>(Check algorithm)

    alt Using JWKS Validation (Recommended)
        JWTModule->>Keycloak: GET /.well-known/jwks.json
        Keycloak->>JWTModule: Public Keys (JWKS)
        JWTModule->>JWTModule: Verify Signature<br/>with Public Key
    else Using Introspection
        JWTModule->>Keycloak: POST /token/introspect
        Keycloak->>JWTModule: Token Active + Claims
    end

    alt Token Valid
        JWTModule->>JWTModule: Check Expiration (exp)
        JWTModule->>JWTModule: Check Audience (aud)
        JWTModule->>JWTModule: Check Issuer (iss)
        JWTModule->>Backend: User Claims<br/>{sub, email, roles}

        Backend->>Casbin: Check Authorization<br/>(user, resource, action)
        Casbin->>Backend: ALLOW/DENY

        alt Authorization Granted
            Backend->>Frontend: 200 OK<br/>Response Data
        else Authorization Denied
            Backend->>Frontend: 403 Forbidden
        end
    else Token Invalid
        JWTModule->>Backend: Invalid Token
        Backend->>Frontend: 401 Unauthorized
    end
```

## Admin Operation Flow

Authorization flow for admin-only operations.

```mermaid
sequenceDiagram
    actor Admin
    participant Frontend
    participant Backend
    participant Keycloak
    participant Casbin

    Admin->>Frontend: Request Admin Operation<br/>(e.g., Create User)
    Frontend->>Backend: POST /api/admin/user/<br/>Authorization: Bearer {token}

    Backend->>Backend: Extract JWT
    Backend->>Keycloak: Validate Token
    Keycloak->>Backend: Valid Token<br/>+ User Claims

    Backend->>Backend: Extract Roles<br/>(realm_access.roles)

    alt Has Keycloak Admin Role
        Note over Backend,Casbin: Keycloak realm "admin" role grants<br/>access to all admin operations

        alt User CRUD Operation
            Backend->>Keycloak: Admin API Call<br/>Create/Update/Delete User
            Keycloak->>Backend: User Modified<br/>{user_id, email}
            Backend->>Casbin: Update User Policies<br/>(create/remove policy store)
            Casbin->>Backend: Policies Updated
            Backend->>Frontend: 200/201 OK<br/>{message, user_data}
        else Policy CRUD Operation
            Backend->>Casbin: Add/Remove Policy
            Casbin->>Backend: Policy Modified
            Backend->>Backend: Persist to Policy Store
            Backend->>Frontend: 200 OK<br/>{message, policy_data}
        else Instance CRUD Operation
            Backend->>Backend: Create/Update/Delete Instance
            Backend->>Backend: Save Instance Config
            Backend->>Casbin: Update Instance Policies
            Casbin->>Backend: Policies Updated
            Backend->>Frontend: 200/201 OK<br/>{message, instance_data}
        end

        Frontend->>Admin: Success Message

    else No Keycloak Admin Role
        Backend->>Frontend: 403 Forbidden<br/>Admin role required
        Frontend->>Admin: Error Message
    end
```

## Token Refresh Flow

Refreshing expired access tokens without re-login.

```mermaid
sequenceDiagram
    participant Frontend
    participant Backend
    participant Keycloak

    Frontend->>Backend: API Request<br/>Authorization: Bearer {expired_token}
    Backend->>Backend: Validate Token
    Backend->>Frontend: 401 Unauthorized<br/>Token Expired

    Frontend->>Frontend: Check Refresh Token<br/>Exists and Valid?

    alt Has Valid Refresh Token
        Frontend->>Keycloak: POST /token<br/>grant_type=refresh_token<br/>refresh_token={refresh_token}

        Keycloak->>Keycloak: Validate Refresh Token
        Keycloak->>Frontend: New Access Token<br/>+ New Refresh Token

        Frontend->>Frontend: Store New Tokens
        Frontend->>Backend: Retry Original Request<br/>Authorization: Bearer {new_token}
        Backend->>Backend: Validate New Token
        Backend->>Frontend: 200 OK<br/>Response Data

    else No Refresh Token or Invalid
        Frontend->>Frontend: Clear Tokens
        Frontend->>Frontend: Redirect to Login
    end
```

## User Management Flow

Creating a new user through the admin API.

```mermaid
sequenceDiagram
    actor Admin
    participant Backend
    participant Keycloak
    participant PolicyMgr
    participant Casbin

    Admin->>Backend: POST /api/users/<br/>{username, email, password}

    Backend->>Backend: Validate JWT Token
    Backend->>Backend: Check Keycloak Admin Role<br/>(realm_access.roles)
    Note over Backend: Requires "admin" role in Keycloak realm

    Backend->>Keycloak: POST /admin/realms/{realm}/users<br/>{username, email, enabled: true}
    Keycloak->>Keycloak: Create User Account
    Keycloak->>Backend: 201 Created<br/>{user_id}

    Backend->>Keycloak: PUT /admin/realms/{realm}/users/{user_id}/reset-password<br/>{value: password, temporary: false}
    Keycloak->>Backend: 204 No Content

    Backend->>Keycloak: POST /admin/realms/{realm}/users/{user_id}/role-mappings/realm<br/>[{name: "user"}]
    Keycloak->>Backend: 204 No Content

    Backend->>PolicyMgr: Add Default Policies<br/>(user basic access)
    PolicyMgr->>Casbin: Add Policy Rules
    Casbin->>PolicyMgr: Policies Added
    PolicyMgr->>PolicyMgr: Persist to Policy Store

    Backend->>Admin: 201 Created<br/>{user_id, username, email}
```

## Logout Flow

Proper session termination and token revocation.

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant Backend
    participant Keycloak

    User->>Frontend: Click Logout

    Frontend->>Backend: POST /api/auth/logout<br/>Authorization: Bearer {token}
    Backend->>Backend: Extract Token

    Backend->>Keycloak: POST /logout<br/>id_token_hint={id_token}<br/>post_logout_redirect_uri={uri}

    Keycloak->>Keycloak: Revoke Session
    Keycloak->>Keycloak: Invalidate Tokens
    Keycloak->>Backend: Redirect to URI

    Backend->>Frontend: 200 OK<br/>Logout Successful

    Frontend->>Frontend: Clear Local Tokens<br/>(SessionStorage/Memory)
    Frontend->>Frontend: Clear User State
    Frontend->>User: Redirect to Login Page
```

---

## Authentication Patterns

### Pattern 1: Authorization Code Flow (Standard)
- **Use Case:** Web applications with a backend
- **Security:** Most secure, code exchange prevents token interception
- **Implementation:** Current system uses this for user authentication

### Pattern 2: Client Credentials Flow
- **Use Case:** Service-to-service communication
- **Security:** Machine authentication, no user context
- **Implementation:** Backend uses this for Keycloak admin operations
- **Details:** See [Backend Initialization](../../backend/docs/INITIALIZATION.md)

### Pattern 3: Resource Owner Password Flow
- **Use Case:** Trusted first-party apps
- **Security:** Less secure, credentials exposed to client
- **Status:** Used only for admin CLI token in init scripts
- **Details:** See [Backend Initialization](../../backend/docs/INITIALIZATION.md)

---

## Security Considerations

### Token Storage
- ✅ **Memory/SessionStorage** - Current implementation
- ❌ **LocalStorage** - Vulnerable to XSS attacks
- ✅ **HTTP-only Cookies** - Alternative secure option

### Token Validation
- ✅ **JWKS-based** - Fast, no network call per request
- ✅ **Token Introspection** - Real-time revocation check
- ⚠️ **Signature Verification** - Always verify, never trust client

### Authorization Checks
- ✅ **Backend enforcement** - Never trust frontend
- ✅ **Casbin policies** - Fine-grained control
- ✅ **Role-based + Resource-based** - Defense in depth

---

**Last Updated:** 2025-10-23
