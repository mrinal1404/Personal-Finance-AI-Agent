"""
Personal Finance AI Agent — Streamlit Dashboard
Run with: streamlit run streamlit_app.py
"""
from __future__ import annotations

import json
import time
import uuid
from collections import defaultdict
from typing import Any, Dict, List

import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Finance AI Agent",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "http://localhost:8000/api/v1"

# ── Session State Defaults ────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "tool_logs" not in st.session_state:
    st.session_state.tool_logs = []
if "last_report" not in st.session_state:
    st.session_state.last_report = None
if "transactions" not in st.session_state:
    st.session_state.transactions = []
if "income_data" not in st.session_state:
    st.session_state.income_data = []


# ── Helper: API Calls ─────────────────────────────────────────────────────────
def api_get(endpoint: str, params: dict = None) -> dict | None:
    try:
        r = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=120)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to the FastAPI backend. Run: `uvicorn main:app --reload`")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_post(endpoint: str, payload: dict) -> dict | None:
    try:
        r = requests.post(f"{API_BASE}{endpoint}", json=payload, timeout=180)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to the FastAPI backend. Run: `uvicorn main:app --reload`")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def load_transactions() -> bool:
    data = api_get("/transactions", params={"months": 3})
    if data:
        st.session_state.transactions = data.get("transactions", [])
        st.session_state.income_data = data.get("income", [])
        return True
    return False


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/emoji/96/money-bag.png", width=60)
    st.title("Finance AI Agent")
    st.caption(f"Session: `{st.session_state.session_id}`")

    st.divider()
    st.subheader("⚙️ Configuration")

    monthly_income = st.number_input(
        "Monthly Income (₹)",
        value=85000,
        step=5000,
        min_value=10000,
        help="Your take-home salary per month.",
    )

    st.markdown("**Budget Limits (₹/month)**")
    budget_food = st.slider("Food & Dining", 3000, 20000, 8000, 500)
    budget_shopping = st.slider("Shopping", 1000, 15000, 5000, 500)
    budget_entertainment = st.slider("Entertainment", 500, 5000, 2000, 100)
    budget_transport = st.slider("Transportation", 500, 8000, 3000, 200)

    budget_limits = {
        "Food & Dining": float(budget_food),
        "Shopping": float(budget_shopping),
        "Entertainment": float(budget_entertainment),
        "Transportation": float(budget_transport),
        "Rent": 22000.0,
        "Utilities": 4000.0,
        "Healthcare": 3000.0,
        "Education": 3000.0,
        "Finance": 8000.0,
    }

    st.divider()
    if st.button("🔄 Reload Transactions", use_container_width=True):
        with st.spinner("Loading..."):
            load_transactions()
            st.success("Transactions loaded!")

    st.divider()
    st.caption("Built with LangGraph · LangChain · FastAPI · Streamlit")


# ── Title ─────────────────────────────────────────────────────────────────────
st.title("💰 Personal Finance AI Agent")
st.caption("Autonomous spending analysis · Budget insights · Personalised savings advice")

# Load transactions on first render
if not st.session_state.transactions:
    load_transactions()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_overview, tab_transactions, tab_agent, tab_reports, tab_logs = st.tabs([
    "📊 Overview",
    "💳 Transactions",
    "🤖 Agent Chat",
    "📈 Reports",
    "🔍 Tool Logs",
])


