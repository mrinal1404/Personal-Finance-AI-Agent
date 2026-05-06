"""
Tool: Analyse spending by category and compare against budget limits.
"""
import json
import os
from collections import defaultdict
from langchain_core.tools import tool


CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "categories.json")


@tool
def analyze_budget(transactions_json: str, monthly_income: float = 85000.0) -> str:
    """
    Analyse spending patterns by category and compare with recommended budget percentages.

    Args:
        transactions_json: JSON string of transactions (output from fetch_transactions).
        monthly_income: User's average monthly take-home income in INR.

    Returns:
        JSON string with per-category spending breakdown, budget status, and overspending alerts.
    """
    try:
        data = json.loads(transactions_json)
        if data.get("status") == "error":
            return transactions_json

        transactions = data.get("transactions", [])
        income_records = data.get("income", [])

        # Determine actual monthly income from records if available
        if income_records:
            salary_income = [i for i in income_records if "salary" in i["description"].lower()]
            if salary_income:
                monthly_income = sum(i["amount"] for i in salary_income) / max(len(salary_income), 1)

        with open(CATEGORIES_PATH) as f:
            cat_config = json.load(f)

        # Aggregate spend per category per month
        monthly_category_spend: dict = defaultdict(lambda: defaultdict(float))
        category_transactions: dict = defaultdict(list)

        for txn in transactions:
            if txn["amount"] >= 0:
                continue  # skip income/refunds
            month_key = txn["date"][:7]  # "YYYY-MM"
            cat = txn.get("category", "Others")
            monthly_category_spend[month_key][cat] += abs(txn["amount"])
            category_transactions[cat].append(txn)

        months = list(monthly_category_spend.keys())
        num_months = max(len(months), 1)

        # Compute average monthly spend per category
        avg_by_category: dict = defaultdict(float)
        for month_data in monthly_category_spend.values():
            for cat, amt in month_data.items():
                avg_by_category[cat] += amt
        avg_by_category = {k: round(v / num_months, 2) for k, v in avg_by_category.items()}

        # Build breakdown with budget comparison
        breakdown = []
        total_avg_spend = sum(avg_by_category.values())
        categories_config = cat_config.get("categories", {})

        for cat, avg_spend in sorted(avg_by_category.items(), key=lambda x: -x[1]):
            budget_pct = categories_config.get(cat, {}).get("budget_percentage", 5)
            budget_limit = monthly_income * budget_pct / 100
            pct_of_income = round(avg_spend / monthly_income * 100, 1)
            overspend = round(avg_spend - budget_limit, 2)
            color = categories_config.get(cat, {}).get("color", "#BDC3C7")

            top_merchants = {}
            for txn in category_transactions[cat]:
                m = txn.get("merchant", "Unknown")
                top_merchants[m] = top_merchants.get(m, 0) + abs(txn["amount"])
            top_merchants_sorted = sorted(top_merchants.items(), key=lambda x: -x[1])[:3]

            breakdown.append({
                "category": cat,
                "avg_monthly_spend_inr": avg_spend,
                "budget_limit_inr": round(budget_limit, 2),
                "budget_percentage_recommended": budget_pct,
                "actual_percentage_of_income": pct_of_income,
                "overspend_inr": overspend,
                "status": "over_budget" if overspend > 0 else "within_budget",
                "color": color,
                "top_merchants": [{"merchant": m, "total": round(v, 2)} for m, v in top_merchants_sorted],
                "transaction_count": len(category_transactions[cat]),
            })

        overspend_categories = [b for b in breakdown if b["status"] == "over_budget"]
        savings_opportunity = round(sum(b["overspend_inr"] for b in overspend_categories), 2)

        return json.dumps({
            "status": "success",
            "monthly_income_inr": round(monthly_income, 2),
            "avg_monthly_spend_inr": round(total_avg_spend, 2),
            "avg_monthly_savings_inr": round(monthly_income - total_avg_spend, 2),
            "savings_rate_percentage": round((monthly_income - total_avg_spend) / monthly_income * 100, 1),
            "months_analysed": num_months,
            "category_breakdown": breakdown,
            "overspend_categories": [b["category"] for b in overspend_categories],
            "total_savings_opportunity_inr": savings_opportunity,
        }, indent=2)

    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})
