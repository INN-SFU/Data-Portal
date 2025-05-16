from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from datetime import timedelta


class Policy(BaseModel):
    user_uuid: Optional[UUID] = None
    endpoint_uuid: Optional[UUID] = None
    resource: Optional[str] = None
    action: Optional[str] = None


Policies = list[Policy]


class Agreement(BaseModel):
    uuid: UUID
    policies: Policies
    lifespan: timedelta
    version: float
