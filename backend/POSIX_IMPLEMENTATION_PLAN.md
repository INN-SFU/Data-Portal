# POSIX Storage System - Implementation Roadmap

## Overview

This document provides a high-level roadmap for implementing presigned URL support for POSIX storage in the AMS system. The implementation follows the system design documented in "System Design: Presigned URL Access for POSIX Storage in AMS.pdf".

## Architecture Components

The complete system consists of three components:

1. **PosixStorageAgent** (Backend) - Storage agent that calls Issuer for tokens
2. **Storage Issuer Service** - Generates JWT tokens (standalone microservice)
3. **Storage Gateway Service** - Validates tokens and streams files (standalone microservice)

## System Flow

```
User → AMS Backend (auth + policy check)
         ↓
      Backend → PosixStorageAgent → Storage Issuer
                                        ↓
                                    JWT token
                                        ↓
                                  User gets token
                                        ↓
                                  Storage Gateway (validates + streams file)
```

## Implementation Phases

### Phase 1: Basic POSIX Storage Agent ✅ **COMPLETE**

**Status**: Implemented and tested (19/19 tests passing)

**What's Done**:
- ✅ PosixStorageAgent class with file tree loading
- ✅ Path validation and security (prevents directory traversal)
- ✅ Regex-based resource matching (like S3 agent)
- ✅ Placeholder URL generation for read/write operations
- ✅ Comprehensive test suite

**Files**:
- `backend/core/connectivity/agents/posix_agent.py`
- `backend/tests/test_posix_agent.py`

**Configuration**:
```python
{
    "flavour": "posix",
    "instance_url": "http://gateway.local:9000",
    "root_path": "/path/to/storage/root"
}
```

**Testing**:
```bash
docker exec ams-backend-dev python -m pytest tests/test_posix_agent.py -v
```

---

### Phase 2: Storage Issuer Service ✅ **COMPLETE**

**Status**: Implemented, tested, and documented

**What's Done**:
- ✅ FastAPI microservice for JWT token generation
- ✅ RS256 asymmetric signing with RSA keys
- ✅ JWKS endpoint for public key distribution
- ✅ /v1/presign API endpoint with API key auth
- ✅ Docker containerization
- ✅ Comprehensive documentation

**Location**: `storage-issuer/` (root level, separate from backend)

**Documentation**:
- [storage-issuer/README.md](../../storage-issuer/README.md) - Usage and API reference
- [storage-issuer/ARCHITECTURE.md](../../storage-issuer/ARCHITECTURE.md) - Design details

**Key Endpoints**:
- `POST /v1/presign` - Generate JWT token (requires API key)
- `GET /.well-known/jwks.json` - Public key distribution
- `GET /v1/health` - Health check

**Deployment**:
```bash
docker compose -p ams-storage-issuer -f storage-issuer/docker-compose.yml up -d
```

**Testing**:
```bash
# Test presign endpoint
curl -X POST http://localhost:8001/v1/presign \
  -H "X-API-Key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{"user_uuid":"test","instance_uuid":"inst","path":"file.txt","op":"read","ttl":3600}'

# Test JWKS
curl http://localhost:8001/.well-known/jwks.json
```

---

### Phase 3: Storage Gateway Service (In Progress)

**Goal**: Create service that validates tokens and streams files from POSIX filesystem.

**Location**: `storage-gateway/` (root level, separate service)

**Key Features**:
- JWT token validation using Issuer's JWKS
- Single-use token enforcement (jti tracking in Redis)
- File streaming with HTTP Range support
- JSON manifest generation for folders
- On-the-fly ZIP compression for folder downloads

**Service Structure**:
```
storage-gateway/
├── server.py              # FastAPI app entry point
├── api/
│   └── download.py        # GET /download?token={jwt}
├── auth/
│   ├── jwt_validator.py   # Token validation via JWKS
│   └── jti_tracker.py     # Redis-based replay prevention
├── streaming/
│   ├── file_stream.py     # Single file streaming
│   ├── manifest.py        # JSON manifest generation
│   └── zip_stream.py      # On-the-fly ZIP compression
├── config.py
├── Dockerfile
├── docker-compose.yml
└── README.md
```

**API Endpoint**: `GET /download?token={jwt}`

**Response Types**:
- **Single file** (`bundle=file`): Stream file with HTTP Range support
- **Manifest** (`bundle=manifest`): JSON list of files in folder
- **ZIP** (`bundle=zip`): Streamed ZIP archive of folder

