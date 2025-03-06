"""
Author: Patrick Mahon
Contact: pmahon@sfu.ca
Date: 2024-07-25
Description: Mailer for user communications, access key distribution, etc.
"""
import os

from fastapi_mail import ConnectionConfig
from pydantic import BaseModel, EmailStr

# Configuration for FastAPI-Mail
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("OUTGOING_MAIL_PORT")),
    MAIL_SERVER=os.getenv("OUTGOING_MAIL_SERVER"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)


# Email schema
class EmailSchema(BaseModel):
    """Represents the schema for an email."""
    email: EmailStr
