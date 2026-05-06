"""
Shared utility functions.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Dict


def format_inr(amount: float) -> str:
    """Format a number as Indian Rupees with commas."""
    return f"₹{amount:,.2f}"


def safe_json_loads(text: str) -> Any:
    """Parse JSON from a string, stripping markdown code fences if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    return json.loads(text)


def month_label(date_str: str) -> str:
    """Convert 'YYYY-MM' to 'Mon YYYY' (e.g., '2025-03' → 'Mar 2025')."""
    return datetime.strptime(date_str + "-01", "%Y-%m-%d").strftime("%b %Y")


def transactions_to_table(transactions: List[Dict]) -> List[Dict]:
    """Prepare transactions for display (positive amounts, formatted dates)."""
    rows = []
    for t in transactions:
        rows.append({
            "Date": t["date"],
            "Description": t["description"],
            "Category": t.get("category", "Others"),
            "Merchant": t.get("merchant", "Unknown"),
            "Amount (₹)": abs(t["amount"]),
            "Type": "Expense" if t["amount"] < 0 else "Income",
        })
    return rows
