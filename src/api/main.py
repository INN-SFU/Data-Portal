import os
import uuid

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from internal.authentication.auth import validate_credentials, validate_token, generate_token, decode_token
from casbin import Enforcer

# Load environment variables from .env file
load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Initialize Casbin enforcer
enforcer = Enforcer(os.getenv('ENFORCER_MODEL'), os.getenv('ENFORCER_ADAPTER'))


@app.get("/")
def read_root(request: Request):
    """
    Handler for the root endpoint.

    :param request: The incoming request object.
    :type request: Request
    :return: The rendered index.html template.
    :rtype: templates.TemplateResponse
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/auth")
def auth(request: Request):
    """
    Handler for the auth endpoint.

    :param request: The incoming request object.
    :type request: Request
    :return: The rendered auth.html template.
    :rtype: templates.TemplateResponse
    """

    uid = request.query_params.get("uid")
    password = request.query_params.get("key")
    print(uid)
    if not uid or not password:
        return {"error": "No UID or password provided"}

    if validate_credentials(uid, password):
        return {"success": "Valid credentials"}
    else:
        return {"error": "Invalid credentials"}


@app.get("/get_token")
def get_token(request: Request):
    """
    Handler for the generate token endpoint.

    :param request: The incoming request object.
    :type request: Request
    :return: The rendered get_token.html template.
    :rtype: templates.TemplateResponse
    """

    uid = request.query_params.get("uid")
    password = request.query_params.get("key")
    print(uid)
    if not uid or not password:
        return {"error": "No UID or password provided"}

    token = generate_token(uid, password, 5)
    return {"token": token}


@app.get("/validate_token")
def validate_token(request: Request):
    """
    Handler for the validate token endpoint.

    :param request: The incoming request object.
    :type request: Request
    :return: The rendered validate_token.html template.
    :rtype: templates.TemplateResponse
    """

    token = request.query_params.get("token")

    if not token:
        return {"error": "No token provided"}

    try:
        validate_token(token)
        return {"success": "Valid token"}
    except ExpiredSignatureError as e:
        return {"error": e.__str__()}
    except InvalidTokenError as e:
        return {"error": e.__str__()}
    except Exception as e:
        return {"error": e.__str__}


@app.get("/policies")
def read_data_access_policies(request: Request, document_id: str):
    """
    Handler for the data access policies endpoint.

    :param document_id: The ID of the data access policy document.
    :param request: The incoming request object.
    :type request: Request
    :return: The rendered data_access_policies.html template.
    :rtype: templates.TemplateResponse
    """

    return templates.TemplateResponse("policy_documents/" + document_id + ".html", {"request": request})


@app.get("/assets")
def read_assets(request: Request):
    """
    Retrieve assets for a given user.

    :param request: The HTTP request object.
    :return: A template response containing the assets HTML page for the specified user.
    """
    # Token Validation
    try:
        token = request.cookies.get("token")
    except ExpiredSignatureError as e:
        return {"error": e.__str__()}
    except InvalidTokenError as e:
        return {"error": e.__str__()}

    if not validate_token(token):
        return {"error": "No payload found in token"}
    else:
        # Payload Processing
        # get user_id's assets
        payload = decode_token(token)
        user_id = payload.get("user_id")

        if not user_id:
            return {"error": "Invalid token payload"}

        # Retrieve assets for user_id


        # Valid Response
        return templates.TemplateResponse("assets.html", {"request": request, "user_id": payload.user_id})
