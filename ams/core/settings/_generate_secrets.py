import base64
import os
import dotenv
import pathlib

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305


def _generate_secrets():
    print('Updating secrets...')
    secrets = {
        "UID_SECRET": ChaCha20Poly1305.generate_key(),
        "PASS_SECRET": os.urandom(32),
        "ACCESS_TOKEN_SECRET": os.urandom(32),
    }
    settings_directory = pathlib.Path(__file__).parent.resolve()
    for secret in secrets.keys():
        dotenv.set_key(os.path.join(settings_directory, '.secrets'), secret,
                       base64.b64encode(secrets[secret]).decode('utf-8'))

    # Reload secrets from .secrets file
    dotenv.load_dotenv(os.path.join(settings_directory, '.secrets'), override=True)