from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel


class AddUserRequest(BaseModel):
    username: str
    email: str
    roles: list


class AddUserResponse(BaseModel):
    success: bool
    details: dict
