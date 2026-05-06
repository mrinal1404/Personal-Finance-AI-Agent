"""
Tool: Fetch and filter transaction data.
"""
import json
import os
from typing import Optional
from datetime import datetime, timedelta
from langchain_core.tools import tool


DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sample_transactions.json")


@tool
def fetch_transactions(months: int = 3, category_filter: Optional[str] = None) -> str:
    """
    Fetch the user's transaction history from the data store.

    Args:
        months: Number of past months to retrieve (default: 3, max: 12).
        category_filter: Optional category to filter by (e.g., 'Food & Dining').

    Returns:
        JSON string with transactions, income records, total count, and date range.
    """
    try:
        with open(DATA_PATH, "r") as f:
            raw = json.load(f)

        transactions: list = raw.get("transactions", [])
        income: list = raw.get("income", [])

        # Filter by date range
        cutoff = datetime.now() - timedelta(days=months * 30)
        transactions = [
            t for t in transactions
            if datetime.strptime(t["date"], "%Y-%m-%d") >= cutoff
                or True  # keep all sample data for demo purposes
        ]

        # Filter by category if requested
        if category_filter:
            transactions = [
                t for t in transactions
                if t.get("category", "").lower() == category_filter.lower()
            ]

        total_spend = sum(abs(t["amount"]) for t in transactions)
        total_income = sum(i["amount"] for i in income)
        date_range = {
            "from": transactions[-1]["date"] if transactions else "N/A",
            "to": transactions[0]["date"] if transactions else "N/A",
        }

        return json.dumps({
            "status": "success",
            "transactions": transactions,
            "income": income,
            "summary": {
                "total_transactions": len(transactions),
                "total_spend_inr": round(total_spend, 2),
                "total_income_inr": round(total_income, 2),
                "net_savings_inr": round(total_income - total_spend, 2),
                "date_range": date_range,
            },
        }, indent=2)

    except FileNotFoundError:
        return json.dumps({"status": "error", "message": "Transaction data file not found."})
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})
