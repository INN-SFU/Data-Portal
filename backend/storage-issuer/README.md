# AMS Storage Issuer Service

Generic JWT token issuer for storage access with presigned URLs.

## Overview

The Storage Issuer is a microservice that generates JWT tokens for secure, time-limited access to storage resources. It works with any storage type that requires JWT-based authentication (POSIX, NFS, WebDAV, etc.).

**Key Features:**
- RS256 asymmetric JWT signing
- JWKS endpoint for public key distribution
- API key authentication for internal services
- Time-limited, single-use tokens
- Path and operation locking

## Architecture

```
AMS Backend (validates user auth & policies)
    ↓ (calls with API key)
Storage Issuer (signs JWT tokens)
    ↓ (returns token)
User
    ↓ (presents token)
Storage Gateway (validates & serves files)
```

## API Endpoints

### POST /v1/presign
Generate a presigned token.

**Authentication:** X-API-Key header

**Request:**
```json
{
  "user_uuid": "abc-123",
  "instance_uuid": "xyz-456",
  "path": "folder/file.txt",
  "op": "read",
  "ttl": 3600,
  "bundle": "file",
  "client_ip": "192.168.1.100"
}
```

**Response:**
```json
{
  "token": "eyJhbGci...",
  "expires_at": "2025-10-08T12:34:56Z",
  "download_url": "http://gateway.local:9000/download?token=eyJhbGci..."
}
```

### GET /.well-known/jwks.json
Get public key for token validation (used by Gateway).

**No authentication required** (public endpoint).

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ISSUER_HOST` | `0.0.0.0` | Service bind address |
| `ISSUER_PORT` | `8001` | Service port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `JWT_ISSUER` | `ams-storage-issuer` | JWT issuer claim |
| `JWT_AUDIENCE` | `ams-storage-gateway` | JWT audience claim |
| `JWT_PRIVATE_KEY_FILE` | `/run/secrets/jwt_private_key` | Path to RSA private key |
| `GATEWAY_URL` | `http://gateway.local:9000` | Gateway service URL |
| `ISSUER_API_KEY` | (required) | API key for authentication |

## Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ISSUER_API_KEY=dev-key
export GATEWAY_URL=http://localhost:9000

# Run server
python server.py
```

### Running with Docker

```bash
# Build and start
docker compose up -d --build

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## JWT Token Format

**Claims:**
```json
{
  "iss": "ams-storage-issuer",       // Issuer
  "aud": "ams-storage-gateway",      // Audience
  "sub": "user-uuid",                 // User UUID
  "exp": 1728394496,                  // Expiration (Unix timestamp)
  "iat": 1728390896,                  // Issued at
  "jti": "unique-id",                 // Token ID (for replay prevention)
  "path": "folder/file.txt",          // Resource path (locked)
  "op": "read",                       // Operation (locked)
  "bundle": "file",                   // Download type
  "cip": "192.168.1.100",            // Client IP (optional)
  "iid": "instance-uuid"              // Instance UUID (optional)
}
```

## Security

- **RS256 signing**: Asymmetric keys prevent token forgery
- **Private key**: Never leaves Issuer service
- **Public key**: Distributed via JWKS endpoint
- **API key auth**: Only AMS Backend can request tokens
- **Time-limited**: Tokens expire (default 1 hour)
- **Single-use**: Gateway enforces via jti tracking in Redis
- **Path locked**: Token only valid for specific resource
- **Operation locked**: Separate tokens for read vs write

## Integration with AMS Backend

The backend automatically manages issuer credentials and injects them into POSIX storage instances:

**Automatic Credential Management:**
- Backend generates/loads API key from `/run/secrets/storage_issuer_api_key`
- Issuer URL configured via `STORAGE_ISSUER_URL` environment variable
- Credentials automatically injected when creating POSIX instances
- Users only provide Gateway URL (simplified UX)

**Backend to Issuer Communication:**
```python
# Backend calls Issuer after validating user auth/authz
import requests

response = requests.post(
    f"{issuer_url}/v1/presign",  # http://storage-issuer:8001 (Docker DNS)
    headers={"X-API-Key": api_key},  # From /run/secrets
    json={
        "user_uuid": user_uuid,
        "instance_uuid": instance_uuid,
        "path": "data/file.txt",
        "op": "read",
        "ttl": 3600
    }
)

token_data = response.json()
download_url = token_data["download_url"]  # http://storage-gateway:9000/api/download?token=...
```

**User Experience:**
- Users create POSIX instances with only `instance_url` (Gateway URL)
- Backend handles all issuer configuration internally
- Improved security (credentials not exposed to users)

## Deployment

### Development (Docker with Shared Network)

**Prerequisites:**
```bash
# Create shared network for service discovery
docker network create ams-network
```

**Deployment:**
```bash
# 1. Start Backend (sets up issuer credentials)
cd backend
docker compose -p ams-backend -f docker-compose.backend.yml up -d

# 2. Start Storage Issuer
cd storage-issuer
docker compose -p ams-storage-issuer up -d --build

# 3. Start Storage Gateway
cd ../../storage-gateway
docker compose -p ams-storage-gateway up -d --build
```

**Service Communication via Docker DNS:**
- Backend → Issuer: `http://storage-issuer:8001`
- Gateway → Issuer JWKS: `http://storage-issuer:8001/.well-known/jwks.json`
- Users → Gateway: `http://localhost:9000` (or custom Gateway URL)

### Production (Distributed Deployment)

Deploy alongside AMS Backend (not on storage server):

**Architecture:**
```
Application Server:
├── AMS Backend (API + business logic)
└── Storage Issuer (JWT signing)
    ├── Has: Private signing key (sensitive)
    ├── Exposes: JWKS endpoint (public key)

Storage Server(s):
└── Storage Gateway (file streaming)
    ├── Has: Public key only (via JWKS)
    ├── Cannot: Forge tokens (no private key)
```

**Security Benefits:**
- Issuer has signing key (sensitive) on application server
- Gateway only has public key (less sensitive) on storage server
- If storage compromised, tokens can't be forged
- Principle of least privilege

## Health Check

```bash
curl http://localhost:8001/v1/health
```

## API Documentation

Interactive API docs available at:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc
