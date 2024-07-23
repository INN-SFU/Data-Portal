from treelib import Tree

from fastapi import Depends
from fastapi.security import HTTPBasicCredentials
from fastapi.exceptions import HTTPException

from core.data_access_manager import dam
from core.authentication import validate_credentials as auth_validate_credentials

from api.v0_1.endpoints.service.auth import security


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


def validate_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> (str, str):
    """
    Validate credentials.

    :param credentials: The HTTP basic authentication credentials.
    :return: Returns a tuple containing the username and password if the credentials are valid.
    :raises HTTPException: If the credentials are invalid.
    """
    uid = credentials.username
    password = credentials.password

    if uid not in dam.get_users():
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if auth_validate_credentials(uid, password):
        return uid, password
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")


def is_admin(credentials: HTTPBasicCredentials = Depends(security)) -> bool:
    """
    Function to check if the user with the given credentials is an admin.

    :param credentials: The HTTPBasicCredentials object containing the username and password.
    :type credentials: HTTPBasicCredentials, optional

    :return: True if the user is an admin, False otherwise.
    :rtype: bool
    :raises HTTPException: If the user is not an administrator.
    """
    uid = credentials.username

    if not dam.get_user(uid)['role'] == 'admin':
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    else:
        return True
