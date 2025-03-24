import logging
from treelib import Tree

from fastapi import Depends, status
from fastapi.security import HTTPBasicCredentials
from fastapi.exceptions import HTTPException

from core.data_access_manager import dam
from core.authentication import validate_credentials as auth_validate_credentials

from api.v0_1.endpoints.service.auth import security

logger = logging.getLogger('app')


def convert_file_tree_to_dict(tree: Tree) -> list[dict]:
    """
    Convert a file tree to a dictionary.

    :param tree: The file tree to convert.
    :type tree: Tree
    :return: The converted file tree as a dictionary.
    :rtype: list[dict]
    """
    tree_data = []
    for node in tree.all_nodes():
        if node.tag != 'root':  # Skip the 'root' node
            parent = tree.parent(node.identifier)
            # If the parent is 'root', treat this node as a top-level node
            parent_id = '#' if parent is None or parent.tag == 'root' else parent.identifier
            tree_data.append(
                {"id": node.identifier, "parent": parent_id, "text": node.tag, "li_attr": {"data-id": node.identifier}}
            )
    return tree_data


def validate_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """
    Validate _credentials.

    :param credentials: The HTTP basic authentication _credentials.
    :return: Returns the username (uid) if the _credentials are valid.
    :raises HTTPException: If the _credentials are invalid.
    """
    uid = credentials.username
    password = credentials.password

    logger.info(f"User access request: {uid}")
    if uid not in dam.get_all_users():
        logger.info(f"User access denied. {uid} is not a registered user.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid _credentials")

    if auth_validate_credentials(uid, password):
        logger.info(f"User access granted: {uid}")
        return uid
    else:
        logger.info(f"User access denied: {uid}. Invalid key.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid _credentials")


def is_admin(credentials: HTTPBasicCredentials = Depends(security)) -> bool:
    """
    Function to check if the user with the given _credentials is an admin.

    :param credentials: The HTTPBasicCredentials object containing the username and password.
    :type credentials: HTTPBasicCredentials, optional

    :return: True if the user is an admin, False otherwise.
    :rtype: bool
    :raises HTTPException: If the user is not an administrator.
    """
    uid = credentials.username

    logger.info(f"Admin access request: {uid}")

    if not dam.get_user(uid)['role'] == 'admin':
        logger.info(f"Admin access denied. {uid} is not a registered administrator.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid _credentials.")
    else:
        logger.info(f"Admin access granted: {uid}")
        return True
