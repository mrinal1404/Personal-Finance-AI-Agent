"""
Pydantic v2 schemas for the FastAPI layer.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Request Models ────────────────────────────────────────────────────────────

class AnalyseRequest(BaseModel):
    query: str = Field(
        default="Analyse my finances for the past 3 months and give me a full savings report.",
        description="Natural language instruction for the agent.",
    )
    session_id: str = Field(
        default="default",
        description="Unique session / thread ID for conversation continuity.",
    )
    budget_limits: Optional[Dict[str, float]] = Field(
        default=None,
        description="Per-category monthly budget limits in INR.",
        example={"Food & Dining": 8000, "Shopping": 5000, "Entertainment": 2000},
    )
    monthly_income: Optional[float] = Field(
        default=85000.0,
        description="User's monthly take-home income in INR.",
    )


class FeedbackRequest(BaseModel):
    session_id: str = Field(description="Session ID from a previous analyse call.")
    feedback: str = Field(
        description="User's corrective feedback on the agent's recommendations.",
        example="My rent is fixed and cannot be reduced. Focus on other categories.",
    )
    original_query: Optional[str] = Field(
        default=None,
        description="Original query — used to re-run the agent with full context.",
    )


class TransactionsRequest(BaseModel):
    months: int = Field(default=3, ge=1, le=12, description="Number of months to fetch.")
    category_filter: Optional[str] = Field(default=None, description="Filter by category name.")


# ── Response Models ───────────────────────────────────────────────────────────

class ToolCallLog(BaseModel):
    iteration: int
    tool_name: str
    tool_args: Dict[str, Any]
    timestamp: str


class AnalyseResponse(BaseModel):
    status: str
    session_id: str
    final_message: str
    tool_call_logs: List[ToolCallLog] = []
    iteration_count: int = 0
    error: Optional[str] = None


class TransactionSummary(BaseModel):
    total_transactions: int
    total_spend_inr: float
    total_income_inr: float
    net_savings_inr: float
    date_range: Dict[str, str]


class TransactionsResponse(BaseModel):
    status: str
    transactions: List[Dict[str, Any]]
    income: List[Dict[str, Any]]
    summary: TransactionSummary


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_provider: str
    llm_model: str
