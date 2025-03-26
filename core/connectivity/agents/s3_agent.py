import boto3
import treelib
import os
import logging

from typing import List

from core.connectivity.agent import Agent

logger = logging.getLogger("casbin")


class S3Agent(Agent):
    """
    S3Agent is a class that represents an agent for interacting with an S3 object store service.

    Inherits from Agent.

    Attributes:
        endpoint_url (str): The endpoint URL of the S3 service.
        s3_client (boto3.interface): The S3 interface for interacting with the service.
        file_tree (treelib.Tree): The file tree representing the structure of objects in the S3 service.
    """
    FLAVOUR = 's3'

    def __init__(self,
                 access_point_slug: str,
                 endpoint_url: str,
                 aws_access_key_id: str,
                 aws_secret_access_key: str):
        """
        Initialize a new instance of the class.

        :param access_point_slug: The slug for the access point.
        :type access_point_slug: str
        :param endpoint_url: The endpoint_url URL for the access point.
        :type endpoint_url: str
        """

        super().__init__(access_point_slug, endpoint_url)

        self.s3_client = boto3.client('s3',
                                      endpoint_url=self.endpoint_url,
                                      aws_access_key_id=aws_access_key_id,
                                      aws_secret_access_key=aws_secret_access_key)

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
            self._add_file_to_tree(bucket)

        # Fetch all objects in each bucket
        for bucket in buckets:
            objects = self.fetch_all_bucket_keys(bucket)
            # Add folders to the file tree
            for obj in objects:
                self._add_file_to_tree(os.path.join(bucket, obj))

    def fetch_all_buckets(self) -> List[str]:
        """
        Fetches all buckets from the S3 interface.

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

    def generate_access_links(self, resource: str, method: str, ttl: int):
        """
        Generate a presigned URL for accessing the resource.

        :param resource: The resource to generate the presigned URL for. Resources are always referenced from the root
            which is literally labelled 'root'.
            E.g:    root/bucket/object
        :param method: The method to generate the presigned URL for.
        :param ttl: The time-to-live for the presigned URL.
        :return: The presigned URL.
        """
        urls = []
        paths = []

        # GET request handling
        if method == 'GET':
            # Get the file paths for the resource
            logger.info(f"Getting file identifiers for resource: {resource}")
            paths = self.get_file_identifiers(resource)
            logger.info(f"Found {len(paths)} paths for resource: {resource}")
        # PUT request handling
        elif method == 'PUT':
            # Get the file paths for the resource
            paths = [resource]
        else:
            raise ValueError(f"Method {method} not supported")

        logger.info("Generating presigned URLs for {len(paths)} paths")
        for path in paths:
            urls.append(self._generate_presigned_url(path, ttl))
        logger.info(f"Generated urls: {urls}")

        return urls, paths

    def _generate_presigned_url(self, path, ttl):
        bucket = path.split("/")[0]
        key = "/".join(path.split("/")[1:])
        logger.info(f"Generating presigned URL for bucket: {bucket}, key: {key}, TTL: {ttl}")
        return self.s3_client.generate_presigned_url('get_object',
                                                     Params={'Bucket': bucket, 'Key': key},
                                                     ExpiresIn=ttl)

    def _get_config(self) -> dict:
        """
        Get the configuration of the agent.

        :return: The configuration of the agent.
        :rtype: dict
        """

        config = {
                "access_point_slug": self.access_point_slug,
                "endpoint_url": self.endpoint_url,
                "aws_access_key_id": self.s3_client._request_signer._credentials.access_key,
                "aws_secret_access_key": self.s3_client._request_signer._credentials.secret_key
            }

        return config
