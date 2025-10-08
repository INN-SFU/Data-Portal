# POSIX Storage Agent - Implementation Plan

## Overview

This document outlines the phased implementation approach for adding presigned URL support for POSIX storage in the AMS system. The implementation follows the system design documented in "System Design: Presigned URL Access for POSIX Storage in AMS.pdf".

## Architecture Components

The complete system consists of three components:

1. **Issuer/Presigner Service** - Generates JWT tokens after authentication and authorization
2. **Gateway/Streamer Service** - Validates tokens and streams files
3. **AMS Storage Agent (PosixStorageAgent)** - Integration layer that calls presigner service

## Implementation Phases

### Phase 1: Basic POSIX Storage Agent ✅ **COMPLETE**

**Status**: Implemented and tested (19/19 tests passing)

**What's Done**:
- ✅ PosixStorageAgent class with file tree loading
- ✅ Path validation and security (prevents directory traversal)
- ✅ Regex-based resource matching (like S3 agent)
- ✅ Placeholder URL generation for read/write operations
- ✅ Comprehensive test suite (tests/test_posix_agent.py)

**Files Modified**:
- `core/connectivity/agents/posix_agent.py` - Complete rewrite
- `tests/test_posix_agent.py` - New test file

**Key Features**:
- File tree built from POSIX filesystem using `os.walk()`
- Security: Path validation prevents directory traversal attacks
- Regex matching: Full support for pattern-based file matching
- Placeholder URLs: `http://{gateway_url}/{path}?method={read|write}&ttl={seconds}`

**Configuration**:
```python
{
    "flavour": "posix",
    "instance_url": "http://gateway.local:9000",  # Future: Gateway service URL
    "root_path": "/path/to/storage/root"  # Absolute path to storage directory
}
```

**Testing**:
```bash
docker exec ams-backend-dev python -m pytest tests/test_posix_agent.py -v
```

---

### Phase 2: Issuer/Presigner Service (Next)

**Goal**: Create a separate microservice that issues JWT tokens for file access.

**Microservice Design**:
- Separate FastAPI application (similar to backend structure)
- Runs independently (separate Docker container)
- Communicates with Keycloak for authentication
- Communicates with AMS backend for authorization (via Casbin)

**Implementation Tasks**:

1. **Service Structure**:
   ```
   backend/services/issuer/
   ├── server.py              # FastAPI app entry point
   ├── api/
   │   └── v1/
   │       └── presign.py     # /v1/presign endpoint
   ├── auth/
   │   ├── keycloak.py        # OIDC token validation
   │   └── casbin_client.py   # Policy check via AMS API
   ├── jwt/
   │   ├── signer.py          # JWT signing with RS256
   │   └── jwks.py            # JWKS endpoint
   └── config.py              # Configuration
   ```

2. **API Endpoint**: `POST /v1/presign`

   **Request**:
   ```json
   {
     "path": "folder/file.txt",
     "op": "read",
     "ttl": 3600,
     "bundle": "file"  // or "manifest" or "zip"
   }
   ```

   **Response**:
   ```json
   {
     "token": "eyJhbGci...",  // JWT token
     "expires_at": "2025-10-08T12:34:56Z",
     "download_url": "http://gateway.local:9000/download?token=eyJhbGci..."
   }
   ```

3. **JWT Token Claims**:
   ```json
   {
     "path": "folder/file.txt",      // Resource path
     "op": "read",                    // Operation
     "exp": 1728394496,               // Expiration timestamp
     "iss": "ams-posix-issuer",       // Issuer
     "sub": "user-uuid",              // User UUID from Keycloak
     "bundle": "file",                // Download type
     "jti": "unique-token-id",        // Token ID (for replay prevention)
     "aud": "ams-posix-gateway",      // Audience (gateway service)
     "cip": "192.168.1.100"           // Client IP (optional pinning)
   }
   ```

4. **Authentication Flow**:
   - Client sends OIDC access token from Keycloak in `Authorization: Bearer` header
   - Issuer validates token with Keycloak (JWKS validation)
   - Extract user UUID from token

5. **Authorization Flow**:
   - Call AMS backend API to check Casbin policy
   - Endpoint: `POST /api/internal/validate-policy`
   - Request: `{"user_uuid": "...", "instance_uuid": "...", "resource": "...", "action": "read"}`
   - Response: `{"allowed": true/false}`

6. **JWT Signing**:
   - Generate RSA key pair on startup (or load from secrets)
   - Sign tokens with RS256 algorithm
   - Publish public key via JWKS endpoint: `GET /.well-known/jwks.json`

