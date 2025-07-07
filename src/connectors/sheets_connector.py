import asyncio
import time
from typing import List, Optional

import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound
from gspread.utils import ValueInputOption
from src.auth.credentials import CredentialProvider
from .interfaces import ParsedExpense, SheetsConnector


class GSpreadSheetsConnector(SheetsConnector):
    """
    SheetsConnector implementation using gspread.

    All gspread calls are executed in a background thread via `asyncio.to_thread`
    so the public interface remains fully async.
    """
        
    def __init__(
        self,
        credential_provider: CredentialProvider,
        spreadsheet_id: str,
        worksheet_name: str = "Expenses",
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        self._credential_provider = credential_provider
        self._spreadsheet_id = spreadsheet_id
        self._worksheet_name = worksheet_name
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor

        # Lazily instantiated gspread client and worksheet handle
        self._client: Optional[gspread.Client] = None
        self._worksheet_handle: Optional[gspread.Worksheet] = None

    # ----Internal Helpers----
    def _get_client(self) -> gspread.Client:
        """Create (or return cached) gspread client using refreshed creds."""
        if self._client is None:
            creds = self._credential_provider.get_sheets_credentials()
            self._client = gspread.authorize(creds)
        return self._client

    def _retry_sleep(self, attempt: int) -> None:
        """Exponential back-off helper."""
        delay = self._backoff_factor * (2 ** attempt)
        time.sleep(delay)
    # --------

    async def open_sheet(
        self, spreadsheet_id: str, worksheet_name: str
    ) -> gspread.Worksheet:
        """
        Open or create the worksheet and cache the handle internally.
        Returns the worksheet handle for downstream use.
        """
        def sync_open() -> gspread.Worksheet:
            client = self._get_client()

            # Open spreadsheet
            try:
                ss = client.open_by_key(spreadsheet_id)
            except SpreadsheetNotFound as exc:
                raise RuntimeError(f"Spreadsheet ID {spreadsheet_id} not found") from exc

            # Get or create worksheet
            try:
                ws = ss.worksheet(worksheet_name)
            except WorksheetNotFound:
                ws = ss.add_worksheet(title=worksheet_name, rows=1000, cols=20)

            self._worksheet_handle = ws
            return ws

        # to_thread runs sync_open in a thread and returns Worksheet, not a coroutine
        ws: gspread.Worksheet = await asyncio.to_thread(sync_open)
        return ws

    async def append_row(self, worksheet_handle: gspread.Worksheet, row: List[str]) -> None:
        """
        Append a single row to the given worksheet with retry/back-off.
        """
        def sync_append():
            attempt = 0
            while attempt <= self._max_retries:
                try:
                    # Use the correct enum value instead of string literal
                    worksheet_handle.append_row(row, value_input_option=ValueInputOption.user_entered)
                    return
                except APIError as exc:
                    status = getattr(exc.response, "status_code", None)
                    # Only retry on 429 / 5xx responses
                    if status and status >= 500:
                        if attempt == self._max_retries:
                            raise
                        self._retry_sleep(attempt)
                        attempt += 1
                        continue
                    raise  # Non-retryable error

        await asyncio.to_thread(sync_append)

    # Convenience wrapper
    async def record_expense(self, expense: ParsedExpense) -> None:
        """
        Helper that converts ParsedExpense → row and appends to the sheet.
        """
        # Ensure worksheet is open and handle is not None
        if self._worksheet_handle is None:
            self._worksheet_handle = await self.open_sheet(self._spreadsheet_id, self._worksheet_name)

        # Convert to list of strings
        row = [
            expense.date,
            expense.vendor,
            f"{expense.amount:.2f} {expense.currency}",
            expense.category or "",
            expense.description or "",
        ]
        
        # Now we can safely pass the non-None worksheet handle
        await self.append_row(self._worksheet_handle, row)
