# Storage Issuer - Architecture & Design

## Overview

The Storage Issuer is a standalone microservice that issues JWT tokens for secure, time-limited access to storage resources. It's designed to work with any storage type that lacks native presigned URL support (POSIX, NFS, WebDAV, etc.).

## Architecture

### Component Placement

```
┌─────────────────────────────────────────────────────────┐
│  Application Server                                     │
│  ┌──────────────────┐         ┌───────────────────┐    │
│  │  AMS Backend     │────────▶│ Storage Issuer    │    │
│  │                  │ API Key │                   │    │
│  │ - Auth (Keycloak)│         │ - Signs JWT       │    │
│  │ - Authz (Casbin) │         │ - JWKS endpoint   │    │
│  │ - Policy checks  │         │ - RSA keys        │    │
│  └──────────────────┘         └───────────────────┘    │
└─────────────────────────────────────────────────────────┘
                │                         │
                │ Returns JWT token       │ Public key (JWKS)
                ▼                         ▼
           ┌─────────┐         ┌──────────────────────┐
           │  User   │────────▶│  Storage Gateway     │
           └─────────┘         │  (validates token)   │
              Presents JWT     └──────────────────────┘
                                         │
                                         ▼
                               ┌──────────────────────┐
                               │  POSIX Filesystem    │
                               └──────────────────────┘
```

### Why Separate from Backend?

**Design Decision:** Storage Issuer is a separate microservice, not embedded in AMS Backend.

**Rationale:**
1. **Security Isolation**: Private signing key isolated from main application
2. **Independent Scaling**: Token issuance can scale separately from API
3. **Reusability**: Can serve multiple AMS instances
4. **Storage Agnostic**: Works with any storage type needing JWT tokens
5. **Clean Separation**: Backend handles policy, Issuer handles signing

### Why NOT Use This for S3?

S3 already has native presigned URLs via AWS SDK. No need for our JWT system:

```python
# S3StorageAgent - uses native AWS presigning
url = s3_client.generate_presigned_url('get_object', ...)
```

**Storage Issuer is only for storage types WITHOUT native presigning:**
- ✅ POSIX filesystems
- ✅ NFS shares
- ✅ WebDAV servers
- ❌ S3 (has native)
- ❌ Azure Blob (has SAS tokens)
- ❌ GCS (has signed URLs)

## JWT Token Design

### Token Format

**Algorithm:** RS256 (RSA with SHA-256)

