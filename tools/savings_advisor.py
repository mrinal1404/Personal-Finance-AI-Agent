"""
Tool: Generate personalised, data-driven savings advice.
"""
import json
from langchain_core.tools import tool


@tool
def generate_savings_advice(
    budget_analysis_json: str,
    anomalies_json: str,
    forecast_json: str,
    user_constraints: str = "",
) -> str:
    """
    Generate personalised savings advice based on budget analysis, anomalies, and forecasts.

    Args:
        budget_analysis_json: Output from analyze_budget tool.
        anomalies_json: Output from detect_anomalies tool.
        forecast_json: Output from forecast_expenses tool.
        user_constraints: Comma-separated list of constraints (e.g., "rent is fixed,need gym").

    Returns:
        JSON string with prioritised savings recommendations, estimated savings, and 30-day plan.
    """
    try:
        budget = json.loads(budget_analysis_json)
        anomalies_data = json.loads(anomalies_json)
        forecast = json.loads(forecast_json)

        constraints = [c.strip().lower() for c in user_constraints.split(",") if c.strip()]
        recommendations = []

        # ── Analyse over-budget categories ───────────────────────────────────
        breakdown = budget.get("category_breakdown", [])
        income = budget.get("monthly_income_inr", 85000)

        for cat_data in breakdown:
            cat = cat_data["category"]
            overspend = cat_data.get("overspend_inr", 0)
            avg_spend = cat_data.get("avg_monthly_spend_inr", 0)

            # Skip if user flagged this as a constraint
            if any(c in cat.lower() for c in constraints):
                continue

            if cat == "Food & Dining" and overspend > 0:
                food_delivery_spend = sum(
                    m["total"] for m in cat_data.get("top_merchants", [])
                    if any(app in m["merchant"].lower() for app in ["swiggy", "zomato", "uber", "zepto"])
                )
                if food_delivery_spend > 3000:
                    saving = round(food_delivery_spend * 0.3, 0)
                    recommendations.append({
                        "rank": 1,
                        "category": cat,
                        "action": "Reduce food delivery frequency",
                        "detail": (
                            f"You spend ₹{food_delivery_spend:,.0f}/month on delivery apps. "
                            f"Cooking at home 3 extra days/week could save ₹{saving:,.0f}/month."
                        ),
                        "estimated_monthly_saving_inr": saving,
                        "difficulty": "medium",
                        "impact": "high",
                        "quick_wins": [
                            "Set a weekly delivery app budget of ₹800",
                            "Meal-prep on Sundays to reduce weekday orders",
                            "Use Swiggy/Zomato only on weekends",
                        ],
                    })

            elif cat == "Shopping" and overspend > 0:
                saving = round(min(overspend, avg_spend * 0.25), 0)
                recommendations.append({
                    "rank": 2,
                    "category": cat,
                    "action": "Apply a 48-hour rule for non-essential purchases",
                    "detail": (
                        f"You're over budget on Shopping by ₹{overspend:,.0f}/month. "
                        f"A 48-hour waiting period before buying non-essentials typically cuts "
                        f"impulse spend by 25%, saving ~₹{saving:,.0f}/month."
                    ),
                    "estimated_monthly_saving_inr": saving,
                    "difficulty": "easy",
                    "impact": "high",
                    "quick_wins": [
                        "Unsubscribe from Myntra/Amazon sale notifications",
                        "Move wishlist items to a 'Review in 48h' list",
                        "Set a monthly shopping budget of ₹3,000",
                    ],
                })

            elif cat == "Entertainment" and overspend > 0:
                saving = round(overspend * 0.5, 0)
                recommendations.append({
                    "rank": 3,
                    "category": cat,
                    "action": "Audit and consolidate streaming subscriptions",
                    "detail": (
                        f"You have multiple subscriptions (Netflix, Spotify, Amazon Prime, etc.). "
                        f"Consolidating to 2-3 services saves ~₹{saving:,.0f}/month."
                    ),
                    "estimated_monthly_saving_inr": saving,
                    "difficulty": "easy",
                    "impact": "medium",
                    "quick_wins": [
                        "Cancel one streaming service this week",
                        "Share a family plan for Netflix (₹649 → ₹325 per person)",
                        "Use free tiers of Spotify / YouTube",
                    ],
                })

        # ── Add SIP/investment recommendation if savings rate is low ─────────
        savings_rate = budget.get("savings_rate_percentage", 0)
        if savings_rate < 20:
            current_savings = budget.get("avg_monthly_savings_inr", 0)
            target_sip = round(income * 0.15, 0)
            recommendations.append({
                "rank": 4,
                "category": "Savings & Investment",
                "action": "Start a ₹{:,.0f}/month SIP immediately".format(target_sip),
                "detail": (
                    f"Your current savings rate is {savings_rate}% (₹{current_savings:,.0f}/month). "
                    f"The 50-30-20 rule recommends saving at least 20%. A ₹{target_sip:,.0f}/month "
                    f"SIP in an index fund (e.g., Nifty 50) could grow to ₹{target_sip*200:,.0f} "
                    f"in 10 years at 12% CAGR."
                ),
                "estimated_monthly_saving_inr": target_sip,
                "difficulty": "easy",
                "impact": "very_high",
                "quick_wins": [
                    "Set up auto-debit SIP on the 1st of each month",
                    "Use Zerodha Coin or Groww for zero-commission index funds",
                    "Start with ₹5,000/month and increase by 10% annually",
                ],
            })

        # ── Anomaly-based recommendations ────────────────────────────────────
        high_anomalies = [a for a in anomalies_data.get("anomalies", []) if a["severity"] == "high"]
        if high_anomalies:
            amt = sum(a.get("amount_inr", 0) for a in high_anomalies if "amount_inr" in a)
            recommendations.append({
                "rank": 5,
                "category": "Anomalies",
                "action": "Review and dispute suspicious transactions",
                "detail": (
                    f"Found {len(high_anomalies)} high-severity anomalies totalling "
                    f"~₹{amt:,.0f}. Review these transactions immediately for potential "
                    f"errors or fraud."
                ),
                "estimated_monthly_saving_inr": round(amt * 0.1, 0),
                "difficulty": "easy",
                "impact": "high",
                "quick_wins": [
                    f"Review transaction: {high_anomalies[0].get('description', high_anomalies[0].get('message', '')[:50])}",
                    "Enable UPI transaction alerts on your banking app",
                    "Set a per-transaction SMS alert threshold of ₹500",
                ],
            })

        # ── Sort and compute totals ───────────────────────────────────────────
        recommendations.sort(key=lambda r: -r["estimated_monthly_saving_inr"])
        total_potential_saving = sum(r["estimated_monthly_saving_inr"] for r in recommendations)

        # ── 30-day action plan ────────────────────────────────────────────────
        action_plan = [
            {"week": 1, "actions": [
                "Review all subscriptions and cancel at least one",
                "Set up budget alerts on your banking app for each category",
                "Plan 3 home-cooked meals this week instead of ordering",
            ]},
            {"week": 2, "actions": [
                "Open a Zerodha/Groww account if not already done",
                "Set up a ₹{:,.0f}/month SIP auto-debit".format(round(income * 0.10, 0)),
                "Create a shopping wishlist — buy only after 48 hours",
            ]},
            {"week": 3, "actions": [
                "Review this month's bank statement for duplicate charges",
                "Meal-prep on Sunday to cover 3 weekday lunches",
                "Unsubscribe from promotional e-mails / push notifications",
            ]},
            {"week": 4, "actions": [
                "Track all expenses for the week manually to build awareness",
                "Calculate your actual savings rate vs target (20%)",
                "Review and update your budget limits for next month",
            ]},
        ]

        return json.dumps({
            "status": "success",
            "recommendations": recommendations,
            "total_potential_monthly_saving_inr": round(total_potential_saving, 2),
            "annual_saving_potential_inr": round(total_potential_saving * 12, 2),
            "thirty_day_action_plan": action_plan,
            "constraints_respected": constraints,
        }, indent=2)

    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})
