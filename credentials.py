from google.oauth2.credentials import Credentials as BaseCredentials
import requests

import datetime

import config


class Credentials(BaseCredentials):
    """
    Google OAuth2 Credentials, modified to use auth-flow-provider to refresh instead of Google.
    This is required since refreshing the token through Google requires a client secret, and
    auth-flow-provider exists to keep the client secret hidden.
    """

    def refresh(self, _):
        if self._refresh_token:
            auth_response = requests.post(f"{config.AUTH_SERVICE_URL}/flows/google/refresh", json={
                "refresh_token": self._refresh_token
            })

            data = auth_response.json()

            self.token = data["access_token"]

            expiry = datetime.datetime.fromtimestamp(data["expiry_date"] // 1000, datetime.timezone.utc)
            expiry = expiry.replace(tzinfo=None)

            self.expiry = expiry
        else:
            super().refresh()
