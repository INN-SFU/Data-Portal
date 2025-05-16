import os
import re
import logging
import boto3
import treelib

from typing import List, Tuple
from core.connectivity import AbstractStorageAgent

casbin_logger = logging.getLogger("casbin")
app_logger = logging.getLogger("app")


class S3StorageAgent(AbstractStorageAgent):
    FLAVOUR = 's3'
    CONFIG = {
        "aws_access_key_id": str,
        "aws_secret_access_key": str
    }

    # ensure CORS only applies once
    _cors_enabled = False

    def __init__(self,
                 endpoint_url: str,
                 aws_access_key_id: str,
                 aws_secret_access_key: str):
        super().__init__(endpoint_url)

        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )

        # build the in-memory file tree
        self.file_tree = treelib.Tree()
        self._load_file_tree()

        # enable CORS the first time any agent is created
        if not S3StorageAgent._cors_enabled:
            self._enable_cors()
            S3StorageAgent._cors_enabled = True

    def _load_file_tree(self):
        self.file_tree.create_node('root', 'root')
        for bucket in self.fetch_all_buckets():
            self._add_file_to_tree(bucket)
            for obj in self.fetch_all_bucket_keys(bucket):
                self._add_file_to_tree(os.path.join(bucket, obj))

    def fetch_all_buckets(self) -> List[str]:
        resp = self.s3_client.list_buckets()
        return [b['Name'] for b in resp.get('Buckets', [])]

    def fetch_all_bucket_keys(self, bucket: str) -> List[str]:
        resp = self.s3_client.list_objects_v2(Bucket=bucket)
        return [o['Key'] for o in resp.get('Contents', [])]

    def generate_access_link(
        self, resource: str, method: str, ttl: int
    ) -> Tuple[List[str], List[str]]:
        # map to boto3 operation
        if method == "read":
            verb = "get_object"
        elif method == "write":
            verb = "put_object"
        else:
            raise ValueError(f"Unsupported method {method!r}")

        # WRITE: single presigned‐PUT URL
        if verb == "put_object":
            try:
                bucket, key = resource.split("/", 1)
            except ValueError:
                raise ValueError(f"Bad S3 path: {resource!r}")
            url = self.s3_client.generate_presigned_url(
                ClientMethod=verb,
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=ttl
            )
            casbin_logger.info(f"generate_access_link (write): URL for {resource}")
            return [url], [resource]

        # READ: treat resource as regex, full‐match
        pattern = re.compile(resource)
        all_paths = [
            n.identifier
            for n in self.file_tree.all_nodes()
            if n.identifier != 'root'
        ]
        matched = [p for p in all_paths if pattern.fullmatch(p)]
        if not matched:
            casbin_logger.info(f"No objects match regex: {resource}")
            return [], []

        urls = []
        for path in matched:
            bucket, key = path.split("/", 1)
            urls.append(self.s3_client.generate_presigned_url(
                ClientMethod=verb,
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=ttl
            ))

        casbin_logger.info(f"generate_access_link (read): matched {len(matched)} for {resource}")
        return urls, matched

    def _enable_cors(self):
        """
        Permissive CORS for local dev: allow all origins,
        all typical S3 methods, and OPTIONS preflights.
        """
        cors_conf = {
            "CORSRules": [{
                "AllowedOrigins": ["*"],  # dev only!
                "AllowedMethods": [  # include OPTIONS + HEAD
                    "GET", "PUT", "POST", "DELETE", "HEAD"
                ],
                "AllowedHeaders": ["*"],
                "ExposeHeaders": ["ETag"],
                "MaxAgeSeconds": 300
            }]
        }
        for bucket in self.fetch_all_buckets():
            app_logger.info(f"Applying dev CORS to bucket {bucket}")
            self.s3_client.put_bucket_cors(
                Bucket=bucket,
                CORSConfiguration=cors_conf
            )

    def config(self, secrets: bool = False) -> dict:
        return super().config(secrets)

    def _secrets(self):
        creds = self.s3_client._request_signer._credentials
        return {
            "aws_access_key_id": creds.access_key,
            "aws_secret_access_key": creds.secret_key
        }

    def refresh_connection(self):
        creds = self.s3_client._request_signer._credentials
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=creds.access_key,
            aws_secret_access_key=creds.secret_key
        )

    def close(self):
        self.s3_client.close()

    def __str__(self):
        return f"S3StorageAgent(endpoint_url={self.endpoint_url})"