7. **Docker Configuration**:
   ```yaml
   # docker-compose.issuer.yml
   services:
     issuer:
       build: services/issuer
       container_name: ams-issuer
       environment:
         KEYCLOAK_DOMAIN: http://keycloak.local:8080
         KEYCLOAK_REALM: ams-portal
         AMS_BACKEND_URL: http://backend.local:8000
         GATEWAY_URL: http://gateway.local:9000
         JWT_PRIVATE_KEY_FILE: /run/secrets/jwt_private_key
         LOG_LEVEL: INFO
       ports: ["8001:8001"]
       extra_hosts:
         - "keycloak.local:host-gateway"
         - "backend.local:host-gateway"
   ```

**Testing Strategy**:
- Unit tests for JWT generation and signing
- Integration tests for Keycloak authentication
- Integration tests for Casbin authorization
- End-to-end tests for `/v1/presign` endpoint

---

### Phase 3: Gateway/Streamer Service

**Goal**: Create a service that validates tokens and streams files.

**Microservice Design**:
- Separate FastAPI application
- Validates JWT tokens from Issuer
- Streams files with HTTP Range support
- Generates JSON manifests and ZIP archives

**Implementation Tasks**:

1. **Service Structure**:
   ```
   backend/services/gateway/
   ├── server.py              # FastAPI app entry point
   ├── api/
   │   └── download.py        # /download endpoint
   ├── auth/
   │   ├── jwt_validator.py   # JWT validation via JWKS
   │   └── redis_jti.py       # Token replay prevention
   ├── streaming/
   │   ├── file_stream.py     # Single file streaming
   │   ├── manifest.py        # JSON manifest generation
   │   └── zip_stream.py      # On-the-fly ZIP compression
   └── config.py
   ```

2. **API Endpoint**: `GET /download?token={jwt}`

   **Response Types**:
   - **Single file** (`bundle=file`): Stream file with HTTP Range support
   - **Manifest** (`bundle=manifest`): JSON list of files in folder
   - **ZIP** (`bundle=zip`): Streamed ZIP archive of folder

3. **JWT Validation**:
   - Fetch JWKS from Issuer: `GET http://issuer.local:8001/.well-known/jwks.json`
   - Validate token signature using public key
   - Check expiration (`exp` claim)
   - Check audience (`aud` claim must be "ams-posix-gateway")
   - Validate token hasn't been used (check `jti` in Redis)

4. **Token Replay Prevention**:
   - Store `jti` claim in Redis with TTL matching token expiration
   - Before serving file, check if `jti` exists in Redis
   - If exists, reject (token already used)
   - If not exists, store `jti` and serve file

5. **File Streaming**:
   - **Single file**: Use `FileResponse` with HTTP Range support
   - **Manifest**: Generate JSON list recursively from folder
   - **ZIP**: Use `zipstream` library for streaming compression

6. **Security**:
   - Validate path is within storage root (prevent traversal)
   - Optional: Validate client IP matches `cip` claim
   - Log all access attempts

**Testing Strategy**:
- Unit tests for JWT validation
- Unit tests for jti replay prevention
- Integration tests for file streaming
- Integration tests for ZIP generation
- Performance tests for large file streaming

---

### Phase 4: Integration & End-to-End Testing

**Goal**: Connect all components and test the complete flow.

**Implementation Tasks**:

1. **Update PosixStorageAgent**:

   Replace placeholder URL generation with actual Issuer calls:

   ```python
   def generate_access_link(self, resource: str, method: str, ttl: int):
       """Call Issuer service to generate presigned JWT tokens."""

       # Build presign request
       payload = {
           "path": resource,
           "op": method,
           "ttl": ttl,
           "bundle": "file"  # or determine based on resource type
       }

       # Call Issuer service
       response = requests.post(
           f"{self.issuer_url}/v1/presign",
           json=payload,
           headers={"Authorization": f"Bearer {self.access_token}"},
           timeout=5
       )

       if response.status_code != 200:
           raise ValueError(f"Presign failed: {response.text}")

       data = response.json()
       return [data["download_url"]], [resource]
   ```

2. **Configuration Updates**:

   Add Issuer URL to PosixStorageAgent config:
   ```python
   CONFIG = {
       "root_path": str,
       "issuer_url": str  # e.g., "http://issuer.local:8001"
   }
   ```

3. **Docker Compose Integration**:

   Update README with full startup:
   ```bash
   # 1. Start Keycloak
   docker compose -p ams-keycloak -f docker-compose.keycloak.yml up -d

   # 2. Start Backend
   docker compose -p ams-backend -f docker-compose.backend.yml up -d

   # 3. Start Issuer
   docker compose -p ams-issuer -f docker-compose.issuer.yml up -d

   # 4. Start Gateway
   docker compose -p ams-gateway -f docker-compose.gateway.yml up -d

   # 5. Start Frontend
   docker compose -p ams-frontend -f docker-compose.frontend.yml up -d
   ```

