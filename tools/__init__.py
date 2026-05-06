"""
Tool registry — exports all agent tools as a flat list.
"""
from tools.transaction_fetcher import fetch_transactions
from tools.budget_analysis import analyze_budget
from tools.anomaly_detection import detect_anomalies
from tools.expense_forecasting import forecast_expenses
from tools.savings_advisor import generate_savings_advice

__all__ = [
    "fetch_transactions",
    "analyze_budget",
    "detect_anomalies",
    "forecast_expenses",
    "generate_savings_advice",
]


def get_all_tools() -> list:
    """Return all registered tools as a list for binding to the LLM."""
    return [
        fetch_transactions,
        analyze_budget,
        detect_anomalies,
        forecast_expenses,
        generate_savings_advice,
    ]