**Token Validation Flow**:
1. Extract JWT from query parameter
2. Fetch JWKS from Issuer (cached)
3. Validate token signature
4. Check expiration (`exp` claim)
5. Check audience (`aud` claim)
6. Check jti not in Redis (replay prevention)
7. Validate path matches requested resource
8. Store jti in Redis with TTL
9. Stream file from POSIX filesystem

**Security**:
- Path validation (prevent directory traversal)
- Single-use enforcement (Redis jti tracking)
- IP pinning validation (optional `cip` claim)
- Operation validation (read vs write)

**Dependencies**:
- Redis for jti tracking
- Access to POSIX filesystem (root_path)

---

### Phase 4: Integration & End-to-End Testing (Planned)

**Goal**: Connect all components and test complete flow.

**Deployment**: All services run in Docker on development machine

**Implementation Tasks**:

1. **Update PosixStorageAgent**:
   - Replace placeholder URL generation
   - Call Storage Issuer's `/v1/presign` endpoint
   - Pass user context and approved resource path

   ```python
   def generate_access_link(self, resource: str, method: str, ttl: int):
       # Call Issuer service
       response = requests.post(
           f"{self.issuer_url}/v1/presign",
           headers={"X-API-Key": self.api_key},
           json={
               "user_uuid": self.user_uuid,
               "instance_uuid": self.instance_uuid,
               "path": resource,
               "op": method,
               "ttl": ttl
           }
       )
       data = response.json()
       return [data["download_url"]], [resource]
   ```

2. **Configuration Updates**:
   - Add Issuer URL to PosixStorageAgent config
   - Add Issuer API key to environment
   - Configure Gateway URL for download links

3. **Docker Compose Integration**:
   ```bash
   # 1. Start Keycloak
   docker compose -p ams-keycloak -f backend/docker-compose.keycloak.yml up -d

   # 2. Start Backend
   docker compose -p ams-backend -f backend/docker-compose.backend.yml up -d

   # 3. Start Storage Issuer
   docker compose -p ams-storage-issuer -f storage-issuer/docker-compose.yml up -d

   # 4. Start Storage Gateway
   docker compose -p ams-storage-gateway -f storage-gateway/docker-compose.yml up -d

   # 5. Start Frontend
   docker compose -p ams-frontend -f frontend/docker-compose.frontend.yml up -d
   ```

