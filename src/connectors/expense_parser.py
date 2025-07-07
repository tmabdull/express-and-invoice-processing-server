from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import re
import base64
from pydantic import ValidationError
from .interfaces import ExpenseParser, RawEmail, ParsedExpense

# Type alias for a parsing step function
ParseStep = Callable[[Dict[str, Any]], Dict[str, Any]]

# Changed decode_body signature to accept the full context:
def decode_body(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decode any Base64 URL-safe encoded parts of the email body,
    and return a dict with raw text under 'body_text'.
    """
    raw: RawEmail = context["raw"]
    try:
        decoded = base64.urlsafe_b64decode(raw.body + "===")  # pad if needed
        body_text = decoded.decode("utf-8", errors="ignore")
    except Exception:
        body_text = raw.body
    return {"body_text": body_text, "subject": raw.subject}

def extract_fields(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract date, vendor, amount, currency, category, description from body_text.
    Uses regexes for common patterns.
    """
    text = context["body_text"]
    # Date: formats like YYYY-MM-DD or MM/DD/YYYY
    date_match = re.search(r"(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})", text)
    raw_date = date_match.group(1) if date_match else ""
    # Amount & currency, e.g. $123.45 or 123.45 USD
    amt_match = re.search(r"([$€£]?)(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)(?:\s*(USD|EUR|GBP))?", text)
    currency_symbol, amt_str, currency_code = amt_match.groups() if amt_match else ("", "0", None)
    # Normalize amount
    amount = float(amt_str.replace(",", ""))
    # Normalize currency
    symbol_map = {"$": "USD", "€": "EUR", "£": "GBP"}
    currency = currency_code or symbol_map.get(currency_symbol, "USD")
    # Vendor: assume first line or 'Vendor: X' pattern
    vendor_match = re.search(r"Vendor[:\-]\s*(.+)", text)
    if vendor_match:
        vendor = vendor_match.group(1).strip().splitlines()[0]
    else:
        vendor = context["subject"] or "Unknown"
    # Category & description: optional patterns
    cat_match = re.search(r"Category[:\-]\s*(.+)", text)
    category = cat_match.group(1).strip() if cat_match else None
    desc_match = re.search(r"Description[:\-]\s*(.+)", text)
    description = desc_match.group(1).strip() if desc_match else None

    return {
        "date": raw_date,
        "vendor": vendor,
        "amount": amount,
        "currency": currency,
        "category": category,
        "description": description,
    }

def normalize_formats(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert date to ISO 8601 (YYYY-MM-DD) and ensure currency code is uppercase.
    """
    # Normalize date
    dt = None
    raw_date = context["date"]
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            dt = datetime.strptime(raw_date, fmt)
            break
        except Exception:
            continue
    iso_date = dt.date().isoformat() if dt else raw_date

    # Uppercase currency
    currency = context["currency"].upper() if context.get("currency") else None

    return {"date": iso_date, "currency": currency}

def build_parsed_expense(context: Dict[str, Any]) -> ParsedExpense:
    """
    Validate and construct the ParsedExpense model via Pydantic.
    """
    try:
        return ParsedExpense(**context)
    except ValidationError as ve:
        # Propagate or wrap as needed
        raise ve

class DefaultExpenseParser(ExpenseParser):
    """
    ExpenseParser implementation with a pluggable pipeline.
    """

    def __init__(self, steps: Optional[List[ParseStep]] = None):
        # Default pipeline: decode → extract → normalize → build model
        self.steps = steps or [
            decode_body,
            extract_fields,
            normalize_formats,
        ]

    def parse(self, raw_email: RawEmail) -> ParsedExpense:
        # Initialize context with the raw email object
        context: Dict[str, Any] = {"raw": raw_email}
        # Run each step in sequence, merging results into context
        for step in self.steps:
            result = step(context)
            context.update(result)
        # Build and return the Pydantic model
        return build_parsed_expense(context)
