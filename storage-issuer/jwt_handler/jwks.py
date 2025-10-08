"""
JWKS (JSON Web Key Set) Module

Provides JWKS endpoint for publishing public keys.
Gateway services use this to validate JWT tokens.
"""
import logging
from typing import Dict, Any
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import base64

logger = logging.getLogger('issuer.jwt.jwks')


class JWKSProvider:
    """
    JWKS provider for publishing public keys.

    Converts RSA public key to JWK (JSON Web Key) format
    for use in JWKS endpoint.
    """

    def __init__(self, public_key: rsa.RSAPublicKey, key_id: str = "default"):
        """
        Initialize JWKS provider.

        :param public_key: RSA public key object
        :param key_id: Key identifier (kid)
        """
        self.public_key = public_key
        self.key_id = key_id

    def get_jwks(self) -> Dict[str, Any]:
        """
        Get JWKS (JSON Web Key Set) representation.

        Returns a JWK Set containing the public key in JWK format.
        Gateway services use this to validate JWT signatures.

        :return: JWKS dictionary
        """
        # Extract RSA public key components
        public_numbers = self.public_key.public_numbers()

        # Convert to base64url encoding (without padding)
        n = self._int_to_base64url(public_numbers.n)
        e = self._int_to_base64url(public_numbers.e)

        # Build JWK (JSON Web Key)
        jwk = {
            "kty": "RSA",           # Key type
            "use": "sig",           # Key use (signature)
            "alg": "RS256",         # Algorithm
            "kid": self.key_id,     # Key ID
            "n": n,                 # Modulus
            "e": e,                 # Exponent
        }

        # JWKS is a set of keys
        jwks = {
            "keys": [jwk]
        }

        logger.debug(f"Generated JWKS for key_id={self.key_id}")
        return jwks

    def _int_to_base64url(self, value: int) -> str:
        """
        Convert integer to base64url encoding.

        :param value: Integer value
        :return: Base64url encoded string (without padding)
        """
        # Convert to bytes (big-endian)
        value_bytes = value.to_bytes(
            (value.bit_length() + 7) // 8,
            byteorder='big'
        )

        # Base64url encode (no padding)
        encoded = base64.urlsafe_b64encode(value_bytes).decode('utf-8')
        return encoded.rstrip('=')

    def get_public_key_pem(self) -> str:
        """
        Get public key in PEM format.

        Convenience method for debugging and testing.

        :return: Public key as PEM string
        """
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode('utf-8')
