"""
Tool: Forecast next month's expenses using trend analysis and linear regression.
"""
import json
from collections import defaultdict
from langchain_core.tools import tool


@tool
def forecast_expenses(transactions_json: str) -> str:
    """
    Forecast next month's expenses for each spending category using linear trend analysis.

    Uses simple linear regression on monthly category totals to project next month's spend.
    Also computes an overall savings forecast based on expected income.

    Args:
        transactions_json: JSON string of transactions from fetch_transactions.

    Returns:
        JSON string with per-category forecasts, confidence levels, and total projected spend.
    """
    try:
        data = json.loads(transactions_json)
        if data.get("status") == "error":
            return transactions_json

        transactions = [t for t in data.get("transactions", []) if t["amount"] < 0]
        income_records = data.get("income", [])

        # Compute average monthly income
        salary = [i["amount"] for i in income_records if "salary" in i["description"].lower()]
        avg_income = sum(salary) / max(len(salary), 1) if salary else 85000.0

        # Aggregate monthly spend per category
        monthly_cat: dict = defaultdict(lambda: defaultdict(float))
        for txn in transactions:
            month = txn["date"][:7]
            cat = txn.get("category", "Others")
            monthly_cat[month][cat] += abs(txn["amount"])

        months = sorted(monthly_cat.keys())
        all_categories = set()
        for m in monthly_cat.values():
            all_categories.update(m.keys())

        def linear_forecast(values: list[float]) -> tuple[float, str]:
            """Simple linear regression to predict next value."""
            n = len(values)
            if n == 0:
                return 0.0, "low"
            if n == 1:
                return values[0], "low"

            x = list(range(n))
            x_mean = sum(x) / n
            y_mean = sum(values) / n
            numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
            denominator = sum((xi - x_mean) ** 2 for xi in x)
            slope = numerator / denominator if denominator != 0 else 0
            intercept = y_mean - slope * x_mean
            forecast_val = max(0.0, intercept + slope * n)

            # Confidence based on variance relative to mean
            if y_mean == 0:
                confidence = "low"
            else:
                variance = sum((v - y_mean) ** 2 for v in values) / n
                cv = (variance ** 0.5) / y_mean  # coefficient of variation
                confidence = "high" if cv < 0.15 else ("medium" if cv < 0.35 else "low")

            return round(forecast_val, 2), confidence

        category_forecasts = []
        total_forecast = 0.0

        for cat in sorted(all_categories):
            monthly_values = [monthly_cat[m].get(cat, 0.0) for m in months]
            forecast_val, confidence = linear_forecast(monthly_values)
            avg_val = round(sum(monthly_values) / len(monthly_values), 2) if monthly_values else 0
            trend = "increasing" if forecast_val > avg_val * 1.05 else (
                "decreasing" if forecast_val < avg_val * 0.95 else "stable"
            )

            category_forecasts.append({
                "category": cat,
                "forecasted_spend_inr": forecast_val,
                "average_historical_inr": avg_val,
                "trend": trend,
                "confidence": confidence,
                "monthly_history": [
                    {"month": m, "spend_inr": round(monthly_cat[m].get(cat, 0), 2)}
                    for m in months
                ],
            })
            total_forecast += forecast_val

        # Sort by forecasted amount descending
        category_forecasts.sort(key=lambda x: -x["forecasted_spend_inr"])

        projected_savings = round(avg_income - total_forecast, 2)
        savings_rate = round(projected_savings / avg_income * 100, 1) if avg_income else 0

        # Determine next month label
        from datetime import datetime
        if months:
            last_month = datetime.strptime(months[-1] + "-01", "%Y-%m-%d")
            from datetime import timedelta
            next_month = last_month.replace(day=28) + timedelta(days=4)
            next_month_label = next_month.strftime("%B %Y")
        else:
            next_month_label = "Next Month"

        return json.dumps({
            "status": "success",
            "forecast_month": next_month_label,
            "projected_income_inr": round(avg_income, 2),
            "projected_total_spend_inr": round(total_forecast, 2),
            "projected_savings_inr": projected_savings,
            "projected_savings_rate_pct": savings_rate,
            "category_forecasts": category_forecasts,
            "outlook": (
                "positive" if savings_rate >= 20
                else ("neutral" if savings_rate >= 10 else "concerning")
            ),
        }, indent=2)

    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})
