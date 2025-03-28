import json
import os

import treelib
import re

from treelib.exceptions import DuplicatedNodeIdError
from abc import ABC
from treelib import node, tree


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

    def __init__(self, access_point_slug: str, endpoint_url: str,  separator: str = '/'):
        """
        Initialize a new instance of the class.

        :param access_point_slug: The slug for the access point.
        :type access_point_slug: str
        :param endpoint_url: The endpoint_url for the access point.
        :type endpoint_url: str
        """
        self.access_point_slug = access_point_slug
        self.endpoint_url = endpoint_url
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
            return [node_.identifier for node_ in self.file_tree.leaves(path)]
        except KeyError:
            raise ValueError(f"Path '{path}' not found in the tree")

    def filter_file_tree(self, node_filter) -> tree:
        """
        Returns a subtree of the access point's file tree based on the provided boolean node filter function.

        :param node_filter: A function or lambda expression that takes a node object as input and returns a boolean
            value indicating whether the node should be included in the filtered tree.
        :return: A filtered tree object containing only the nodes that pass the node_filter criteria.
        :rtype: treelib.Tree
        """
        user_tree = treelib.Tree()
        user_tree.create_node('root', 'root')  # Create a root node for the user tree

        for user_node in self.file_tree.filter_nodes(node_filter):
            if not user_tree.contains(user_node.identifier):
                # Ensure all parents are added to the user tree
                parent = self.file_tree.parent(user_node.identifier)
                while parent and not user_tree.contains(parent.identifier):
                    user_tree.create_node(parent.tag, parent.identifier,
                                          parent=parent.predecessor(self.file_tree.identifier))
                    parent = self.file_tree.parent(parent.identifier)
                user_tree.create_node(user_node.tag, user_node.identifier,
                                      parent=user_node.predecessor(self.file_tree.identifier))
        return user_tree

    def generate_access_links(self, resource: str, method: str, ttl: int):
        """
        Generate a presigned URL for accessing an asset.

        :param resource: The key/regex of the asset(s).
        :param method: The method to use for accessing the asset.
        :param ttl: The time-to-live for the URL.
        :return: The presigned URL.
        """
        raise NotImplementedError

    def get_file_paths(self, resource: str = None):
        """
        Return the file paths of all files matching the resource regular expression.

        :param resource: The key/regex of the asset(s).
        :return: A list of resource file paths.
        """
        if resource is None:
            regex = re.compile('.*')
        else:
            regex = re.compile(resource)

        def node_filter(n: node):
            # Omit the root
            if n.identifier == 'root':
                return False
            return regex.match(n.identifier)

        return [user_node.identifier for user_node in self.file_tree.filter_nodes(node_filter)]

    def get_config(self):
        """
        Return the configuration of the agent.

        :return: The configuration of the agent.
        """
        config = {
            'access_point_slug': self.access_point_slug,
            'endpoint_url': self.endpoint_url,
            'separator': self.separator
        }

        return config

    def _get_config(self):
        """
        Return the configuration of the agent including sensitive information.

        :return: The configuration of the agent.
        :rtype: dict
        """
        raise NotImplementedError
