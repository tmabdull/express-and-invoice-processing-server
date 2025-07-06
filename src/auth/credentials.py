import os
from typing import Optional, Union, List, cast
from google.auth.credentials import Credentials as BaseCredentials
from google.oauth2.credentials import Credentials as OAuth2Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

class CredentialProvider:
    """
    Loads, refreshes, and supplies OAuth2 Credentials for Google APIs.
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
        self._creds: Optional[Union[BaseCredentials, OAuth2Credentials]] = None

    def load_credentials(self) -> OAuth2Credentials:
        """
        Load credentials from disk or run OAuth flow if necessary.
        Always returns an OAuth2Credentials instance.
        """
        # Return cached valid creds
        if (
            self._creds
            and isinstance(self._creds, OAuth2Credentials)
            and self._creds.valid
        ):
            return self._creds

        creds: OAuth2Credentials

        # Load from file if present
        if os.path.exists(self.token_file):
            creds = OAuth2Credentials.from_authorized_user_file(
                self.token_file, scopes=self.scopes
            )
        else:
            client_config = {
                "installed": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [
                        "urn:ietf:wg:oauth:2.0:oob",
                        "http://localhost"
                    ]
                }
            }
            flow = InstalledAppFlow.from_client_config(
                client_config=client_config,
                scopes=self.scopes
            )

            # Cast tells the type‐checker “I know this call returns the Google OAuth2 credentials type” 
            # Guarantees .refresh_token and .to_json() methods exist on creds.
            # Makes self._creds = creds acceptable because OAuth2Credentials is a subtype of your Union type.
            creds = cast(OAuth2Credentials, flow.run_local_server(port=0))
        
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        # Persist OAuth2Credentials
        with open(self.token_file, "w") as token:
            token.write(creds.to_json())

        # Store in the provider as the common BaseCredentials type
        self._creds = creds  
        return creds

    def get_gmail_credentials(self) -> OAuth2Credentials:
        """Return valid Gmail Credentials."""
        return self.load_credentials()

    def get_sheets_credentials(self) -> OAuth2Credentials:
        """Return valid Google Sheets Credentials."""
        return self.load_credentials()
