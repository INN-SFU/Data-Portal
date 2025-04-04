from typing import Dict, Any, Optional, List, Union

import treelib
import re

from treelib.exceptions import DuplicatedNodeIdError
from abc import ABC
from treelib import node, tree
from uuid import UUID
from core.management.policies import AbstractPolicyManager


class AbstractStorageAgent(ABC):
    """
    AbstractStorageAgent

    Class representing an agent.

    Methods:
    - __init__()
    - _add_file_to_tree()
    - _load_file_tree()
    - fetch_all_asset_paths()
    - generate_html()
    """

    FLAVOUR = None

    def __init__(self, access_point_slug: str, endpoint_url: str, endpoint_uid: UUID, separator: str = '/'):
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
        self.uid = endpoint_uid
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
        sub_tree = treelib.Tree()
        sub_tree.create_node('root', 'root')  # Create a root node for the user tree

        for node in self.file_tree.filter_nodes(node_filter):
            if not sub_tree.contains(node.identifier):
                # Ensure all parents are added to the user tree
                parent = self.file_tree.parent(node.identifier)
                while parent and not sub_tree.contains(parent.identifier):
                    sub_tree.create_node(parent.tag, parent.identifier,
                                         parent=parent.predecessor(self.file_tree.identifier))
                    parent = self.file_tree.parent(parent.identifier)
                sub_tree.create_node(node.tag, node.identifier,
                                     parent=node.predecessor(self.file_tree.identifier))
        return sub_tree

    def partition_file_tree_by_access(
            self,
            policy_manager: AbstractPolicyManager,
            user_uid: UUID,
            access_point_uid: UUID,
            access_types: Union[str, List[str]]
    ) -> Dict[str, treelib.Tree]:
        """
        Partition the file tree into separate treelib.Tree objects for each access type
        in a single traversal, using the provided policy manager.

        :param policy_manager: An instance responsible for validating policies.
        :param user_uid: The user UUID.
        :param access_point_uid: The identifier for the storage endpoint.
        :param access_types: A single access type (as a string) or a list of access types (e.g. 'read' or ['read', 'write']).
        :return: A dict mapping each access type to a filtered treelib.Tree.
        """
        # If a single string is passed, convert it to a list.
        if isinstance(access_types, str):
            access_types = [access_types]  # type: List[str]

        # Convert UUIDs to strings.
        user_uid_str: str = str(user_uid)
        access_point_uid_str: str = str(access_point_uid)

        # Alias for a partition dictionary.
        Partition = Dict[str, Any]

        def partition_node(node: treelib.Node) -> Dict[str, Optional[Partition]]:
            # Check policy for the current node for each access type.
            current_allowed: Dict[str, bool] = {
                access: policy_manager.validate_policy(user_uid_str, access_point_uid_str, node.identifier, access)
                for access in access_types
            }
            # Recurse on children.
            children_partitions: List[Dict[str, Optional[Partition]]] = [
                partition_node(child) for child in self.file_tree.children(node.identifier)
            ]

            # For each access type, gather partitions from children that are not empty.
            partitions: Dict[str, Optional[Partition]] = {}
            for access in access_types:
                allowed_children: List[Partition] = [
                    child_partition[access]
                    for child_partition in children_partitions
                    if child_partition[access] is not None
                ]
                # Include the node if it is the root, it passes the policy, or has allowed children.
                if node.identifier == 'root' or current_allowed[access] or allowed_children:
                    partitions[access] = {
                        'identifier': node.identifier,
                        'tag': node.tag,
                        'children': allowed_children
                    }
                else:
                    partitions[access] = None
            return partitions

        # Start partitioning from the root node.
        root_node: treelib.Node = self.file_tree.get_node('root')
        partitions: Dict[str, Optional[Partition]] = partition_node(root_node)

        # Helper function to convert a dictionary-based tree to a treelib.Tree.
        def dict_to_tree(dict_tree: Partition) -> treelib.Tree:
            new_tree = treelib.Tree()

            def add_nodes_recursively(node_dict: Partition, parent_id: Optional[str] = None) -> None:
                new_tree.create_node(tag=node_dict['tag'], identifier=node_dict['identifier'], parent=parent_id)
                for child in node_dict.get('children', []):
                    add_nodes_recursively(child, node_dict['identifier'])

            add_nodes_recursively(dict_tree)
            return new_tree

        # Convert each partition (if any) into a treelib.Tree.
        trees: Dict[str, treelib.Tree] = {}
        for access in access_types:
            if partitions[access] is not None:
                trees[access] = dict_to_tree(partitions[access])
        return trees

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
            'access_point_uid': self.uid,
            'endpoint_url': self.endpoint_url,
            'flavour': self.FLAVOUR
        }

        return config

    def _get_config(self):
        """
        Return the configuration of the agent including sensitive information.

        :return: The configuration of the agent.
        :rtype: dict
        """
        raise NotImplementedError
