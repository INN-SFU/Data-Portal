import boto3
import json
import treelib
import os

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
    def generate_html(self) -> str:
        """
        Generate HTML representation of the file tree.

        :return: HTML string representing the file tree.
        """
        html_output = "<ul>"

        def recurse(node):
            nonlocal html_output
            children = self.file_tree.children(node.identifier)
            if children:  # Check if the node has children to determine if it's a folder
                html_output += f"<li class='folder'>{node.tag}<ul style='display: none;'>"
                for child in children:
                    recurse(child)
                html_output += "</ul></li>"
            else:
                html_output += f"<li class='file'>{node.tag}</li>"

        root_node = self.file_tree.get_node(self.file_tree.root)
        if root_node is not None:
            recurse(root_node)
        html_output += "</ul>"
        return html_output


class ArbutusAgent(Agent):
    """
    ArbutusAgent is a class that represents an agent for interacting with the Arbutus Cloud Object Store service.

    Inherits from Agent.

    Attributes:
        endpoint (str): The endpoint URL of the Arbutus Cloud service.
        client (boto3.client): The S3 client for interacting with the Arbutus Cloud service.
        file_tree (treelib.Tree): The file tree representing the structure of objects in the Arbutus Cloud service.
    """

    def __init__(self):
        # Access point slug for Arbutus Cloud, needs a matching entry in agents.json file referenced by
        # ACCESS_AGENT_CONFIG
        ACCESS_POINT_SLUG = 'arbutus-cloud'

        # Initialize the S3 client
        with open(os.getenv('ACCESS_AGENT_CONFIG'), 'r') as f:
            config = json.load(f)[ACCESS_POINT_SLUG]
        f.close()

        super().__init__(ACCESS_POINT_SLUG, config['endpoint'])

        self.client = boto3.client('s3',
                                   endpoint_url=self.endpoint,
                                   aws_access_key_id=config['credentials']['aws_access_key_id'],
                                   aws_secret_access_key=config['credentials']['aws_secret_access_key'])

        # Initialize the file tree
        self.file_tree = treelib.Tree()
        self._load_file_tree()

    def _load_file_tree(self):
        """
        Load the file tree by creating nodes for buckets and adding objects to it.

        :return: None
        """
        # Create the root node
        self.file_tree.create_node('root', 'root')

        # Fetch all buckets
        buckets = self.fetch_all_buckets()

        # Add buckets to the file tree
        for bucket in buckets:
            self.file_tree.create_node(bucket, bucket, parent='root')

        # Fetch all objects in each bucket
        for bucket in buckets:
            objects = self.fetch_all_bucket_keys(bucket)
            # Add folders to the file tree
            for obj in objects:
                self._add_file_to_tree(obj, parent=bucket)

    def fetch_all_buckets(self) -> List[str]:
        """
        Fetches all buckets from the S3 client.

        :return: List of bucket names.
        :rtype: List[str]
        """
        response = self.client.list_buckets()
        buckets = []
        for bucket in response['Buckets']:
            buckets.append(bucket['Name'])
        return buckets

    def fetch_all_bucket_keys(self, bucket) -> List[str]:
        """
        Fetches all the keys of the objects in the given bucket.

        :param bucket: The name of the bucket.
        :return: A list of all the keys of the objects in the bucket.
        :rtype: list[str]
        """
        response = self.client.list_objects_v2(Bucket=bucket)
        objects = []
        for obj in response['Contents']:
            objects.append(obj['Key'])
        return objects

    def fetch_all_keys(self) -> List[str]:
        """
        Fetches all object keys from S3 buckets.

        :return: A list of all object keys (i.e. paths).
        :rtype: list[str]
        """
        all_keys = []

        # fetch all buckets
        buckets = self.fetch_all_buckets()

        # fetch all objects in each bucket
        for bucket in buckets:
            objects = self.fetch_all_bucket_keys(bucket)
            all_keys.extend(objects)

        return all_keys


if __name__ == '__main__':
    agent = ArbutusAgent()
    print(agent.file_tree.__str__())
