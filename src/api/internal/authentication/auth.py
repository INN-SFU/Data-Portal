import os
import jwt
import time

from hashlib import blake2b


def _generate_uid_key(uid_slug: str) -> str:
    """
    Generates the uid_slug key for a given uuid

    :param uid_slug: The users uid.
    :return: The generated uid_slug key as a string.
    """
    j = blake2b(digest_size=int(os.getenv("DIGEST_SIZE")), key=os.getenv("PASS_SECRET").encode())
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
    return uid_slug, _generate_uid_key(uid_slug)


def validate_credentials(uid_slug: str, key: str) -> bool:
    """
    Validate if the provided credentials are valid.

    :param uid_slug: The user ID. A string.
    :param key: The key associated with the user ID. A string.
    :return: True if the provided credentials are valid, False otherwise.
    """
    derived_key = _generate_uid_key(uid_slug)
    return key == derived_key


def generate_token(uid_slug: str, key: str, time_to_live: int) -> str:
    """
    Generate Access Token

    Generates an access token for the given user ID, key, and time to live.

    :param uid_slug: The user ID.
    :type uid_slug: str
    :param key: The key for the user.
    :type key: str
    :param time_to_live: The time to live (in seconds) for the access token.
    :type time_to_live: int
    :return: The generated access token.
    :rtype: str
    :raises ValueError: If the provided credentials are invalid.
    """

    if validate_credentials(uid_slug, key):
        # generate access token if credentials are valid
        payload = {
            "uid": uid_slug,
            "key": key,
            "time_to_live": time_to_live + time.time()
        }

        return jwt.encode(payload, os.getenv("ACCESS_TOKEN_SECRET"), algorithm="HS256")
    else:
        raise ValueError("Invalid credentials")


def validate_token(token: str) -> bool:
    """
    :param token: The access token to be validated.
    :param action: Optional parameter specifying the action to be validated.
    :return: Returns a boolean value indicating whether the access token is valid or not.

    This method validates the given access token. It decodes the token using the access_token_secret and checks if it has expired. If the token has not expired, it optionally validates the
    * specified action. If the action is valid or no action is specified, it returns True indicating that the access token is valid. Otherwise, it returns False.

    Example usage:
        token = "abc123xyz"
        action = ("read", "post")
        is_valid = validate_access_token(token, action)
        print(is_valid)  # Output: True
    """
    try:
        payload = jwt.decode(token, os.getenv("ACCESS_TOKEN_SECRET"), algorithms=["HS256"])
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
    return jwt.decode(token, os.getenv("ACCESS_TOKEN_SECRET"), algorithm="HS256")


if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv("/Users/pmahon/Research/INN/Data Portal/DAM/src/api/.env")
    uid_slug_ = "pmahon@sfu.ca"
    _, key_ = generate_credentials(uid_slug_)
    print(f"uid_slug: {uid_slug_}")
    print(f"Key: {key_}")

    access_token = generate_token(uid_slug=uid_slug_, key=key_, time_to_live=5)
    print(f"Access Token: {access_token}")
    print(jwt.decode(access_token, os.getenv("ACCESS_TOKEN_SECRET"), algorithms=["HS256"]))

    print(validate_token(access_token))
