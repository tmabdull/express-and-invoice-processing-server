# File: src/workflow/expense_workflow.py

import asyncio
from typing import List

from src.connectors.interfaces import RawEmail, ParsedExpense
from src.connectors.gmail_connector import FastMCPGmailConnector
from src.connectors.expense_parser import DefaultExpenseParser
from src.connectors.sheets_connector import GSpreadSheetsConnector
from src.connectors.slack_connector import SlackWebConnector


class ExpenseWorkflow:
    """
    Orchestrates the end-to-end expense processing workflow:
      1. Fetch unread receipts from Gmail
      2. Parse each email into a structured expense
      3. Record the expense in Google Sheets
      4. Send an approval request in Slack
      5. Mark the email as read
    """

    def __init__(
        self,
        gmail_connector: FastMCPGmailConnector,
        parser: DefaultExpenseParser,
        sheets_connector: GSpreadSheetsConnector,
        slack_connector: SlackWebConnector,
    ) -> None:
        self.gmail = gmail_connector
        self.parser = parser
        self.sheets = sheets_connector
        self.slack = slack_connector

    async def run(self) -> None:
        # 1. Fetch unread receipts
        raw_emails: List[RawEmail] = await self.gmail.fetch_unread_receipts()

        # 2. Process each email in parallel
        async def process_email(raw: RawEmail):
            try:
                # 2a. Parse into expense
                expense: ParsedExpense = self.parser.parse(raw)

                # 2b. Record in Sheets
                await self.sheets.record_expense(expense)

                # 2c. Notify in Slack
                text = (
                    "New Expense Submitted:\n"
                    f"• Date: {expense.date}\n"
                    f"• Vendor: {expense.vendor}\n"
                    f"• Amount: {expense.amount:.2f} {expense.currency}\n"
                    f"• Category: {expense.category or 'Uncategorized'}\n"
                    f"• Description: {expense.description or 'None'}"
                )
                attachments = {
                    "fallback": "Approve or reject the expense",
                    "callback_id": "expense_approval",
                    "actions": [
                        {"name": "approve", "text": "Approve", "type": "button", "style": "primary", "value": "approve"},
                        {"name": "reject",  "text": "Reject",  "type": "button", "style": "danger",  "value": "reject"},
                    ],
                }
                await self.slack.send_notification(
                    channel_id=self.slack.default_channel,
                    message=text,
                    attachments=attachments,
                )

                # 2d. Mark email as read
                await self.gmail.mark_as_read(raw.message_id)

            except Exception as e:
                # Log or handle per-email errors as needed
                # For now, print to stderr
                import sys
                print(f"Error processing email {raw.message_id}: {e}", file=sys.stderr)

        # Run all email processes concurrently, with a limit
        if raw_emails:
            # Limit concurrency to avoid API throttling
            sem = asyncio.Semaphore(5)

            async def sem_task(email: RawEmail):
                async with sem:
                    await process_email(email)

            await asyncio.gather(*(sem_task(e) for e in raw_emails))
