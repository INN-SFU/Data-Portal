from typing import Optional, Union
from uuid import UUID

from pydantic import BaseModel
from datetime import timedelta


class Policy(BaseModel):
    user_id: Union[UUID, None] = None
    endpoint_id: Union[UUID, None] = None
    resource: Optional[str] = None
    action: Optional[str] = None


Policies = list[Policy]


class Agreement(BaseModel):
    uuid: UUID
    policies: Policies
    lifespan: timedelta
    version: float
