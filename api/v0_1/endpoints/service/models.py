from typing import Dict, Type

from pydantic import BaseModel, Field

from core.management.policies import Policy
from core.management.users.models import User


class GetAssetRequest(BaseModel):
    resource: str = Field(..., description="The resource to be accessed.")
    access_point: str = Field(..., description="The name of the access point.")
    action: str = Field(..., description="The action to be performed on the resource.")


class GetAssetResponse(BaseModel):
    presigned_urls: list[str] = Field(..., description="The presigned URLs for the asset.")
    file_paths: list[str] = Field(..., description="The file paths for the asset.")


class PutAssetRequest(BaseModel):
    resource: str = Field(..., description="Target path/key to write to (e.g. 'folder/sub/file.txt').")
    access_point: str = Field(..., description="Name of the storage access point.")


class PutAssetResponse(BaseModel):
    presigned_urls: list[str] = Field(..., description="List of presigned PUT URLs (one per file).")
    file_paths: list[str] = Field(..., description="List of file paths these URLs correspond to.")


class AddUserRequest(BaseModel):
    username: str = Field(..., description="The username of the user.")
    email: str = Field(..., description="The email of the user.")
    roles: list[str] = Field(..., description="The roles of the user.")


class AddUserResponse(BaseModel):
    success: bool = Field(..., description="Indicates whether the user was successfully added.")
    details: User = Field(..., description="The details of the user that was added.")


class RemoveUserResponse(BaseModel):
    success: bool = Field(..., description="Indicates whether the user was successfully removed.")
    details: User = Field(None, description="The details of the user that was removed.")


class AddPolicyRequest(BaseModel):
    username: str = Field(..., description="The username of the user.")
    endpoint_name: str = Field(..., description="The name of the endpoint.")
    resource: str = Field(..., description="The resource to be accessed.")
    action: str = Field(..., description="The action to be performed on the resource.")


class AddPolicyResponse(BaseModel):
    success: bool = Field(..., description="Indicates whether the policies were successfully updated.")
    details: list[Policy] = Field(..., description="The details of the policies that were updated.")


class RemovePolicyRequest(BaseModel):
    username: str = Field(..., description="The username of the user.")
    endpoint_name: str = Field(..., description="The name of the endpoint.")
    resource: str = Field(..., description="The resource to be accessed.")
    action: str = Field(..., description="The action to be performed on the resource.")


class RemovePolicyResponse(BaseModel):
    success: bool = Field(..., description="Indicates whether the policies were successfully removed.")
    details: list[Policy] = Field(..., description="The details of the policies that were removed.")


class GetPolicyResponse(BaseModel):
    success: bool = Field(..., description="Indicates whether the policies were successfully retrieved.")
    details: list[Policy] = Field(..., description="The details of the policies that were retrieved.")


# Model registration structure
model_registry: Dict[str, Type[BaseModel]] = {}


def register_model(model_name: str, model_class: Type[BaseModel], endpoint: str):
    """Registers a model and its associated endpoint."""
    model_registry[model_name] = {
        "model_class": model_class,
        "endpoint": endpoint
    }


# Register models

register_model("AddUserRequest", AddUserRequest, "/admin/user/")
register_model("AddUserResponse", AddUserResponse, "/admin/user/")
register_model("RemoveUserResponse", RemoveUserResponse, "/admin/user/")
register_model("GetPolicyResponse", GetPolicyResponse, "/admin/policy/")
register_model("AddPolicyResponse", AddPolicyResponse, "/admin/policy/")
register_model("AddPolicyRequest", AddPolicyRequest, "/admin/policy/")
register_model("RemovePolicyRequest", RemovePolicyRequest, "/admin/policy/")
register_model("RemovePolicyResponse", RemovePolicyResponse, "/admin/policy/")
register_model("GetPolicyResponse", GetPolicyResponse, "/admin/policy/")
