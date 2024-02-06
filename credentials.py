import google.auth.exceptions
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

import os

from config import SCOPES, USER_CONFIG_DIR

global _creds
_creds: Credentials | None = None


def _run_authentication_flow():
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    return flow.run_local_server(port=0, timeout_seconds=60)


def get_saved_credentials() -> Credentials | None:
    token_path = os.path.join(USER_CONFIG_DIR, "token.json")
    
    if os.path.isfile(token_path):
        credentials = Credentials.from_authorized_user_file(token_path, SCOPES)
    else:
        return None
    
    if not credentials.valid:
        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except google.auth.exceptions.RefreshError:
                return None
            
            save_credentials(credentials)
        else:
            return None
    
    return credentials


def get_credentials_flow() -> Credentials | None:
    try:
        credentials = _run_authentication_flow()
        save_credentials(credentials)
        return credentials
    except AttributeError:
        # Raised in run_local_server when a timeout occurs
        raise TimeoutError("OAuth2 Flow timed out")


def save_credentials(credentials: Credentials):
    token_path = os.path.join(USER_CONFIG_DIR, "token.json")

    with open(token_path, "w") as token:
        token.write(credentials.to_json())
