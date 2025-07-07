from typing import Optional, List
from google.auth.credentials import Credentials as BaseCredentials
from google.oauth2.credentials import Credentials as OAuth2Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow

from src.auth.oauth_callback_server import wait_for_callback

from dotenv import load_dotenv
import os
load_dotenv()

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

class CredentialProvider:
    """
    Provides OAuth2 Credentials via a Web‐Server flow.
    """

    def __init__(
        self,
        client_id_env: str = "GOOGLE_CLIENT_ID",
        client_secret_env: str = "GOOGLE_CLIENT_SECRET",
        token_file: str = ".google_token.json",
        scopes: Optional[List[str]] = None,
    ):
        self.client_id = os.getenv(client_id_env)
        self.client_secret = os.getenv(client_secret_env)
        self.token_file = token_file
        self.scopes = scopes or [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/spreadsheets",
        ]
        self._creds: Optional[BaseCredentials] = None

    def load_credentials(self) -> BaseCredentials:
        """
        Load credentials from disk or run Web‐Server OAuth flow if necessary.
        Returns a BaseCredentials instance (e.g. OAuth2Credentials).
        """
        # 1) Reuse cached valid credentials
        if self._creds and self._creds.valid:
            return self._creds

        creds: BaseCredentials

        # 2) Load from token file if it exists
        if os.path.exists(self.token_file):
            creds = OAuth2Credentials.from_authorized_user_file(
                self.token_file, scopes=self.scopes
            )
        else:
            # 3) Run Web Application Flow
            redirect_url: str = "http://localhost:8080/callback"
            # redirect_url = "https://5481-2601-644-8001-7440-5db4-b47d-6b6d-e234.ngrok-free.app/callback"

            client_config = {
                "web": {
                    "client_id":     self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
                    "token_uri":     "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_url],
                }
            }
            flow = Flow.from_client_config(
                client_config=client_config,
                scopes=self.scopes,
                redirect_uri=redirect_url,
            )

            auth_url, _ = flow.authorization_url(
                access_type="offline",
                prompt="consent",
            )
            print(f"Visit this URL to authorize the application:\n\n{auth_url}\n")

            # Wait for your Flask callback to capture the full redirect URL...
            authorization_response = wait_for_callback()

            flow.fetch_token(authorization_response=authorization_response)
            creds = flow.credentials  # type: BaseCredentials

        # 4) Refresh if expired
        if creds.expired and hasattr(creds, "refresh_token") and creds.refresh_token:
            creds.refresh(Request())

        # 5) Persist for reuse
        with open(self.token_file, "w") as token:
            token.write(creds.to_json())

        self._creds = creds
        return creds

    def get_gmail_credentials(self) -> BaseCredentials:
        """Return valid credentials for Gmail API."""
        return self.load_credentials()

    def get_sheets_credentials(self) -> BaseCredentials:
        """Return valid credentials for Sheets API."""
        return self.load_credentials()
