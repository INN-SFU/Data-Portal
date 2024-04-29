import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

secrets = {
    "UID_SECRET": ChaCha20Poly1305.generate_key(),
    "UID_NONCE": os.urandom(12),
    "UID_ASSOCIATED_DATA": os.urandom(12),
    "PASS_SECRET": os.urandom(32),
    "ACCESS_TOKEN_SECRET": os.urandom(32),
}

with open('.env', 'w') as f:
    for secret in secrets.keys():
        f.write(f"{secret}={base64.b64encode(secrets[secret]).decode('utf-8')}\n")
f.close()
