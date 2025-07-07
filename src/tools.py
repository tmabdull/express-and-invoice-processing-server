from fastmcp import FastMCP
from typing import List
from src.connectors.interfaces import RawEmail, ParsedExpense
from src.connectors.gmail_connector import FastMCPGmailConnector
from src.connectors.expense_parser import DefaultExpenseParser
from src.connectors.sheets_connector import GSpreadSheetsConnector
from src.connectors.slack_connector import SlackWebConnector
from src.auth.credentials import CredentialProvider
from src.workflow import ExpenseWorkflow

from dotenv import load_dotenv
import os
load_dotenv()

# Instantiate shared providers and connectors
_creds = CredentialProvider()
_gmail_conn = FastMCPGmailConnector(credential_provider=_creds)
_parser = DefaultExpenseParser()
_sheets_conn = GSpreadSheetsConnector(
    credential_provider=_creds,
    spreadsheet_id=__import__("os").getenv("EXPENSE_SPREADSHEET_ID", ""),
)
_slack_conn = SlackWebConnector(
    bot_token=__import__("os").getenv("SLACK_BOT_TOKEN", ""),
    default_channel=__import__("os").getenv("SLACK_CHANNEL_ID", ""),
)

mcp = FastMCP(name="ExpenseProcessor")

@mcp.tool(name="fetch_receipts", description="Fetch unread expense receipt emails from Gmail")
async def fetch_receipts() -> List[RawEmail]:
    return await _gmail_conn.fetch_unread_receipts()


@mcp.tool(name="parse_expense", description="Parse a raw email into structured expense data")
def parse_expense(raw: RawEmail) -> ParsedExpense:
    return _parser.parse(raw)


@mcp.tool(name="record_expense", description="Append parsed expense as a new row in Google Sheets")
async def record_expense(expense: ParsedExpense) -> None:
    await _sheets_conn.record_expense(expense)


@mcp.tool(name="notify_slack", description="Send an approval request notification to Slack")
async def notify_slack(expense: ParsedExpense) -> None:
    # Format & send Slack notification
    
    # Build text and attachments dict here so 'attachments' is always a dict, not the model
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
            {
                "name": "approve",
                "text": "Approve",
                "type": "button",
                "style": "primary",
                "value": "approve",
            },
            {
                "name": "reject",
                "text": "Reject",
                "type": "button",
                "style": "danger",
                "value": "reject",
            },
        ],
    }

    await _slack_conn.send_notification(
        channel_id=None,
        message=text,
        attachments=attachments,
    )   

@mcp.tool(
    name="run_full_workflow",
    description="Fetch unread receipts, parse, record in Sheets, notify Slack, and mark as read"
)
async def run_full_workflow() -> None:
    # Instantiate workflow with the same connectors used above
    creds = CredentialProvider()
    workflow = ExpenseWorkflow(
        gmail_connector=FastMCPGmailConnector(credential_provider=creds),
        parser=DefaultExpenseParser(),
        sheets_connector=GSpreadSheetsConnector(
            credential_provider=creds,
            spreadsheet_id=os.getenv("EXPENSE_SPREADSHEET_ID", "")
        ),
        slack_connector=SlackWebConnector(
            bot_token=os.getenv("SLACK_BOT_TOKEN", ""),
            default_channel=os.getenv("SLACK_CHANNEL_ID", "")
        ),
    )
    await workflow.run()


def bootstrap_server() -> FastMCP:
    """
    Return the fully-bootstrapped FastMCP server.
    """
    return mcp
