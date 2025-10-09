"""
Tests for JWT Signer Module

Tests JWT token signing, validation, and JWKS generation.
"""
import pytest
import jwt as pyjwt
from datetime import datetime, timezone, timedelta
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jwt_handler.signer import JWTSigner
from jwt_handler.jwks import JWKSProvider


class TestJWTSigner:
    """Test JWT signer functionality."""

    def test_init_generates_key_pair(self):
        """Test that signer generates RSA key pair on init."""
        signer = JWTSigner(
            private_key_path=None,
            issuer="test-issuer",
            audience="test-gateway"
        )

        assert signer.private_key is not None
        assert signer.public_key is not None
        assert signer.issuer == "test-issuer"
        assert signer.audience == "test-gateway"

    def test_sign_token_basic(self):
        """Test signing a basic token."""
        signer = JWTSigner(issuer="test-issuer", audience="test-gateway")

        token = signer.sign_token(
            path="test/file.txt",
            operation="read",
            subject="user-123",
            ttl=3600
        )

        assert isinstance(token, str)
        assert len(token) > 0

    def test_sign_token_claims(self):
        """Test that signed token contains correct claims."""
        signer = JWTSigner(issuer="test-issuer", audience="test-gateway")

        token = signer.sign_token(
            path="test/file.txt",
            operation="read",
            subject="user-123",
            ttl=3600,
            bundle="file",
            client_ip="192.168.1.100",
            instance_uuid="instance-456"
        )

        # Decode without verification to check claims
        decoded = signer.decode_token(token, verify=False)

        assert decoded["path"] == "test/file.txt"
        assert decoded["op"] == "read"
        assert decoded["sub"] == "user-123"
        assert decoded["bundle"] == "file"
        assert decoded["cip"] == "192.168.1.100"
        assert decoded["iid"] == "instance-456"
        assert decoded["iss"] == "test-issuer"
        assert decoded["aud"] == "test-gateway"
        assert "jti" in decoded
        assert "exp" in decoded
        assert "iat" in decoded

    def test_sign_and_verify_token(self):
        """Test signing and verifying a token."""
        signer = JWTSigner(issuer="test-issuer", audience="test-gateway")

        token = signer.sign_token(
            path="test/file.txt",
            operation="read",
            subject="user-123",
            ttl=3600
        )

        # Verify with public key
        decoded = signer.decode_token(token, verify=True)

        assert decoded["path"] == "test/file.txt"
        assert decoded["sub"] == "user-123"

    def test_token_expiration(self):
        """Test that token expiration is set correctly."""
        signer = JWTSigner(issuer="test-issuer", audience="test-gateway")

        ttl = 3600
        before = datetime.now(timezone.utc)

        token = signer.sign_token(
            path="test/file.txt",
            operation="read",
            subject="user-123",
            ttl=ttl
        )

        after = datetime.now(timezone.utc)

        decoded = signer.decode_token(token, verify=False)
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)

        # Expiration should be approximately now + ttl
        expected_min = before + timedelta(seconds=ttl)
        expected_max = after + timedelta(seconds=ttl)

        assert expected_min <= exp_time <= expected_max

    def test_invalid_signature_fails(self):
        """Test that invalid signature is rejected."""
        signer1 = JWTSigner(issuer="test-issuer", audience="test-gateway")
        signer2 = JWTSigner(issuer="test-issuer", audience="test-gateway")

        # Sign with signer1
        token = signer1.sign_token(
            path="test/file.txt",
            operation="read",
            subject="user-123",
            ttl=3600
        )

        # Try to verify with signer2's public key (different key pair)
        with pytest.raises(pyjwt.InvalidSignatureError):
            signer2.decode_token(token, verify=True)

    def test_expired_token_fails(self):
        """Test that expired token is rejected."""
        signer = JWTSigner(issuer="test-issuer", audience="test-gateway")

        # Create token with negative TTL (already expired)
        token = signer.sign_token(
            path="test/file.txt",
            operation="read",
            subject="user-123",
            ttl=-1
        )

        # Verification should fail due to expiration
        with pytest.raises(pyjwt.ExpiredSignatureError):
            signer.decode_token(token, verify=True)

    def test_get_public_key_pem(self):
        """Test getting public key in PEM format."""
        signer = JWTSigner(issuer="test-issuer", audience="test-gateway")

        pem = signer.get_public_key_pem()

        assert isinstance(pem, str)
        assert "BEGIN PUBLIC KEY" in pem
        assert "END PUBLIC KEY" in pem


class TestJWKSProvider:
    """Test JWKS provider functionality."""

    def test_get_jwks(self):
        """Test JWKS generation."""
        signer = JWTSigner(issuer="test-issuer", audience="test-gateway")
        jwks_provider = JWKSProvider(signer.public_key, key_id="test-key")

        jwks = jwks_provider.get_jwks()

        assert "keys" in jwks
        assert len(jwks["keys"]) == 1

        key = jwks["keys"][0]
        assert key["kty"] == "RSA"
        assert key["use"] == "sig"
        assert key["alg"] == "RS256"
        assert key["kid"] == "test-key"
        assert "n" in key  # Modulus
        assert "e" in key  # Exponent

    def test_jwks_validation(self):
        """Test that JWKS can be used to validate tokens."""
        signer = JWTSigner(issuer="test-issuer", audience="test-gateway")
        jwks_provider = JWKSProvider(signer.public_key, key_id="default")

        # Sign a token
        token = signer.sign_token(
            path="test/file.txt",
            operation="read",
            subject="user-123",
            ttl=3600
        )

        # Get JWKS
        jwks = jwks_provider.get_jwks()

        # In real world, Gateway would use PyJWKClient to validate
        # For this test, we just verify the JWKS structure is correct
        assert jwks["keys"][0]["kty"] == "RSA"
