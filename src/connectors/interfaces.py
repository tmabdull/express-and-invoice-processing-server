from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel
from gspread import Worksheet


class RawEmail(BaseModel):
    message_id: str
    subject: str
    body: str
    # add other raw fields as needed


class ParsedExpense(BaseModel):
    date: str
    vendor: str
    amount: float
    currency: str
    category: Optional[str]
    description: Optional[str]


class GmailConnector(ABC):
    @abstractmethod
    async def fetch_unread_receipts(self) -> List[RawEmail]:
        """Retrieve unread emails matching configured receipt queries."""
        pass

    @abstractmethod
    async def mark_as_read(self, message_id: str) -> None:
        """Mark a message as read in Gmail."""
        pass


class ExpenseParser(ABC):
    @abstractmethod
    def parse(self, raw_email: RawEmail) -> ParsedExpense:
        """Convert a RawEmail into a ParsedExpense model."""
        pass


class SheetsConnector(ABC):
    @abstractmethod
    async def open_sheet(self, spreadsheet_id: str, worksheet_name: str) -> Worksheet:
        """Open or create a worksheet handle for appending rows."""
        pass

    @abstractmethod
    async def append_row(self, worksheet_handle, row: List[str]) -> None:
        """Append a row of strings to the given worksheet."""
        pass


class SlackConnector(ABC):
    @abstractmethod
    async def send_notification(
        self,
        channel_id: str,
        message: str,
        attachments: Optional[dict] = None,
    ) -> None:
        """Post a formatted approval notification to Slack."""
        pass