**Why RS256?**
- Asymmetric: Private key signs, public key validates
- Gateway can validate without calling Issuer
- Gateway cannot forge tokens (doesn't have private key)
- Industry standard (OIDC, OAuth 2.0)

### Token Claims

```json
{
  "iss": "ams-storage-issuer",        // Issuer identifier
  "aud": "ams-storage-gateway",       // Audience (which service validates)
  "sub": "user-uuid-abc-123",         // Subject (user identifier)
  "exp": 1728394496,                  // Expiration (Unix timestamp)
  "iat": 1728390896,                  // Issued at (Unix timestamp)
  "jti": "unique-token-id",           // JWT ID (prevents replay attacks)

  // Custom claims - lock token to specific access
  "path": "folder/file.txt",          // Resource path (locked)
  "op": "read",                       // Operation: read|write (locked)
  "bundle": "file",                   // Download type: file|manifest|zip
  "iid": "instance-uuid",             // Instance identifier (optional)
  "cip": "192.168.1.100"              // Client IP (optional, for IP pinning)
}
```

### Security Features

**Path Locking:**
- Token only valid for the exact path in `path` claim
- Gateway rejects if requested path ≠ token path
- Prevents privilege escalation

**Operation Locking:**
- Separate tokens for read vs write
- Cannot use read token for write operations
- Fine-grained access control

**Time Limiting:**
- Configurable TTL (60s to 24h)
- Short-lived tokens reduce exposure
- Forces re-authentication/re-authorization

**Single-Use (via jti):**
- Gateway tracks used token IDs in Redis
- First use: allowed, jti stored
- Second use: rejected (replay attack)
- TTL in Redis matches token expiration

**IP Pinning (optional):**
- Lock token to specific client IP
- Gateway validates client IP matches `cip` claim
- Prevents token theft and reuse from different location

## Key Management

### RSA Key Pair

**Generation:**
```python
# Automatic on first startup
rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)
```

**Storage:**
- Private key: `/run/secrets/jwt_private_key` (secure location)
- Public key: Derived from private key, distributed via JWKS
- Permissions: 0600 (owner read/write only)

**Key Rotation (Future - Phase 5):**
- Generate new key pair
- Publish both keys in JWKS with different `kid` (key ID)
- Gateway caches multiple keys, validates with correct one
- Old tokens still valid until expiration
- Remove old key after all tokens expired

### JWKS Endpoint

**Purpose:** Distribute public key to Gateway for token validation

**Endpoint:** `GET /.well-known/jwks.json`

**Response:**
```json
{
  "keys": [
    {
      "kty": "RSA",           // Key type
      "use": "sig",           // Usage: signature
      "alg": "RS256",         // Algorithm
      "kid": "default",       // Key ID
      "n": "...",             // Modulus (base64url)
      "e": "AQAB"             // Exponent (base64url)
    }
  ]
}
```

**No Authentication Required:**
- Public key is safe to distribute
- Anyone can validate tokens
- Only Issuer can sign tokens

## API Design

### POST /v1/presign

**Authentication:** API Key (X-API-Key header)

**Why API Key?**
- Backend is trusted internal service
- Simpler than OAuth for service-to-service
- Rotatable secret
- No user context needed

**Request Flow:**
1. Backend validates user's Keycloak token
2. Backend checks Casbin policy for resource access
3. Backend calls Issuer with approved parameters
4. Issuer signs token (no further validation)
5. Backend returns token to user
6. User presents token to Gateway

**Trust Model:**
- Issuer trusts Backend completely
- Backend has already done auth/authz
- Issuer is a "dumb signing service"
- Keeps Issuer simple and focused

### Health & Monitoring

**GET /v1/health:**
- Service health check
- Signer initialization status
- Used by Docker health checks

**GET /:**
- Service information
- Version, issuer/audience claims
- Links to JWKS and docs

## Design Decisions

### Why Not Keycloak Validation in Issuer?

**Considered:** Issuer validates Keycloak tokens directly

**Rejected Because:**
- Duplicate validation (Backend already does this)
- Tighter coupling (Issuer depends on Keycloak)
- More complexity in Issuer
- Backend is source of truth for auth

**Instead:** Issuer trusts Backend via API key

### Why Not Policy Validation in Issuer?

**Considered:** Issuer calls Backend to check Casbin policies

**Rejected Because:**
- Duplicate work (Backend already checked)
- Extra network round-trip
- Backend is source of truth for authz
- Keeps Issuer simple

**Instead:** Backend checks policy before calling Issuer

### Why Standalone Service vs Library?

**Considered:** JWT signing as library embedded in Backend

**Rejected Because:**
- Private key in same process as web API (security risk)
- Can't scale token issuance independently
- Harder to audit token generation
- Less reusable across instances

**Instead:** Separate microservice with API key auth

### Module Naming: jwt_handler

**Original:** `jwt` module
**Problem:** Conflicts with PyJWT library (`import jwt`)

**Tried:** `token` module
**Problem:** Conflicts with Python built-in `token` module

**Final:** `jwt_handler`
**Result:** No conflicts, clear purpose

## Performance Considerations

### Token Generation

**Latency:** ~10-50ms per token
- RSA signing is CPU-intensive
- Acceptable for user-initiated downloads
- Can cache if needed (with caution)

**Throughput:** ~100-1000 tokens/sec
- Single instance sufficient for most use cases
- Can horizontally scale if needed
- Stateless design enables easy scaling

### JWKS Caching

**Gateway Should Cache:**
- Fetch JWKS once on startup
- Refresh periodically (e.g., every hour)
- Reduces load on Issuer
- Faster token validation

**Cache TTL:** 3600s (1 hour)
- Balance between freshness and performance
- Supports key rotation
- Minimal impact if Issuer restarts

## Future Enhancements

### Phase 3 (Gateway Service)
- Implement token validation
- Redis jti tracking
- File streaming
- Manifest and ZIP generation

### Phase 4 (Integration)
- Update PosixStorageAgent to call Issuer
- End-to-end testing
- Performance optimization

### Phase 5 (Production)
- TLS/mTLS for service communication
- Key rotation automation
- Metrics and monitoring (Prometheus)
- Distributed tracing (Jaeger)
- Rate limiting
- Token caching strategies
- Multi-instance deployment
- Load balancing

### Potential Features
- **Batch Presigning:** Generate multiple tokens in one request
- **Token Refresh:** Extend token lifetime before expiration
- **Scoped Tokens:** Multiple paths in single token
- **Delegation:** User can grant limited access to others
- **Audit Webhooks:** Notify on token generation
- **Custom Claims:** Instance-specific metadata
- **Token Revocation:** Blacklist tokens before expiration (requires state)

## Security Considerations

### Private Key Protection

**Storage:**
- tmpfs (RAM, not disk)
- Restricted permissions (0600)
- Not logged or exposed

**Rotation:**
- Manual process for now
- Automated in Phase 5
- Zero-downtime rotation via JWKS multi-key support

### API Key Management

**Current:**
- Environment variable
- Single shared secret

**Production (Phase 5):**
- Per-backend instance keys
- Stored in secrets manager (HashiCorp Vault)
- Rotation policy
- Audit logging of API key usage

### Token Security

**Mitigations:**
- **Short TTL:** Limits exposure window (default 1 hour)
- **Single-use (jti):** Prevents replay attacks
- **IP pinning:** Prevents theft (optional)
- **Path locking:** Limits scope
- **HTTPS only:** Prevents interception (production)

**Remaining Risks:**
- Token theft before first use (HTTPS mitigates)
- Compromised client can use token (normal for bearer tokens)
- No revocation without state (acceptable trade-off)

## Testing

### Unit Tests

**Covered:**
- JWT signing and validation
- JWKS generation
- Key pair generation
- Token expiration
- Invalid signature rejection

**Run:**
```bash
pytest storage-issuer/tests/ -v
```

### Integration Testing

**Manual:**
```bash
# Start service
docker compose up -d

# Test presign
curl -X POST http://localhost:8001/v1/presign \
  -H "X-API-Key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{"user_uuid":"test","path":"file.txt","op":"read","ttl":3600}'

# Test JWKS
curl http://localhost:8001/.well-known/jwks.json
```

### Load Testing (Future - Phase 5)

```bash
# Apache Bench
ab -n 1000 -c 10 -H "X-API-Key: dev-key" \
  -p presign-request.json \
  -T application/json \
  http://localhost:8001/v1/presign
```

## Deployment

### Development (Docker Compose)

```bash
docker compose -p ams-storage-issuer up -d
```

### Production (Phase 5)

**Kubernetes:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: storage-issuer
spec:
  replicas: 3
  selector:
    matchLabels:
      app: storage-issuer
  template:
    spec:
      containers:
      - name: issuer
        image: ams-storage-issuer:1.0
        env:
        - name: ISSUER_API_KEY
          valueFrom:
            secretKeyRef:
              name: issuer-secrets
              key: api-key
```

**Docker Swarm:**
```yaml
version: "3.8"
services:
  storage-issuer:
    image: ams-storage-issuer:1.0
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
    secrets:
      - jwt_private_key
      - issuer_api_key
```

## Monitoring & Observability

### Logs

**Structured Logging:**
```python
logger.info(
    "Token issued",
    extra={
        "user_uuid": user_uuid,
        "instance_uuid": instance_uuid,
        "path": path,
        "op": op,
        "ttl": ttl,
        "jti": jti
    }
)
```

### Metrics (Future - Phase 5)

**Prometheus Metrics:**
- `issuer_tokens_issued_total` - Counter of tokens issued
- `issuer_tokens_issued_duration_seconds` - Histogram of signing time
- `issuer_api_requests_total` - Counter by endpoint and status
- `issuer_api_request_duration_seconds` - Request latency

### Tracing (Future - Phase 5)

**OpenTelemetry:**
- Trace token generation through system
- Backend → Issuer → Gateway flow
- Correlate with user requests

## References

- [RFC 7519 - JSON Web Token (JWT)](https://tools.ietf.org/html/rfc7519)
- [RFC 7517 - JSON Web Key (JWK)](https://tools.ietf.org/html/rfc7517)
- [RFC 7518 - JSON Web Algorithms (JWA)](https://tools.ietf.org/html/rfc7518)
- [OIDC Core Specification](https://openid.net/specs/openid-connect-core-1_0.html)
- [System Design PDF](../data_portal/System_Design_Presigned_URL_Access_for_POSIX_Storage_in_AMS.pdf)
- [Backend Implementation Plan](../backend/POSIX_IMPLEMENTATION_PLAN.md)
