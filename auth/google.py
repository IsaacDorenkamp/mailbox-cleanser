import requests
import time
import webbrowser

import config


class AuthorizationError(Exception):
    """
    An error raised when a step in the authorization flow fails.
    """


def run_authorization_flow(timeout: int = 75) -> dict[str, str]:
    end_time = time.time() + timeout

    session = requests.Session()
    auth_setup = session.post(f"{config.AUTH_SERVICE_URL}/flows/google")

    if auth_setup.status_code >= 400:
        raise AuthorizationError("Could not fetch authorization setup data.")

    response_data = auth_setup.json()
    auth_url, auth_key = response_data["url"], response_data["key"]

    webbrowser.open(auth_url)

    auth_result = None
    while time.time() <= end_time:
        auth_check = session.get(f"{config.AUTH_SERVICE_URL}/accept/{auth_key}")
        if auth_check.status_code == 200:
            auth_result = auth_check.json()
            break
    
    if not auth_result:
        raise AuthorizationError("Authorization timed out.")
    
    return auth_result
