import google.auth.exceptions
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

import os

from config import SCOPES, USER_CONFIG_DIR

global _creds
_creds: Credentials | None = None


def _run_authentication_flow():
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    return flow.run_local_server(port=0)


def get_credentials(force: bool = False) -> Credentials:
    global _creds

    token_path = os.path.join(USER_CONFIG_DIR, "token.json")

    if force:
        _creds = _run_authentication_flow()

        with open(token_path, "w") as token:
            token.write(_creds.to_json())
        
        return _creds

    if not _creds and os.path.exists(token_path):
        _creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not _creds or not _creds.valid:
        do_authorize = True
        if _creds and _creds.expired and _creds.refresh_token:
            try:
                _creds.refresh(Request())
                do_authorize = False
            except google.auth.exceptions.RefreshError:
                do_authorize = True
        
        if do_authorize:
            _creds = _run_authentication_flow()
        
        with open(token_path, "w") as token:
            token.write(_creds.to_json())

    return _creds
