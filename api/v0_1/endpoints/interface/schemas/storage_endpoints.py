# api/v0_1/endpoints/service/models.py
from typing import Literal, Union, Annotated
from pydantic import BaseModel, create_model, Field, HttpUrl

from core.connectivity.agents import (
    available_flavours,
    S3StorageAgent,
    PosixStorageAgent
)

# shared base:
class EndpointBase(BaseModel):
    flavour: Literal[tuple(available_flavours.keys())]
    access_point_name: str
    endpoint_url: str

# build per-flavour create models:
S3EndpointCreate = create_model(
    "S3EndpointCreate",
    __base__=EndpointBase,
    flavour=(Literal[S3StorageAgent.FLAVOUR], ...),
    **{ name: (typ, ...) for name, typ in S3StorageAgent.CONFIG.items() }
)

PosixEndpointCreate = create_model(
    "PosixEndpointCreate",
    __base__=EndpointBase,
    flavour=(Literal[PosixStorageAgent.FLAVOUR], ...),
    **{ name: (typ, ...) for name, typ in PosixStorageAgent.CONFIG.items() }
)

# discriminated union:
EndpointCreate = Annotated[
    Union[S3EndpointCreate, PosixEndpointCreate],
    Field(discriminator="flavour")
]
