from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from config import SCOPES
import context


def _run_authentication_flow():
    flow = InstalledAppFlow.from_client_secrets_file(context.get_resource("credentials.json"), SCOPES)
    return flow.run_local_server(port=0, timeout_seconds=60)


def get_credentials_flow() -> Credentials | None:
    try:
        credentials = _run_authentication_flow()
        return credentials
    except AttributeError:
        # Raised in run_local_server when a timeout occurs
        raise TimeoutError("OAuth2 Flow timed out")
