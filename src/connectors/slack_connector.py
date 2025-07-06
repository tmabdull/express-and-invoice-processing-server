import asyncio
import time
import json
from typing import Optional, Dict, Any

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .interfaces import SlackConnector


class SlackWebConnector(SlackConnector):
    """
    SlackConnector implementation using slack-sdk WebClient.
    Sends formatted expense notifications with approval buttons.
    """

    def __init__(
        self,
        bot_token: str,
        default_channel: str,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        self.client = WebClient(token=bot_token)
        self.default_channel = default_channel
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def _format_attachments(self, attachments: dict) -> str:
        """
        Convert an attachments dict into a JSON string as required by Slack.
        """
        # Wrap single attachment in a list
        return json.dumps([attachments])
    
    async def send_notification(
        self,
        channel_id: Optional[str] = None,
        message: Optional[str] = None,
        attachments: Optional[dict] = None,
    ) -> None:
        """
        Post a message to Slack, optionally with a single attachment dict:
        - channel_id: Slack channel ID (e.g. "C0123ABC")
        - message: plain-text message string
        - attachments: a dict of attachment fields (fallback, text, actions, etc.)
        """
        # Build a payload dict allowing non-str values
        payload: Dict[str, Any] = {
            "channel": channel_id or self.default_channel,
            "text": message,
        }

        if attachments:
            # Convert attachments dict → JSON string
            payload["attachments"] = self._format_attachments(attachments)

        attempt = 0
        while True:
            try:
                # Use asyncio.to_thread to avoid blocking
                await asyncio.to_thread(self.client.chat_postMessage, **payload)
                return
            except SlackApiError as exc:
                code = exc.response.status_code if exc.response else None
                # Retry on 429 or 5xx errors
                if code and (code == 429 or 500 <= code < 600) and attempt < self.max_retries:
                    delay = self.backoff_factor * (2 ** attempt)
                    time.sleep(delay)
                    attempt += 1
                    continue
                # Non-retryable or max retries reached
                raise RuntimeError(f"Slack send failed: {exc}") from exc
