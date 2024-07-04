import os
import jwt
import time
import secrets

from hashlib import blake2b


def _generate_uid_secret_key(uid_slug: str) -> str:
    """
    Generates the uid_slug key for a given uuid

    :param uid_slug: The users uid.
    :return: The generated uid_slug key as a string.
    """
    j = blake2b(digest_size=int(os.getenv("DIGEST_SIZE")), key=os.getenv("UID_KEY_SECRET").encode())
    j.update(uid_slug.encode('utf-8'))

    return j.hexdigest()


def generate_credentials(uid_slug: str) -> (str, str):
    """
    Generate credentials for a given uid_slug.

    :param uid_slug: The unique identifier.
    :type uid_slug: str
    :return: The generated credentials consisting of uuid and key.
    :rtype: tuple[str, str]
    """
    return uid_slug, _generate_uid_secret_key(uid_slug)


def validate_credentials(uid_slug: str, key: str) -> bool:
    """
    Validate if the provided credentials are valid.

    :param uid_slug: The user ID. A string.
    :param key: The key associated with the user ID. A string.
    :return: True if the provided credentials are valid, False otherwise.
    """

    derived_key = _generate_uid_secret_key(uid_slug)
    return secrets.compare_digest(key, derived_key)


def generate_token(uid_slug: str, key: str, time_to_live: int, access_point: str = None, resource: str = None,
                   action: str = None) -> str:
    """
    Generate an access token for a given user.

    :param uid_slug: The unique identifier or slug for the user.
    :param key: The key or password for the user.
    :param time_to_live: The time (in seconds) that the token will remain valid.
    :param access_point: (optional) The access point or endpoint for the user.
    :param resource: (optional) The resource or object that the user intends to access.
    :param action: (optional) The action or operation that the user intends to perform.
    :return: The generated access token as a string.
    :raises: ValueError if the provided credentials are invalid.
    """
    if validate_credentials(uid_slug, key):
        # generate access token if credentials are valid
        payload = {
            "uid": uid_slug,
            "key": key,
            "time_to_live": time_to_live + time.time(),
            "access_point": access_point,
            "resource": resource,
            "action": action
        }

        return jwt.encode(payload, os.getenv("JWT_TOKEN_SECRET"), algorithm="HS256")
    else:
        raise ValueError("Invalid credentials")


def token_expired(token: str) -> bool:
    """
    Check if the given token has expired.

    :param token: The token to be checked for expiry.
    :type token: str
    :return: True if the token is expired, False otherwise.
    :rtype: bool
    """
    try: 
        payload = jwt.decode(token, os.getenv("JWT_TOKEN_SECRET"), algorithms=["HS256"])
        # check if token has expired
        if time.time() < payload["time_to_live"]:
            return True
        return False
    except jwt.ExpiredSignatureError:
        return False


def decode_token(token: str):
    """Wrapper to decode a JSON Web Token (JWT).

    :param token: The JWT to be decoded.
    :return: The decoded JWT as a Python dictionary.
    """
    return jwt.decode(token, os.getenv("JWT_TOKEN_SECRET"), algorithms=["HS256"])


if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv("//ams/api/settings/.env")
    uid_slug_ = "pmahon@sfu.ca"
    _, key_ = generate_credentials(uid_slug_)
    print(f"uid_slug: {uid_slug_}")
    print(f"Key: {key_}")

    access_token = generate_token(uid_slug=uid_slug_, key=key_, time_to_live=600)
    print(f"Access Token: {access_token}")
    print(jwt.decode(access_token, os.getenv("JWT_TOKEN_SECRET"), algorithms=["HS256"]))

    print(token_expired(access_token))