4. **End-to-End Testing**:
   - User authenticates via Keycloak
   - Frontend requests file from Backend
   - Backend calls PosixStorageAgent.generate_access_link()
   - Agent calls Storage Issuer to get JWT token
   - Issuer validates (via Backend's prior policy check) and returns JWT
   - Frontend uses token to download from Gateway
   - Gateway validates token and streams file

**Testing Strategy**:
- Integration tests across all services
- Performance tests for high-volume downloads
- Security tests for token validation and replay attacks
- Stress tests for concurrent downloads

---

### Phase 5: Production Deployment with Service Separation (Future)

**Goal**: Enable production deployment with services on separate hosts.

**Deployment**: Distributed deployment for security and scalability

**Architecture**:
```
Application Server (backend.domain.com):
├── Keycloak (OIDC provider)
├── AMS Backend (API, policy management)
└── Storage Issuer (JWT token generation)
    ├── Has: Private signing key
    ├── Connects to: Keycloak, AMS Backend
    ├── Does NOT have: Filesystem access

Storage Server(s) (storage1.domain.com, storage2.domain.com):
├── Storage Gateway (file streaming)
│   ├── Has: Public validation key, filesystem access
│   ├── Connects to: Storage Issuer (for JWKS), Redis (for jti)
│   ├── Does NOT have: Private signing key
└── POSIX Storage (/storage/data/)
```

**Implementation Tasks**:

1. **Network Security**:
   - Configure TLS for all service-to-service communication
   - Implement mTLS between Issuer and Gateway (optional)
   - Firewall rules: Gateway only accepts requests from public internet
   - Issuer only accepts requests from AMS Backend

2. **Configuration Updates**:
   - Environment-based service discovery
   - Support for multiple Gateway instances (load balancing)
   - Issuer URL configuration per storage instance
   - Gateway validates Issuer's JWKS URL

3. **Key Management**:
   - Secure key generation and rotation for RS256 keys
   - Store private key in secrets management system (HashiCorp Vault)
   - Gateway fetches public key from Issuer's JWKS endpoint
   - Support for key rotation without downtime

4. **Redis Configuration**:
   - Shared Redis instance for jti tracking across multiple Gateways
   - Redis clustering for high availability
   - Network access from all Gateway instances

5. **Monitoring & Logging**:
   - Centralized logging for all services
   - Metrics for token issuance rate, download volume, errors
   - Alerts for failed auth/authz, suspicious access patterns

6. **PosixStorageAgent Updates**:
   ```python
   CONFIG = {
       "root_path": str,           # Only used by Gateway
       "issuer_url": str,          # Issuer service URL
       "gateway_url": str,         # Gateway service URL (different from issuer)
       "instance_uuid": str,       # For policy validation
   }
   ```

7. **Deployment Scripts**:
   - Ansible/Terraform scripts for multi-host deployment
   - Health checks for all services
   - Automated certificate management (Let's Encrypt)

**Security Benefits**:
- **Isolation**: Compromise of Gateway cannot forge tokens
- **Least Privilege**: Gateway only has read access to storage
- **Defense in Depth**: Multiple authentication/authorization layers
- **Audit Trail**: Centralized logging of all access

**Scalability**:
- Multiple Gateway instances for horizontal scaling
- Gateway instances can be added/removed dynamically
- Load balancing across storage servers
- Independent scaling of Issuer and Gateway

**Migration Path from Phase 4**:
1. Deploy Issuer on application server
2. Deploy Gateway on storage server with filesystem mount
3. Update PosixStorageAgent configuration with new URLs
4. Test end-to-end flow
5. Migrate DNS/load balancers
6. Decommission old single-host deployment

---

## Current Status

**Phase 1**: ✅ Complete (19/19 tests passing)
**Phase 2**: ✅ Complete (tested and documented)
**Phase 3**: 🔄 In Progress (Gateway service)
**Phase 4**: ⏳ Planned (Integration)
**Phase 5**: ⏳ Planned (Production deployment)

---

## Design Decisions

### Why Separate Services?

**Storage Issuer** and **Storage Gateway** are separate microservices (not embedded in Backend):

**Security**:
- Private key isolated from public-facing services
- Gateway compromise cannot forge tokens
- Principle of least privilege

**Scalability**:
- Token issuance and file streaming scale independently
- Can deploy multiple Gateways across storage servers
- Issuer can serve multiple AMS instances

**Reusability**:
- Storage Issuer is generic (works with any storage type)
- Same Issuer can serve POSIX, NFS, WebDAV, etc.
- Clean separation of concerns

### Why JWT with RS256?

**Asymmetric Signing**:
- Gateway validates without calling Issuer (fast)
- Gateway cannot forge tokens (no private key)
- Standard protocol (OIDC, OAuth 2.0)

**vs. Symmetric (HMAC)**:
- Shared secret = both services can forge tokens
- Less secure if Gateway compromised

### Why Not Use This for S3?

S3 already has native presigned URLs via AWS SDK:

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

---

## Security Considerations

1. **Path Traversal**: Phase 1 includes validation to prevent `../` attacks
2. **Token Signing**: RS256 asymmetric keys prevent token forgery
3. **Token Replay**: Redis jti tracking prevents token reuse
4. **Authentication**: Keycloak OIDC validates user identity (in Backend)
5. **Authorization**: Casbin policies enforce access control (in Backend)
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

---

## Documentation

### Service Documentation
- [Storage Issuer README](../../storage-issuer/README.md) - Usage and API reference
- [Storage Issuer ARCHITECTURE](../../storage-issuer/ARCHITECTURE.md) - Design details and decisions
- Storage Gateway README (Phase 3)
- Storage Gateway ARCHITECTURE (Phase 3)

### Design Documents
- System Design PDF: `System Design: Presigned URL Access for POSIX Storage in AMS.pdf`
- This roadmap: `backend/POSIX_IMPLEMENTATION_PLAN.md`

### Code
- PosixStorageAgent: `backend/core/connectivity/agents/posix_agent.py`
- Storage Issuer: `storage-issuer/`
- Storage Gateway: `storage-gateway/` (Phase 3)

---

## Quick Start (Current State - Phase 2 Complete)

```bash
# 1. Start Keycloak
cd backend
docker compose -p ams-keycloak -f docker-compose.keycloak.yml up -d

# 2. Start Backend
docker compose -p ams-backend -f docker-compose.backend.yml up -d

# 3. Start Storage Issuer
cd ../storage-issuer
docker compose -p ams-storage-issuer up -d

# 4. Test Storage Issuer
curl http://localhost:8001/.well-known/jwks.json
curl -X POST http://localhost:8001/v1/presign \
  -H "X-API-Key: dev-api-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{"user_uuid":"test","instance_uuid":"inst","path":"file.txt","op":"read","ttl":3600}'

# 5. Next: Implement Storage Gateway (Phase 3)
```
