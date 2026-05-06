"""
FastAPI route definitions for the Personal Finance Agent API.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse

from agent.graph import run_agent, stream_agent
from models.schemas import (
    AnalyseRequest,
    AnalyseResponse,
    FeedbackRequest,
    TransactionsRequest,
    TransactionsResponse,
    HealthResponse,
)
from tools.transaction_fetcher import fetch_transactions

logger = logging.getLogger(__name__)
router = APIRouter()

# Simple in-memory session store (replace with Redis in production)
_session_store: Dict[str, Any] = {}


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Return API health status and LLM configuration."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "anthropic":
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    else:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    return HealthResponse(
        status="ok",
        version="1.0.0",
        llm_provider=provider,
        llm_model=model,
    )


@router.post("/analyse", response_model=AnalyseResponse, tags=["Agent"])
async def analyse_finances(request: AnalyseRequest):
    """
    Run the finance agent on the user's transaction data.

    The agent autonomously fetches transactions, analyses spending,
    detects anomalies, forecasts expenses, and produces savings advice.
    """
    logger.info("Analyse request | session=%s | query=%s", request.session_id, request.query[:60])

    result = run_agent(
        query=request.query,
        session_id=request.session_id,
        budget_limits=request.budget_limits,
    )

    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Agent error"))

    # Persist result for feedback endpoint
    _session_store[request.session_id] = {
        "last_query": request.query,
        "last_result": result,
    }

    return AnalyseResponse(
        status="success",
        session_id=request.session_id,
        final_message=result.get("final_message", ""),
        tool_call_logs=result.get("tool_call_logs", []),
        iteration_count=result.get("iteration_count", 0),
    )


@router.post("/feedback", response_model=AnalyseResponse, tags=["Agent"])
async def submit_feedback(request: FeedbackRequest):
    """
    Submit user feedback to trigger the self-correction loop.

    The agent re-runs with the original context plus the corrective
    feedback, revising its recommendations accordingly.
    """
    session = _session_store.get(request.session_id, {})
    original_query = request.original_query or session.get(
        "last_query",
        "Re-analyse my finances with the feedback provided.",
    )

    combined_query = (
        f"{original_query}\n\n"
        f"[User Feedback]: {request.feedback}"
    )

    logger.info(
        "Feedback request | session=%s | feedback=%s",
        request.session_id,
        request.feedback[:60],
    )

    result = run_agent(
        query=combined_query,
        session_id=request.session_id,
        user_feedback=request.feedback,
    )

    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Agent error"))

    _session_store[request.session_id] = {
        "last_query": combined_query,
        "last_result": result,
    }

    return AnalyseResponse(
        status="success",
        session_id=request.session_id,
        final_message=result.get("final_message", ""),
        tool_call_logs=result.get("tool_call_logs", []),
        iteration_count=result.get("iteration_count", 0),
    )


@router.get("/transactions", tags=["Data"])
async def get_transactions(months: int = 3, category_filter: str | None = None):
    """Fetch raw transaction data (with optional filters)."""
    raw = fetch_transactions.invoke({
        "months": months,
        "category_filter": category_filter,
    })
    data = json.loads(raw)
    if data.get("status") == "error":
        raise HTTPException(status_code=500, detail=data["message"])
    return data


@router.get("/stream", tags=["Agent"])
async def stream_analysis(
    query: str = "Analyse my finances and give me savings advice.",
    session_id: str = "default",
):
    """
    Stream agent events as Server-Sent Events (SSE).

    Connect to this endpoint to receive real-time agent reasoning traces,
    tool call events, and the final report as they are generated.
    """
    def event_generator():
        try:
            for event in stream_agent(query=query, session_id=session_id):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'event': 'error', 'data': str(exc)})}\n\n"
        finally:
            yield "data: {\"event\": \"done\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions/{session_id}", tags=["Agent"])
async def get_session(session_id: str):
    """Retrieve the last result for a given session."""
    session = _session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    result = session.get("last_result", {})
    return {
        "session_id": session_id,
        "last_query": session.get("last_query"),
        "final_message": result.get("final_message", ""),
        "tool_call_logs": result.get("tool_call_logs", []),
        "iteration_count": result.get("iteration_count", 0),
    }
