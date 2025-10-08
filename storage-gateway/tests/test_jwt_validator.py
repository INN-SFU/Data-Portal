"""
Tests for JWT Validator

Tests token validation using mocked JWKS.
"""
import pytest
import jwt as pyjwt
from datetime import datetime, timezone, timedelta
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth.jwt_validator import JWTValidator, TokenValidationError


class TestJWTValidator:
    """Test JWT validator functionality."""

    @pytest.fixture
    def mock_signer(self):
        """Create a mock JWT signer for testing."""
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend

        # Generate test key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        return {
            "private_key": private_key,
            "public_key": private_key.public_key()
        }

    @pytest.fixture
    def mock_jwks_server(self, mock_signer, httpserver):
        """Mock JWKS endpoint."""
        from cryptography.hazmat.primitives import serialization

        # Get public key numbers
        public_numbers = mock_signer["public_key"].public_numbers()

        # Convert to base64url
        import base64

        def int_to_base64url(num):
            blen = (num.bit_length() + 7) // 8
            byt = num.to_bytes(blen, 'big')
            return base64.urlsafe_b64encode(byt).rstrip(b'=').decode('utf-8')

        n = int_to_base64url(public_numbers.n)
        e = int_to_base64url(public_numbers.e)

        jwks = {
            "keys": [{
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": "default",
                "n": n,
                "e": e
            }]
        }

        httpserver.expect_request("/.well-known/jwks.json").respond_with_json(jwks)
        return httpserver.url_for("/.well-known/jwks.json")

    def test_validate_token_success(self, mock_signer, mock_jwks_server):
        """Test successful token validation."""
        validator = JWTValidator(
            jwks_url=mock_jwks_server,
            audience="ams-storage-gateway",
            issuer="ams-storage-issuer"
        )

        # Create valid token
        now = datetime.now(timezone.utc)
        claims = {
            "iss": "ams-storage-issuer",
            "aud": "ams-storage-gateway",
            "sub": "user-123",
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": "test-jti-123",
            "path": "test/file.txt",
            "op": "read",
            "bundle": "file"
        }

        token = pyjwt.encode(claims, mock_signer["private_key"], algorithm="RS256")

        # Validate
        decoded = validator.validate_token(token)

        assert decoded["sub"] == "user-123"
        assert decoded["path"] == "test/file.txt"
        assert decoded["op"] == "read"

    def test_validate_expired_token_fails(self, mock_signer, mock_jwks_server):
        """Test that expired token is rejected."""
        validator = JWTValidator(
            jwks_url=mock_jwks_server,
            audience="ams-storage-gateway",
            issuer="ams-storage-issuer"
        )

        # Create expired token
        now = datetime.now(timezone.utc)
        claims = {
            "iss": "ams-storage-issuer",
            "aud": "ams-storage-gateway",
            "sub": "user-123",
            "exp": int((now - timedelta(hours=1)).timestamp()),  # Expired
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "jti": "test-jti-123",
            "path": "test/file.txt",
            "op": "read"
        }

        token = pyjwt.encode(claims, mock_signer["private_key"], algorithm="RS256")

        # Should fail
        with pytest.raises(TokenValidationError, match="expired"):
            validator.validate_token(token)

    def test_validate_wrong_audience_fails(self, mock_signer, mock_jwks_server):
        """Test that wrong audience is rejected."""
        validator = JWTValidator(
            jwks_url=mock_jwks_server,
            audience="ams-storage-gateway",
            issuer="ams-storage-issuer"
        )

        # Create token with wrong audience
        now = datetime.now(timezone.utc)
        claims = {
            "iss": "ams-storage-issuer",
            "aud": "wrong-audience",  # Wrong
            "sub": "user-123",
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": "test-jti-123",
            "path": "test/file.txt",
            "op": "read"
        }

        token = pyjwt.encode(claims, mock_signer["private_key"], algorithm="RS256")

        # Should fail
        with pytest.raises(TokenValidationError, match="audience"):
            validator.validate_token(token)

    def test_validate_missing_claims_fails(self, mock_signer, mock_jwks_server):
        """Test that missing required claims are rejected."""
        validator = JWTValidator(
            jwks_url=mock_jwks_server,
            audience="ams-storage-gateway",
            issuer="ams-storage-issuer"
        )

        # Create token missing 'path' claim
        now = datetime.now(timezone.utc)
        claims = {
            "iss": "ams-storage-issuer",
            "aud": "ams-storage-gateway",
            "sub": "user-123",
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": "test-jti-123",
            # Missing "path" and "op"
        }

        token = pyjwt.encode(claims, mock_signer["private_key"], algorithm="RS256")

        # Should fail
        with pytest.raises(TokenValidationError, match="Missing required claim"):
            validator.validate_token(token)

    def test_validate_client_ip_success(self, mock_signer, mock_jwks_server):
        """Test successful client IP validation."""
        validator = JWTValidator(
            jwks_url=mock_jwks_server,
            audience="ams-storage-gateway",
            issuer="ams-storage-issuer"
        )

        claims = {
            "cip": "192.168.1.100"
        }

        # Should not raise
        validator.validate_client_ip(claims, "192.168.1.100")

    def test_validate_client_ip_mismatch_fails(self, mock_signer, mock_jwks_server):
        """Test that IP mismatch is rejected."""
        validator = JWTValidator(
            jwks_url=mock_jwks_server,
            audience="ams-storage-gateway",
            issuer="ams-storage-issuer"
        )

        claims = {
            "cip": "192.168.1.100"
        }

        # Should fail
        with pytest.raises(TokenValidationError, match="IP mismatch"):
            validator.validate_client_ip(claims, "192.168.1.200")