4. **End-to-End Testing**:
   - User authenticates via Keycloak
   - Frontend requests file from backend
   - Backend calls PosixStorageAgent.generate_access_link()
   - Agent calls Issuer to get JWT token
   - Issuer validates auth and checks policy
   - Issuer returns JWT token
   - Frontend uses token to download from Gateway
   - Gateway validates token and streams file

**Testing Strategy**:
- Integration tests across all services
- Performance tests for high-volume downloads
- Security tests for token validation and replay attacks
- Stress tests for concurrent downloads

---

## Current Status

**Phase 1**: ✅ Complete (19/19 tests passing)

**Next Steps**:
1. Review Phase 1 implementation
2. Begin Phase 2: Issuer service skeleton
3. Implement JWT signing and JWKS endpoint
4. Implement Keycloak authentication
5. Implement Casbin policy checking

---

## Design Decisions

### Microservices vs. Monolithic

**Decision**: Use separate microservices for Issuer and Gateway

**Rationale**:
- Mirrors the S3 agent's external dependency pattern (boto3 calls external S3 service)
- Separation of concerns: auth/authz (Issuer) vs. file serving (Gateway)
- Independent scaling (Gateway may need more resources for streaming)
- Security: Gateway has no access to signing keys
- Can be deployed on separate hosts with different security zones

### JWT vs. Other Token Types

**Decision**: Use JWT with RS256 asymmetric signing

**Rationale**:
- Gateway can validate without calling Issuer (uses public key)
- Standard format with good library support
- Claims can embed all necessary metadata
- Supports expiration and audience validation
- Asymmetric keys prevent Gateway from forging tokens

### Redis for jti Tracking

**Decision**: Use Redis for token replay prevention

**Rationale**:
- Fast in-memory lookup for jti checking
- Built-in TTL matches token expiration
- Minimal latency impact on download performance
- Can be shared across multiple Gateway instances

---

## Files Overview

### Phase 1 (Complete)
- `core/connectivity/agents/posix_agent.py` - POSIX storage agent
- `tests/test_posix_agent.py` - Comprehensive test suite

### Phase 2 (Planned)
- `services/issuer/server.py` - Issuer service entry point
- `services/issuer/api/v1/presign.py` - Presign endpoint
- `services/issuer/auth/keycloak.py` - OIDC integration
- `services/issuer/auth/casbin_client.py` - Policy validation
- `services/issuer/jwt/signer.py` - JWT signing
- `services/issuer/jwt/jwks.py` - JWKS endpoint
- `docker-compose.issuer.yml` - Issuer Docker config
- `tests/test_issuer.py` - Issuer tests

### Phase 3 (Planned)
- `services/gateway/server.py` - Gateway service entry point
- `services/gateway/api/download.py` - Download endpoint
- `services/gateway/auth/jwt_validator.py` - Token validation
- `services/gateway/auth/redis_jti.py` - Replay prevention
- `services/gateway/streaming/file_stream.py` - File streaming
- `services/gateway/streaming/manifest.py` - Manifest generation
- `services/gateway/streaming/zip_stream.py` - ZIP streaming
- `docker-compose.gateway.yml` - Gateway Docker config
- `tests/test_gateway.py` - Gateway tests

### Phase 4 (Planned)
- Updates to `core/connectivity/agents/posix_agent.py` - Call Issuer
- Updates to `backend/README.md` - Full service startup docs
- `tests/test_posix_e2e.py` - End-to-end tests

---

## Security Considerations

1. **Path Traversal**: Phase 1 includes validation to prevent `../` attacks
2. **Token Signing**: RS256 asymmetric keys prevent token forgery
3. **Token Replay**: Redis jti tracking prevents token reuse
4. **Authentication**: Keycloak OIDC validates user identity
5. **Authorization**: Casbin policies enforce access control
6. **IP Pinning** (optional): `cip` claim can lock token to client IP
7. **Expiration**: All tokens have TTL (default: 3600s)
8. **Audience**: Gateway validates `aud` claim matches its identity

---

## Performance Considerations

1. **File Streaming**: Use chunked transfer encoding for large files
2. **HTTP Range**: Support partial content requests (206 responses)
3. **ZIP Streaming**: Use `zipstream` to avoid loading entire folder in memory
4. **JWKS Caching**: Cache Issuer public keys with short TTL
5. **Redis**: Use connection pooling for jti checks
6. **Async I/O**: Use FastAPI async endpoints where possible

---

## Future Enhancements

1. **Write Operations**: Implement presigned PUT for file uploads
2. **Multipart Uploads**: Support large file uploads in chunks
3. **Batch Presigning**: Generate multiple tokens in single request
4. **Token Refresh**: Allow token renewal before expiration
5. **Audit Logging**: Track all downloads with user/resource/timestamp
6. **Metrics**: Prometheus metrics for download volume, latency, errors
7. **CDN Integration**: Add caching layer for frequently accessed files
