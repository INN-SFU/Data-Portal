import secrets
import os
import jwt
import time
import base64

from hashlib import blake2b
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

uid_secret = ChaCha20Poly1305.generate_key()
uid_nonce = os.urandom(12)
uid_associated_data = os.urandom(12)
pass_secret = secrets.randbits(32).to_bytes(32, 'big')
access_token_secret = secrets.randbits(32).to_bytes(32, 'big')
digest_size = 20


def _generate_uid_slug(uid: str) -> str:
    cipher = ChaCha20Poly1305(uid_secret)
    return base64.b64encode(cipher.encrypt(uid_nonce, uid.encode(), None)).decode('utf-8')


def _generate_uid_key(uid_slug: str) -> str:
    j = blake2b(digest_size=digest_size, key=pass_secret)
    j.update(uid_slug.encode('utf-8'))

    return j.hexdigest()


def generate_credentials(uid: str) -> (str, str):
    uid_slug = _generate_uid_slug(uid)
    key = _generate_uid_key(uid_slug)
    return uid, key


def validate_credentials(uid: str, key: str) -> bool:
    uid_slug = _generate_uid_slug(uid)
    derived_key = _generate_uid_key(uid_slug)

    return key == derived_key

def validate_action(uid: str, action: str, resource: str) -> bool:
    return True


def generate_access_token(uid: str, key: str, time_to_live: int) -> str:
    uid_slug = _generate_uid_slug(uid)

    if validate_credentials(uid, key):
        # generate access token if credentials are valid
        payload = {
            "uid_slug": uid_slug,
            "key": key,
            "time_to_live": time_to_live + time.time()
        }

        return jwt.encode(payload, access_token_secret, algorithm="HS256")
    else:
        raise ValueError("Invalid credentials")


def validate_access_token(token: str, action: (str, str) = None) -> bool:
    try:
        payload = jwt.decode(token, access_token_secret, algorithms=["HS256"])
        # check if token has expired
        if time.time() < payload["time_to_live"]:
            # check if action is valid
            if action is not None:
                return validate_action(payload["uid_slug"], action[0], action[1])
            return True
        return False
    except jwt.ExpiredSignatureError:
        return False


if __name__ == '__main__':
    uid_ = "pmahon@sfu.ca"
    _, key_ = generate_credentials(uid_)
    print(f"UID: {uid_}")
    print(f"Key: {key_}")

    access_token = generate_access_token(uid=uid_, key=key_, time_to_live=5)
    print(f"Access Token: {access_token}")
    print(jwt.decode(access_token, access_token_secret, algorithms=["HS256"]))

    print(validate_access_token(access_token))
