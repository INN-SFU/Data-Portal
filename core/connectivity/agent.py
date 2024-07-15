import json
import treelib

from treelib.exceptions import DuplicatedNodeIdError
from abc import ABC
from typing import List
from treelib import node, tree
from treelib.exceptions import NodeIDAbsentError

from core.data_access_manager.DataAccessManager import DataAccessManager


class Agent(ABC):
    """
    Agent

    Class representing an agent.

    Methods:
    - __init__()
    - _add_file_to_tree()
    - _load_file_tree()
    - fetch_all_asset_paths()
    - generate_html()
    """

    def __init__(self, access_point_slug: str, endpoint: str, separator: str = '/'):
        """
        Initialize a new instance of the class.

        :param access_point_slug: The slug for the access point.
        :type access_point_slug: str
        :param separator: The string separator used in the file namespace structure.
        :param endpoint: The endpoint for the access point.
        :type endpoint: str
        """
        self.access_point_slug = access_point_slug
        self.endpoint = endpoint
        self.separator = separator
        # File tree to store the structure of objects im the access point
        self.file_tree: treelib.Tree = None

    def _add_file_to_tree(self, path: str):
        """
        Add a file to the file tree.

        :param path: The path of the file to be added.
        :return: None
        """
        parts = path.rstrip(self.separator).split(self.separator)
        parent = self.file_tree.root

        for i in range(len(parts)):
            current_tag = parts[i]
            current_nid = self.separator.join(parts[:i + 1])
            try:
                self.file_tree.create_node(current_tag, current_nid, parent=parent)
            except DuplicatedNodeIdError:
                pass

            parent = self.file_tree.get_node(current_nid)

    def _load_file_tree(self):
        """
        Loads the file tree.

        :return: None
        """
        raise NotImplementedError

    def get_file_identifiers(self, path):
        """
        Get the identifiers of the files in the given path.
        :param path: The path of the node whose children are to be fetched.
        :return: List of identifiers of the files under the given path.
        """
        try:
            # Return the identifiers of the leaf nodes under the node
            return [node.identifier for node in self.file_tree.leaves(path)]
        except KeyError:
            raise ValueError(f"Path '{path}' not found in the tree")

    def get_user_file_tree(self, uid: str, action: str, dam: DataAccessManager) -> tree:
        """
        Get all user files based on the provided user id, action, and DataAccessManager object.

        :param uid: Unique identifier of the user.
        :param action: Action to perform on the files.
        :param dam: DataAccessManager object for retrieving access permissions.
        :return: A Tree object representing the user's accessible files.
        """
        user_tree = treelib.Tree()
        user_tree.create_node('root', 'root')  # Create a root node for the user tree

        def node_filter(n: node):
            vals = (uid, self.access_point_slug, n.identifier, action)
            return dam.enforcer.enforce(*vals)

        for user_node in self.file_tree.filter_nodes(node_filter):
            if not user_tree.contains(user_node.identifier):
                # Ensure all parents are added to the user tree
                parent = self.file_tree.parent(user_node.identifier)
                while parent and not user_tree.contains(parent.identifier):
                    user_tree.create_node(parent.tag, parent.identifier, parent=parent.predecessor(self.file_tree.identifier))
                    parent = self.file_tree.parent(parent.identifier)
                user_tree.create_node(user_node.tag, user_node.identifier, parent=user_node.predecessor(self.file_tree.identifier))

        return user_tree

    # Generate HTML from the tree
    def tree_to_jstree_json(self):
        def recurse(node):
            children = [recurse(child) for child in self.file_tree.children(node.identifier)]
            return {"text": node.tag, "children": children}

        root_node = self.file_tree.get_node(self.file_tree.root)
        return json.dumps([recurse(root_node)])

    def generate_access_links(self, resource: str, method: str, ttl: int):
        """
        Generate a presigned URL for accessing an asset.

        :param resource: The key/regex of the asset(s).
        :param method: The method to use for accessing the asset.
        :param ttl: The time-to-live for the URL.
        :return: The presigned URL.
        """
        raise NotImplementedError
