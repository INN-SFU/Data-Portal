from pydantic import BaseModel
from typing import Literal


class S3EndpointConfig(BaseModel):
    flavour: Literal["s3"]
    access_point_slug: str
    endpoint_url: str
    aws_access_key_id: str
    aws_secret_access_key: str


class PosixEndpointConfig(BaseModel):
    flavour: Literal["posix"]
    access_point_slug: str
    endpoint_url: str
    ssh_ca_key: str


# You can combine them into a union if desired:
from typing import Union

EndpointConfig = Union[S3EndpointConfig, PosixEndpointConfig]
