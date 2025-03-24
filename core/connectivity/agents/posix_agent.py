import base64
import json
import os
import subprocess
import tempfile

import treelib

from core.connectivity.agent import Agent


class PosixAgent(Agent):
    """
    PosixAgent is a class that represents an agent for interacting with a POSIX filesystem.

    Inherits from Agent.

    Attributes:
        endpoint_url (str): The base URL for serving files.
        _SSH_CA_KEY (str): The path to the SSH CA private key used for signing certificates.
    """

    FLAVOUR = 'posix'

    def __init__(self,
                 access_point_slug: str,
                 endpoint_url: str,
                 ssh_ca_key: str):
        """
        Initialize a new instance of the class.

        :param access_point_slug: The slug for the access point.
        :type access_point_slug: str
        :param endpoint_url: The base URL for serving files.
        :type endpoint_url: str
        """

        super().__init__(access_point_slug, endpoint_url)

        self._ssh_ca_key = ssh_ca_key

        # Initialize the file tree
        self._load_file_tree()

    def _load_file_tree(self):
        """
        Load the file tree by creating nodes for files and directories.

        :return: None
        """
        self.file_tree = treelib.Tree()
        self.file_tree.create_node("root", "root")
        for root_dir, dirs, files in os.walk(self.endpoint_url):
            rel_root = os.path.relpath(root_dir, self.endpoint_url)
            for file_name in files:
                if rel_root == '.':
                    path = file_name
                else:
                    rel_path = rel_root.replace(os.path.sep, self.separator)
                    path = rel_path + self.separator + file_name
                self._add_file_to_tree(path)

    def generate_access_links(self, resource: str, method: str, ttl: int):
        """
        Generate a URL with an embedded SSH certificate for accessing a resource.

        :param resource: The resource identity to embed in the certificate.
        :param method: The HTTP method to use for accessing the resource.
        :param ttl: Time-to-live in seconds.
        :return:
        """
        # First, generate the SSH certificate for this resource.
        cert_data = self._generate_ssh_certificate(resource, ttl)
        # Encode the certificate (e.g. Base64) to make it URL safe.
        encoded_cert = base64.urlsafe_b64encode(cert_data.encode()).decode()
        # Build the URL with the certificate as a query parameter.
        tokenized_url = f"{self.endpoint_url}?cert={encoded_cert}"
        return tokenized_url

    def generate_ssh_certificate(self, resource: str, method: str, ttl: int) -> str:
        """
        Generate an SSH certificate that embeds the metadata in its identity field.

        Steps:
          1. Create an ephemeral key pair.
          2. Sign the public key with the SSH CA key.
             - The certificate identity is set to a string like:
                   "resource=folder/file.txt;method=read;ttl=3600"
          3. The validity interval is set to +{ttl}s.

        :param resource: The relative path of the resource.
        :param method: The operation (e.g., "read" or "write").
        :param ttl: The time-to-live in seconds.
        :return: The generated SSH certificate as a string.
        """
        # Create a temporary file for the ephemeral key.
        with tempfile.NamedTemporaryFile(delete=False) as tmp_key:
            key_path = tmp_key.name

        # Generate an ephemeral key pair (RSA, with no passphrase).
        subprocess.run(["ssh-keygen", "-t", "rsa", "-N", "", "-f", key_path], check=True)
        pubkey_path = key_path + ".pub"

        # Define the validity interval (e.g., "+3600s" for 3600 seconds).
        validity = f"+{ttl}s"

        # Build the identity string with our metadata.
        identity = f"resource={resource};method={method};ttl={ttl}"

        # For simplicity, we use the resource as the valid principal.
        principal = resource

        # The generated certificate will be stored in a file with a "-cert.pub" suffix.
        cert_path = key_path + "-cert.pub"

        # Use ssh-keygen to sign the ephemeral public key to generate a certificate.
        # -I sets the identity (here with our metadata).
        # -V sets the validity interval.
        # -n sets the valid principals.
        # -z sets a serial number (here we use a fixed value for demonstration).
        subprocess.run([
            "ssh-keygen", "-s", self._ssh_ca_key,
            "-I", identity,
            "-V", validity,
            "-n", principal,
            "-z", "1",
            "-f", pubkey_path
        ], check=True)

        # Read the generated certificate.
        with open(cert_path, "r") as f:
            cert_data = f.read().strip()

        # Clean up temporary files.
        os.remove(key_path)
        os.remove(pubkey_path)
        os.remove(cert_path)

        return cert_data

    def _get_config(self):
        """
        Get the configuration of the agent.

        :return: The configuration of the agent.
        """
        config = {
            "access_point_slug": self.access_point_slug,
            "endpoint_url": self.endpoint_url,
            "ssh_ca_key": self._ssh_ca_key
        }

        return config
