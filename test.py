import asyncio
from src.connectors.sheets_connector import GSpreadSheetsConnector  # ✅ Correct import
from src.connectors.interfaces import ParsedExpense
from src.auth.credentials import CredentialProvider

async def main():
    SPREADSHEET_ID = "1q9plI3gVExNpFJCuKG2f1zER2ju93zFD-FW0iaFSJXs"
    WORKSHEET_NAME = "Expenses"

    print("initialzing cred provider...")

    credential_provider = CredentialProvider()
    
    print("initialzing gspread connector...")

    connector = GSpreadSheetsConnector(  # ✅ Use the concrete class
        credential_provider=credential_provider,
        spreadsheet_id=SPREADSHEET_ID,
        worksheet_name=WORKSHEET_NAME,
    )

    print("initialzing expense...")

    expense = ParsedExpense(
        date="2025-07-06",
        vendor="Example Corp",
        amount=42.99,
        currency="USD",
        category="Meals",
        description="Lunch with client"
    )

    print("calling record_expense()...")

    try:
        await connector.record_expense(expense)
        print("✅ Expense successfully recorded in Google Sheets.")
    except Exception as e:
        print(f"❌ Failed to record expense: {e}")

if __name__ == "__main__":
    asyncio.run(main())