# ────────────────────────────────────────────────────────────────────────────
# TAB 1: Overview
# ────────────────────────────────────────────────────────────────────────────
with tab_overview:
    txns = st.session_state.transactions
    income_records = st.session_state.income_data

    if not txns:
        st.info("No transaction data loaded. Click **Reload Transactions** in the sidebar.")
    else:
        expenses = [t for t in txns if t["amount"] < 0]
        total_spend = sum(abs(t["amount"]) for t in expenses)
        total_income = sum(i["amount"] for i in income_records)
        net_savings = total_income - total_spend
        savings_rate = (net_savings / total_income * 100) if total_income else 0

        # KPI cards
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💸 Total Spend (3 mo)", f"₹{total_spend:,.0f}", delta=None)
        col2.metric("💵 Total Income (3 mo)", f"₹{total_income:,.0f}")
        col3.metric("🏦 Net Savings", f"₹{net_savings:,.0f}",
                    delta=f"{savings_rate:.1f}% savings rate",
                    delta_color="normal" if savings_rate >= 20 else "inverse")
        col4.metric("📋 Transactions", len(expenses))

        st.divider()

        # Spending by category — pie chart
        cat_totals: dict = defaultdict(float)
        for t in expenses:
            cat_totals[t.get("category", "Others")] += abs(t["amount"])

        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Spending by Category")
            fig_pie = px.pie(
                names=list(cat_totals.keys()),
                values=list(cat_totals.values()),
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig_pie.update_layout(margin=dict(t=20, b=20, l=0, r=0), height=350)
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_right:
            st.subheader("Monthly Spend Trend")
            monthly_totals: dict = defaultdict(float)
            for t in expenses:
                month = t["date"][:7]
                monthly_totals[month] += abs(t["amount"])

            months = sorted(monthly_totals.keys())
            fig_bar = go.Figure(go.Bar(
                x=[m for m in months],
                y=[monthly_totals[m] for m in months],
                marker_color=["#4ECDC4", "#45B7D1", "#FF6B6B"],
                text=[f"₹{monthly_totals[m]:,.0f}" for m in months],
                textposition="outside",
            ))
            fig_bar.update_layout(
                xaxis_title="Month",
                yaxis_title="Amount (₹)",
                margin=dict(t=20, b=20),
                height=350,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        # Budget vs Actual bar chart
        st.subheader("Budget vs Actual Spend (Monthly Average)")
        months_count = max(len(set(t["date"][:7] for t in expenses)), 1)
        avg_by_cat = {cat: round(v / months_count, 0) for cat, v in cat_totals.items()}

        cats = [c for c in avg_by_cat if c in budget_limits]
        fig_budget = go.Figure()
        fig_budget.add_trace(go.Bar(
            name="Actual (avg/month)",
            x=cats,
            y=[avg_by_cat[c] for c in cats],
            marker_color="#FF6B6B",
        ))
        fig_budget.add_trace(go.Bar(
            name="Budget Limit",
            x=cats,
            y=[budget_limits[c] for c in cats],
            marker_color="#82E0AA",
        ))
        fig_budget.update_layout(
            barmode="group",
            xaxis_title="Category",
            yaxis_title="Amount (₹)",
            margin=dict(t=20, b=20),
            height=350,
        )
        st.plotly_chart(fig_budget, use_container_width=True)

        # Top merchants
        st.subheader("🏪 Top 10 Merchants by Spend")
        merchant_totals: dict = defaultdict(float)
        for t in expenses:
            merchant_totals[t.get("merchant", "Unknown")] += abs(t["amount"])

        top_merchants = sorted(merchant_totals.items(), key=lambda x: -x[1])[:10]
        fig_merch = px.bar(
            x=[m[0] for m in top_merchants],
            y=[m[1] for m in top_merchants],
            color=[m[1] for m in top_merchants],
            color_continuous_scale="Viridis",
            labels={"x": "Merchant", "y": "Total Spend (₹)"},
        )
        fig_merch.update_layout(margin=dict(t=20, b=20), height=300, showlegend=False)
        st.plotly_chart(fig_merch, use_container_width=True)


# ────────────────────────────────────────────────────────────────────────────
# TAB 2: Transactions
# ────────────────────────────────────────────────────────────────────────────
with tab_transactions:
    txns = st.session_state.transactions

    if not txns:
        st.info("No transactions loaded.")
    else:
        st.subheader("Transaction History")

        # Filters
        col_f1, col_f2, col_f3 = st.columns(3)
        all_cats = sorted(set(t.get("category", "Others") for t in txns))
        selected_cat = col_f1.selectbox("Filter by Category", ["All"] + all_cats)
        search_term = col_f2.text_input("Search Description")
        sort_col = col_f3.selectbox("Sort by", ["Date (newest)", "Date (oldest)", "Amount (high)", "Amount (low)"])

        filtered = txns.copy()
        if selected_cat != "All":
            filtered = [t for t in filtered if t.get("category") == selected_cat]
        if search_term:
            filtered = [t for t in filtered if search_term.lower() in t["description"].lower()]

        if sort_col == "Date (newest)":
            filtered.sort(key=lambda x: x["date"], reverse=True)
        elif sort_col == "Date (oldest)":
            filtered.sort(key=lambda x: x["date"])
        elif sort_col == "Amount (high)":
            filtered.sort(key=lambda x: abs(x["amount"]), reverse=True)
        else:
            filtered.sort(key=lambda x: abs(x["amount"]))

        # Display
        rows = [
            {
                "Date": t["date"],
                "Description": t["description"],
                "Category": t.get("category", "Others"),
                "Merchant": t.get("merchant", "—"),
                "Amount (₹)": f"₹{abs(t['amount']):,.2f}",
            }
            for t in filtered
        ]
        st.dataframe(rows, use_container_width=True, height=500)
        st.caption(f"Showing {len(filtered)} of {len(txns)} transactions")


# ────────────────────────────────────────────────────────────────────────────
# TAB 3: Agent Chat
# ────────────────────────────────────────────────────────────────────────────
with tab_agent:
    st.subheader("🤖 Chat with your Finance Agent")
    st.caption(
        "The agent autonomously fetches data, analyses spending, detects anomalies, "
        "forecasts expenses, and generates savings advice — no manual prompting needed."
    )

    # Chat history display
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
                st.markdown(msg["content"])

    # Quick action buttons
    st.markdown("**Quick Actions:**")
    qcol1, qcol2, qcol3, qcol4 = st.columns(4)
    quick_query = None
    if qcol1.button("📊 Full Analysis", use_container_width=True):
        quick_query = "Analyse my finances for the past 3 months and give me a detailed savings report."
    if qcol2.button("🚨 Find Anomalies", use_container_width=True):
        quick_query = "Detect any unusual or suspicious transactions in my spending history."
    if qcol3.button("📈 Forecast", use_container_width=True):
        quick_query = "Forecast my expenses for next month and tell me if I'm on track to save 20%."
    if qcol4.button("💡 Savings Tips", use_container_width=True):
        quick_query = "Give me the top 5 actionable ways to save more money this month."

    # Text input
    user_input = st.chat_input("Ask the agent anything about your finances...")
    query_to_send = quick_query or user_input

    if query_to_send:
        # Show user message
        st.session_state.chat_history.append({"role": "user", "content": query_to_send})
        with st.chat_message("user", avatar="👤"):
            st.markdown(query_to_send)

        # Check if it's a feedback/correction message
        is_feedback = any(
            kw in query_to_send.lower()
            for kw in ["my rent", "can't reduce", "need the", "keep the", "don't change", "fixed"]
        )

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Agent is reasoning and calling tools… this may take 30-60 seconds"):
                if is_feedback and st.session_state.chat_history:
                    result = api_post("/feedback", {
                        "session_id": st.session_state.session_id,
                        "feedback": query_to_send,
                        "original_query": next(
                            (m["content"] for m in reversed(st.session_state.chat_history[:-1])
                             if m["role"] == "user"), None
                        ),
                    })
                else:
                    result = api_post("/analyse", {
                        "query": query_to_send,
                        "session_id": st.session_state.session_id,
                        "budget_limits": budget_limits,
                        "monthly_income": monthly_income,
                    })

            if result:
                response_text = result.get("final_message", "No response received.")
                st.markdown(response_text)
                st.session_state.chat_history.append({"role": "assistant", "content": response_text})
                st.session_state.tool_logs = result.get("tool_call_logs", [])
                st.session_state.last_report = response_text

                # Iteration counter
                iters = result.get("iteration_count", 0)
                st.caption(f"✅ Completed in {iters} agent iterations · {len(st.session_state.tool_logs)} tool calls")
            else:
                st.error("Agent did not return a response. Check the backend logs.")

    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.session_state.session_id = str(uuid.uuid4())[:8]
            st.rerun()


# ────────────────────────────────────────────────────────────────────────────
# TAB 4: Reports
# ────────────────────────────────────────────────────────────────────────────
with tab_reports:
    st.subheader("📈 Finance Reports")

    if st.session_state.last_report:
        st.markdown("### Latest Agent Report")
        st.markdown(st.session_state.last_report)
        st.divider()

        col_dl1, col_dl2 = st.columns(2)
        col_dl1.download_button(
            "⬇️ Download Report (MD)",
            data=st.session_state.last_report,
            file_name="finance_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
        col_dl2.download_button(
            "⬇️ Download Tool Logs (JSON)",
            data=json.dumps(st.session_state.tool_logs, indent=2),
            file_name="tool_call_logs.json",
            mime="application/json",
            use_container_width=True,
        )
    else:
        st.info(
            "No report generated yet. Go to **Agent Chat** and run a full analysis first, "
            "or click the button below."
        )
        if st.button("🚀 Run Full Analysis Now", type="primary", use_container_width=True):
            with st.spinner("Running agent…"):
                result = api_post("/analyse", {
                    "query": "Analyse my finances for the past 3 months and give me a full savings report.",
                    "session_id": st.session_state.session_id,
                    "budget_limits": budget_limits,
                    "monthly_income": monthly_income,
                })
            if result:
                st.session_state.last_report = result.get("final_message", "")
                st.session_state.tool_logs = result.get("tool_call_logs", [])
                st.rerun()


# ────────────────────────────────────────────────────────────────────────────
# TAB 5: Tool Logs
# ────────────────────────────────────────────────────────────────────────────
with tab_logs:
    st.subheader("🔍 Agent Reasoning Traces & Tool Call Logs")
    st.caption(
        "Every tool call made by the agent is logged here. "
        "This gives you full transparency into the agent's decision-making process."
    )

    logs = st.session_state.tool_logs
    if not logs:
        st.info("No tool calls logged yet. Run a finance analysis from the **Agent Chat** tab.")
    else:
        # Summary metrics
        unique_tools = set(log.get("tool_name") for log in logs)
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Total Tool Calls", len(logs))
        col_m2.metric("Unique Tools Used", len(unique_tools))
        col_m3.metric("Tools Available", 5)

        # Tool call frequency chart
        tool_counts: dict = defaultdict(int)
        for log in logs:
            tool_counts[log.get("tool_name", "unknown")] += 1

        fig_tools = px.bar(
            x=list(tool_counts.keys()),
            y=list(tool_counts.values()),
            color=list(tool_counts.keys()),
            title="Tool Call Frequency",
            labels={"x": "Tool", "y": "Calls"},
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        fig_tools.update_layout(showlegend=False, height=280, margin=dict(t=40, b=20))
        st.plotly_chart(fig_tools, use_container_width=True)

        # Detailed log
        st.subheader("Detailed Log")
        for i, log in enumerate(logs, 1):
            tool_name = log.get("tool_name", "unknown")
            icon_map = {
                "fetch_transactions": "📥",
                "analyze_budget": "📊",
                "detect_anomalies": "🚨",
                "forecast_expenses": "📈",
                "generate_savings_advice": "💡",
            }
            icon = icon_map.get(tool_name, "🔧")

            with st.expander(
                f"{icon} Call #{i} — `{tool_name}` @ {log.get('timestamp', 'N/A')} "
                f"(Iteration {log.get('iteration', '?')})"
            ):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Tool Name**")
                    st.code(tool_name, language="text")
                with col_b:
                    st.markdown("**Iteration**")
                    st.code(str(log.get("iteration", "?")), language="text")
                st.markdown("**Input Arguments**")
                args = log.get("tool_args", {})
                st.json(args)
