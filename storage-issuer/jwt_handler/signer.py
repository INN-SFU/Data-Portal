"""
JWT Token Signing Module

Handles JWT token generation with RS256 asymmetric signing.
Generates and manages RSA key pairs for token signing.
"""
import os
import jwt
import uuid
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from typing import Dict, Any, Optional

logger = logging.getLogger('issuer.jwt.signer')


class JWTSigner:
    """
    JWT token signer using RS256 algorithm.

    Manages RSA key pair and signs JWT tokens with configurable claims.
    """

    ALGORITHM = "RS256"
    DEFAULT_TTL = 3600  # 1 hour

    def __init__(self,
                 private_key_path: Optional[str] = None,
                 issuer: str = "ams-posix-issuer",
                 audience: str = "ams-posix-gateway"):
        """
        Initialize JWT signer.

        :param private_key_path: Path to RSA private key file (PEM format)
        :param issuer: JWT issuer claim (iss)
        :param audience: JWT audience claim (aud)
        """
        self.issuer = issuer
        self.audience = audience

        # Load or generate RSA key pair
        if private_key_path and Path(private_key_path).exists():
            logger.info(f"Loading private key from {private_key_path}")
            self.private_key = self._load_private_key(private_key_path)
        else:
            logger.warning("No private key found, generating new RSA key pair")
            self.private_key = self._generate_key_pair()

        # Extract public key
        self.public_key = self.private_key.public_key()

        logger.info(f"JWT signer initialized (issuer={issuer}, audience={audience})")

    def _generate_key_pair(self) -> rsa.RSAPrivateKey:
        """
        Generate a new RSA key pair.

        :return: RSA private key object
        """
        logger.info("Generating 2048-bit RSA key pair")
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        return private_key

    def _load_private_key(self, path: str) -> rsa.RSAPrivateKey:
        """
        Load RSA private key from PEM file.

        :param path: Path to private key file
        :return: RSA private key object
        """
        with open(path, 'rb') as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,  # Unencrypted key
                backend=default_backend()
            )
        return private_key

    def save_private_key(self, path: str):
        """
        Save private key to PEM file.

        :param path: Path to save private key
        """
        pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Ensure directory exists
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'wb') as f:
            f.write(pem)

        # Secure permissions (owner read/write only)
        os.chmod(path, 0o600)
        logger.info(f"Private key saved to {path}")

    def get_public_key_pem(self) -> str:
        """
        Get public key in PEM format.

        :return: Public key as PEM string
        """
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode('utf-8')

    def sign_token(self,
                   path: str,
                   operation: str,
                   subject: str,
                   ttl: int = DEFAULT_TTL,
                   bundle: str = "file",
                   client_ip: Optional[str] = None,
                   instance_uuid: Optional[str] = None) -> str:
        """
        Sign a JWT token for file access.

        :param path: Resource path (relative to storage root)
        :param operation: Operation type ("read" or "write")
        :param subject: User UUID (sub claim)
        :param ttl: Time-to-live in seconds
        :param bundle: Download bundle type ("file", "manifest", or "zip")
        :param client_ip: Optional client IP for pinning
        :param instance_uuid: Optional instance UUID for tracking
        :return: Signed JWT token string
        """
        now = datetime.now(timezone.utc)
        exp = now + timedelta(seconds=ttl)

        # Build claims
        claims: Dict[str, Any] = {
            # Standard claims
            "iss": self.issuer,           # Issuer
            "sub": subject,                # Subject (user UUID)
            "aud": self.audience,          # Audience (gateway service)
            "exp": int(exp.timestamp()),   # Expiration time
            "iat": int(now.timestamp()),   # Issued at
            "jti": str(uuid.uuid4()),      # JWT ID (for replay prevention)

            # Custom claims
            "path": path,                  # Resource path
            "op": operation,               # Operation (read/write)
            "bundle": bundle,              # Download type
        }

        # Optional claims
        if client_ip:
            claims["cip"] = client_ip      # Client IP (for IP pinning)
        if instance_uuid:
            claims["iid"] = instance_uuid  # Instance ID

        # Sign token
        token = jwt.encode(
            claims,
            self.private_key,
            algorithm=self.ALGORITHM
        )

        logger.info(f"Signed token: path={path}, op={operation}, sub={subject}, jti={claims['jti']}")
        return token

    def decode_token(self, token: str, verify: bool = True) -> Dict[str, Any]:
        """
        Decode and optionally verify a JWT token.
        Useful for testing and debugging.

        :param token: JWT token string
        :param verify: Whether to verify signature
        :return: Decoded claims dictionary
        :raises jwt.InvalidTokenError: If token is invalid or expired
        """
        if verify:
            decoded = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.ALGORITHM],
                audience=self.audience,
                issuer=self.issuer
            )
        else:
            decoded = jwt.decode(
                token,
                options={"verify_signature": False}
            )

        return decoded
