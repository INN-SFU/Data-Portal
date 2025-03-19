import base64
import os
import dotenv
import pathlib

from cryptography.fernet import Fernet

def _generate_secrets():
    print('Updating secrets...')
    secrets = {
        "UID_KEY_SECRET": os.urandom(32),
        "JWT_TOKEN_SECRET": os.urandom(32),
        "ARBUTUS_AGENT_ACCESS_KEY_SECRET": Fernet.generate_key()
    }
    settings_directory = pathlib.Path(__file__).parent.resolve()
    for secret in secrets.keys():
        dotenv.set_key(os.path.join(settings_directory, '.secrets'), secret,
                       base64.b64encode(secrets[secret]).decode('utf-8'))

    # Reload secrets from .secrets file
    dotenv.load_dotenv(os.path.join(settings_directory, '.secrets'), override=True)