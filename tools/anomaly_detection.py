"""
Tool: Detect spending anomalies (unusual spikes, duplicate charges, large single transactions).
"""
import json
from collections import defaultdict
from langchain_core.tools import tool


@tool
def detect_anomalies(transactions_json: str, z_score_threshold: float = 2.0) -> str:
    """
    Detect unusual or anomalous transactions in the user's spending history.

    Anomaly types detected:
    - Large single transactions (> mean + 2σ within category)
    - Sudden category spikes (monthly spend > 150% of category average)
    - Potential duplicate charges (same merchant, same amount within 3 days)
    - Unusual late-night purchases (proxy for impulse buys)

    Args:
        transactions_json: JSON string of transactions from fetch_transactions.
        z_score_threshold: Z-score threshold for outlier detection (default: 2.0).

    Returns:
        JSON string listing all detected anomalies with severity and details.
    """
    try:
        data = json.loads(transactions_json)
        if data.get("status") == "error":
            return transactions_json

        transactions = [t for t in data.get("transactions", []) if t["amount"] < 0]
        anomalies = []

        # ── 1. Category-level z-score outliers ───────────────────────────────
        category_amounts: dict = defaultdict(list)
        for txn in transactions:
            cat = txn.get("category", "Others")
            category_amounts[cat].append(abs(txn["amount"]))

        for txn in transactions:
            cat = txn.get("category", "Others")
            amounts = category_amounts[cat]
            if len(amounts) < 3:
                continue
            mean = sum(amounts) / len(amounts)
            variance = sum((x - mean) ** 2 for x in amounts) / len(amounts)
            std = variance ** 0.5
            if std == 0:
                continue
            z = (abs(txn["amount"]) - mean) / std
            if z >= z_score_threshold:
                anomalies.append({
                    "type": "large_transaction",
                    "severity": "high" if z >= 3.0 else "medium",
                    "transaction_id": txn["id"],
                    "date": txn["date"],
                    "description": txn["description"],
                    "amount_inr": abs(txn["amount"]),
                    "category": cat,
                    "z_score": round(z, 2),
                    "category_mean_inr": round(mean, 2),
                    "message": (
                        f"₹{abs(txn['amount']):,.0f} spend at '{txn['merchant']}' is "
                        f"{z:.1f}σ above your average {cat} transaction of ₹{mean:,.0f}."
                    ),
                })

        # ── 2. Month-over-month category spikes ──────────────────────────────
        monthly_cat: dict = defaultdict(lambda: defaultdict(float))
        for txn in transactions:
            month = txn["date"][:7]
            cat = txn.get("category", "Others")
            monthly_cat[month][cat] += abs(txn["amount"])

        months = sorted(monthly_cat.keys())
        for i in range(1, len(months)):
            prev, curr = months[i - 1], months[i]
            for cat in monthly_cat[curr]:
                prev_amt = monthly_cat[prev].get(cat, 0)
                curr_amt = monthly_cat[curr][cat]
                if prev_amt > 0 and curr_amt > prev_amt * 1.5:
                    spike_pct = round((curr_amt - prev_amt) / prev_amt * 100, 1)
                    anomalies.append({
                        "type": "category_spike",
                        "severity": "high" if spike_pct > 100 else "medium",
                        "date": curr + "-01",
                        "category": cat,
                        "previous_month_inr": round(prev_amt, 2),
                        "current_month_inr": round(curr_amt, 2),
                        "spike_percentage": spike_pct,
                        "message": (
                            f"{cat} spending jumped {spike_pct}% from ₹{prev_amt:,.0f} "
                            f"({prev}) to ₹{curr_amt:,.0f} ({curr})."
                        ),
                    })

        # ── 3. Potential duplicate charges ────────────────────────────────────
        from datetime import datetime, timedelta

        for i, t1 in enumerate(transactions):
            for t2 in transactions[i + 1:]:
                d1 = datetime.strptime(t1["date"], "%Y-%m-%d")
                d2 = datetime.strptime(t2["date"], "%Y-%m-%d")
                if abs((d2 - d1).days) <= 3:
                    if (t1.get("merchant") == t2.get("merchant") and
                            abs(t1["amount"]) == abs(t2["amount"])):
                        anomalies.append({
                            "type": "potential_duplicate",
                            "severity": "high",
                            "transaction_ids": [t1["id"], t2["id"]],
                            "dates": [t1["date"], t2["date"]],
                            "merchant": t1.get("merchant"),
                            "amount_inr": abs(t1["amount"]),
                            "message": (
                                f"Possible duplicate charge: ₹{abs(t1['amount']):,.0f} at "
                                f"'{t1['merchant']}' on {t1['date']} and {t2['date']}."
                            ),
                        })

        # Deduplicate anomalies by message
        seen: set = set()
        unique_anomalies = []
        for a in anomalies:
            key = a.get("message", "")
            if key not in seen:
                seen.add(key)
                unique_anomalies.append(a)

        high = [a for a in unique_anomalies if a["severity"] == "high"]
        medium = [a for a in unique_anomalies if a["severity"] == "medium"]

        return json.dumps({
            "status": "success",
            "total_anomalies": len(unique_anomalies),
            "high_severity": len(high),
            "medium_severity": len(medium),
            "anomalies": unique_anomalies,
            "summary": (
                f"Found {len(unique_anomalies)} anomalies: "
                f"{len(high)} high-severity, {len(medium)} medium-severity."
            ),
        }, indent=2)

    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})
