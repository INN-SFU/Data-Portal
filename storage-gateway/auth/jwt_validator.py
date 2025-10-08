"""
JWT Token Validator

Validates JWT tokens using the Issuer's JWKS endpoint.
Caches public keys for performance.
"""
import logging
import jwt
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from jwt import PyJWKClient
from jwt.exceptions import (
    InvalidTokenError,
    ExpiredSignatureError,
    InvalidSignatureError,
    InvalidAudienceError,
    DecodeError
)

logger = logging.getLogger('storage-gateway.auth.jwt_validator')


class TokenValidationError(Exception):
    """Base exception for token validation errors."""
    pass


class JWTValidator:
    """
    Validates JWT tokens using Issuer's JWKS endpoint.

    Features:
    - Fetches public keys from Issuer's JWKS endpoint
    - Caches keys for performance (configurable TTL)
    - Validates signature, expiration, audience
    - Extracts and validates claims
    """

    def __init__(
        self,
        jwks_url: str,
        audience: str,
        issuer: str,
        cache_ttl: int = 3600
    ):
        """
        Initialize JWT validator.

        :param jwks_url: URL to Issuer's JWKS endpoint (e.g., http://issuer:8001/.well-known/jwks.json)
        :param audience: Expected audience claim (e.g., "ams-storage-gateway")
        :param issuer: Expected issuer claim (e.g., "ams-storage-issuer")
        :param cache_ttl: JWKS cache TTL in seconds (default: 3600)
        """
        self.jwks_url = jwks_url
        self.audience = audience
        self.issuer = issuer

        # Initialize PyJWKClient for automatic JWKS fetching and caching
        self.jwks_client = PyJWKClient(
            jwks_url,
            cache_keys=True,
            max_cached_keys=16
        )

        logger.info(f"JWT Validator initialized: jwks_url={jwks_url}, audience={audience}, issuer={issuer}")

    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token and return claims.

        :param token: JWT token string
        :return: Decoded token claims
        :raises TokenValidationError: If validation fails
        """
        try:
            # Get signing key from JWKS (cached)
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            # Decode and validate token
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={
                    "require_exp": True,
                    "require_iat": True,
                    "require_jti": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                }
            )

            # Validate required custom claims
            self._validate_custom_claims(claims)

            logger.info(
                f"Token validated successfully",
                extra={
                    "sub": claims.get("sub"),
                    "jti": claims.get("jti"),
                    "path": claims.get("path"),
                    "op": claims.get("op")
                }
            )

            return claims

        except ExpiredSignatureError:
            logger.warning("Token validation failed: expired")
            raise TokenValidationError("Token has expired")

        except InvalidSignatureError:
            logger.error("Token validation failed: invalid signature")
            raise TokenValidationError("Invalid token signature")

        except InvalidAudienceError:
            logger.error(f"Token validation failed: invalid audience (expected: {self.audience})")
            raise TokenValidationError("Invalid token audience")

        except DecodeError as e:
            logger.error(f"Token validation failed: decode error - {e}")
            raise TokenValidationError(f"Invalid token format: {e}")

        except InvalidTokenError as e:
            logger.error(f"Token validation failed: {e}")
            raise TokenValidationError(f"Invalid token: {e}")

        except Exception as e:
            logger.error(f"Unexpected error during token validation: {e}")
            raise TokenValidationError(f"Token validation error: {e}")

    def _validate_custom_claims(self, claims: Dict[str, Any]) -> None:
        """
        Validate custom claims required for storage access.

        :param claims: Decoded token claims
        :raises TokenValidationError: If required claims missing or invalid
        """
        required_claims = ["path", "op", "sub", "jti"]

        for claim in required_claims:
            if claim not in claims:
                raise TokenValidationError(f"Missing required claim: {claim}")

        # Validate operation
        valid_operations = ["read", "write"]
        if claims["op"] not in valid_operations:
            raise TokenValidationError(f"Invalid operation: {claims['op']} (must be one of {valid_operations})")

        # Validate path (basic check - more thorough check in file streamer)
        if not claims["path"] or not isinstance(claims["path"], str):
            raise TokenValidationError("Invalid path claim")

        # Validate bundle if present
        if "bundle" in claims:
            valid_bundles = ["file", "manifest", "zip"]
            if claims["bundle"] not in valid_bundles:
                raise TokenValidationError(f"Invalid bundle type: {claims['bundle']}")

    def validate_client_ip(self, claims: Dict[str, Any], client_ip: str) -> None:
        """
        Validate client IP if token has IP pinning.

        :param claims: Decoded token claims
        :param client_ip: Client's IP address
        :raises TokenValidationError: If IP doesn't match
        """
        if "cip" in claims:
            if claims["cip"] != client_ip:
                logger.warning(
                    f"IP pinning validation failed",
                    extra={
                        "expected_ip": claims["cip"],
                        "actual_ip": client_ip,
                        "jti": claims.get("jti")
                    }
                )
                raise TokenValidationError(f"Client IP mismatch (token pinned to different IP)")

        logger.debug(f"Client IP validated: {client_ip}")

    def get_token_claims_unsafe(self, token: str) -> Dict[str, Any]:
        """
        Decode token without validation (for debugging/logging only).

        WARNING: Do not use for authorization decisions!

        :param token: JWT token string
        :return: Decoded claims (unverified)
        """
        try:
            claims = jwt.decode(token, options={"verify_signature": False})
            return claims
        except Exception as e:
            logger.debug(f"Failed to decode token (unsafe): {e}")
            return {}
