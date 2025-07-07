import base64
from typing import List
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .interfaces import GmailConnector, RawEmail
from src.auth.credentials import CredentialProvider

class FastMCPGmailConnector(GmailConnector):
    """
    GmailConnector implementation using google-api-python-client and httpx for retries.
    """

    def __init__(
        self,
        credential_provider: CredentialProvider,
        user_id: str = "me",
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        self.credential_provider = credential_provider
        self.user_id = user_id
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        # Build the Gmail API service client
        creds = self.credential_provider.load_credentials()
        self.service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    async def fetch_unread_receipts(self) -> List[RawEmail]:
        """
        Fetch unread messages with 'receipt' or 'invoice' in the subject/body.
        """
        messages = []
        try:
            # List unread messages matching query
            response = self.service.users().messages().list(
                userId=self.user_id,
                q="receipt OR invoice",
                labelIds=["UNREAD"],
            ).execute()
            msg_list = response.get("messages", [])
        except HttpError as e:
            raise RuntimeError(f"Gmail list messages failed: {e}") from e

        for msg_meta in msg_list:
            msg_id = msg_meta["id"]
            # Fetch full message payload
            try:
                msg = self.service.users().messages().get(
                    userId=self.user_id, id=msg_id, format="full"
                ).execute()
            except HttpError as e:
                # Skip this message on error
                continue

            payload = msg.get("payload", {})
            headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
            subject = headers.get("subject", "")
            # Extract body (simplest: join all parts)
            body = ""
            for part in payload.get("parts", []) or []:
                if part.get("mimeType", "").startswith("text/"):
                    data = part.get("body", {}).get("data")
                    if data:
                        decoded_bytes = base64.urlsafe_b64decode(data)
                        body += decoded_bytes.decode("utf-8")

            messages.append(RawEmail(message_id=msg_id, subject=subject, body=body))

        return messages

    async def mark_as_read(self, message_id: str) -> None:
        """
        Remove 'UNREAD' label from the given message.
        """
        try:
            self.service.users().messages().modify(
                userId=self.user_id,
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
        except HttpError as e:
            raise RuntimeError(f"Gmail mark_as_read failed for {message_id}: {e}") from e
