"""
Agent state definition for the Personal Finance LangGraph agent.
"""
from typing import TypedDict, Annotated, List, Optional, Dict, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """State maintained throughout the agent's execution graph."""

    # Core message history (LangGraph managed, append-only)
    messages: Annotated[List[BaseMessage], add_messages]

    # Loaded transaction data
    transactions: Optional[List[Dict[str, Any]]]

    # Results from analysis tools
    analysis_results: Optional[Dict[str, Any]]

    # Detected spending anomalies
    anomalies: Optional[List[Dict[str, Any]]]

    # Expense forecast data
    forecast: Optional[Dict[str, Any]]

    # Generated savings recommendations
    recommendations: Optional[List[str]]

    # User's budget limits per category (INR)
    budget_limits: Optional[Dict[str, float]]

    # User feedback for self-correction loop
    user_feedback: Optional[str]

    # Tracks re-runs to prevent infinite loops
    iteration_count: int

    # Detailed log of all tool calls made by the agent
    tool_call_logs: List[Dict[str, Any]]

    # Final summarised finance report
    final_report: Optional[str]

    # Session / thread identifier for persistence
    session_id: Optional[str]
