import (

    boto3)
import json
import treelib
import os
import openstack
import swiftclient

from typing import List


from core.connectivity.agent import Agent


class ArbutusAgent(Agent):
    """
    ArbutusAgent is a class that represents an agent for interacting with the Arbutus Cloud Object Store service.

    Inherits from Agent.

    Attributes:
        endpoint (str): The endpoint URL of the Arbutus Cloud service.
        s3_client (boto3.client): The S3 client for interacting with the Arbutus Cloud service.
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

        self.s3_client = boto3.client('s3',
                                      endpoint_url=self.endpoint,
                                      aws_access_key_id=config['credentials']['aws_access_key_id'],
                                      aws_secret_access_key=config['credentials']['aws_secret_access_key'])

        # Keystone client is used for generating keys for the S3 client
        self.conn = openstack.connect(
            user_domain_name=os.getenv('OS_USER_DOMAIN_NAME'),
            username=os.getenv('OS_USERNAME'),
            password=os.getenv('OS_PASSWORD'),
            project_domain_name=os.getenv('OS_PROJECT_ID'),
            project_name=os.getenv('OS_PROJECT_NAME'),
            auth_url=os.getenv('OS_AUTH_URL')
        )

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
        response = self.s3_client.list_buckets()
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
        response = self.s3_client.list_objects_v2(Bucket=bucket)
        objects = []
        try:
            for obj in response['Contents']:
                objects.append(obj['Key'])
        except KeyError:
            pass
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

    def generate_access_link(self, asset_key: os.PathLike, method: str):

        # Swift connection
        swift_conn = swiftclient.Connection(session=conn.session)

        # Set the temporary URL key (once per container)
        swift_conn.post_container(container_name, {'X-Container-Meta-Temp-URL-Key': temp_url_key})

        # Generate the temporary URL
        method = 'PUT'
        path = f'/v1/AUTH_{conn.session.get_project_id()}/{container_name}/{object_name}'
        expires = int(time.time() + ttl)
        hmac_body = f'{method}\n{expires}\n{path}'
        signature = hmac.new(temp_url_key.encode(), hmac_body.encode(), hashlib.sha1).hexdigest()
        temp_url = f'https://{conn.session.auth.auth_url.split("//")[1]}/v1/AUTH_{conn.session.get_project_id()}/{container_name}/{object_name}?temp_url_sig={signature}&temp_url_expires={expires}'
