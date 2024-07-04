import json
import treelib

from treelib.exceptions import DuplicatedNodeIdError
from abc import ABC
from typing import List


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

    def __init__(self, access_point_slug: str, endpoint: str):
        """
        Initialize a new instance of the class.

        :param access_point_slug: The slug for the access point.
        :type access_point_slug: str
        :param endpoint: The endpoint for the access point.
        :type endpoint: str
        """
        self.access_point_slug = access_point_slug
        self.endpoint = endpoint
        # File tree to store the structure of objects im the access point
        self.file_tree: treelib.Tree = None

    def _add_file_to_tree(self, path: str, parent: str = 'root'):
        """
        Add a file to the file tree.

        :param path: The path of the file to be added.
        :param parent: The parent folder of the file. Default is 'root'.
        :return: None
        """
        parts = path.rstrip('/').split('/')
        parts = [parent] + parts
        for i in range(1, len(parts)):
            current_folder = parts[i]
            try:
                self.file_tree.create_node(current_folder, current_folder, parent=parts[i - 1])
            except DuplicatedNodeIdError:
                pass

    def _load_file_tree(self):
        """
        Loads the file tree.

        :return: None
        """
        raise NotImplementedError

    def fetch_all_asset_paths(self) -> List[str]:
        """
        Fetches all asset paths.

        :return: A list of strings representing the asset paths.
        """
        raise NotImplementedError

    # Generate HTML from the tree
    def tree_to_jstree_json(self):
        def recurse(node):
            children = [recurse(child) for child in self.file_tree.children(node.identifier)]
            return {"text": node.tag, "children": children}

        root_node = self.file_tree.get_node(self.file_tree.root)
        return json.dumps([recurse(root_node)])