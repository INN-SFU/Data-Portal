import boto3
import json
import treelib
import os

from uuid import uuid5, NAMESPACE_DNS
from treelib.exceptions import DuplicatedNodeIdError
from abc import ABC


class Agent(ABC):
    def __init__(self, access_point_slug: str, endpoint: str):
        self.access_point_slug = access_point_slug
        self.endpoint = endpoint
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
        raise NotImplementedError

    def fetch_all_asset_paths(self):
        raise NotImplementedError

    # Generate HTML from the tree
    def generate_html(self):
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
        super().__init__('arbutus-cloud', 'https://object-arbutus.cloud.computecanada.ca:443')

        # Initialize the S3 client
        s3_config = os.path.join(os.path.dirname(__file__), 'arbutus_s3_config.json')
        with open(s3_config, 'r') as f:
            config = json.load(f)
        f.close()
        self.client = boto3.client('s3',
                                   endpoint_url=self.endpoint,
                                   aws_access_key_id=config['aws_access_key_id'],
                                   aws_secret_access_key=config['aws_secret_access_key'])

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

    def fetch_all_buckets(self):
        """
        Fetches all buckets.
        """
        response = self.client.list_buckets()
        buckets = []
        for bucket in response['Buckets']:
            buckets.append(bucket['Name'])
        return buckets

    def fetch_all_bucket_keys(self, bucket):
        """
        Fetches all objects in a bucket.
        """
        response = self.client.list_objects_v2(Bucket=bucket)
        objects = []
        for obj in response['Contents']:
            objects.append(obj['Key'])
        return objects

    def fetch_all_asset_paths(self):
        """
        Fetches all object paths from S3 buckets.

        :return: A list of all object paths.
        :rtype: list
        """
        s3 = self.client
        all_keys = []

        # List all buckets
        buckets_response = s3.list_buckets()
        buckets = [bucket['Name'] for bucket in buckets_response['Buckets']]

        # Fetch object keys from each bucket and format them
        for bucket_name in buckets:
            paginator = s3.get_paginator('list_objects_v2')

            for page in paginator.paginate(Bucket=bucket_name):
                if 'Contents' in page:
                    all_keys.extend([f"{bucket_name}/{obj['Key']}" for obj in page['Contents']])

        return all_keys


agents = [ArbutusAgent()]

if __name__ == '__main__':
    agent = ArbutusAgent()
    print(agent.file_tree.__str__())
