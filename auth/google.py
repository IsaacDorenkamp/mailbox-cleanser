import datetime
import json
import time
import webbrowser

import requests

import config
from credentials import Credentials


class AuthorizationError(Exception):
    """
    An error raised when a step in the authorization flow fails.
    """


def run_authorization_flow(timeout: int = 75) -> Credentials:
    end_time = time.time() + timeout

    session = requests.Session()
    auth_setup = session.post(f"{config.AUTH_SERVICE_URL}/flows/google", json={
        "scopes": config.SCOPES
    })

    if auth_setup.status_code >= 400:
        try:
            response_data = auth_setup.json()
        except json.decoder.JSONDecodeError:
            response_data = {}

        raise AuthorizationError("Could not fetch authorization setup data. Reason: " + response_data.get("detail", "An unknown error occurred."))

    response_data = auth_setup.json()
    auth_flow, auth_url = response_data["flow"], response_data["url"]
    
    webbrowser.open(auth_url)

    auth_result = None
    while time.time() <= end_time:
        auth_check = session.get(f"{config.AUTH_SERVICE_URL}/flows/google/accept/{auth_flow}")
        if auth_check.status_code == 200:
            auth_result = auth_check.json()
            break

        time.sleep(1.0)
    
    if not auth_result:
        raise AuthorizationError("Authorization timed out.")
    
    print(auth_result)

    utc_expiry = datetime.datetime.fromtimestamp(auth_result["expiry_date"] // 1000, tz=datetime.timezone.utc)
    utc_expiry = utc_expiry.replace(tzinfo=None)
    
    result = Credentials(
        auth_result["access_token"],
        refresh_token=auth_result.get("refresh_token", None),
        expiry=utc_expiry
    )
    
    return result