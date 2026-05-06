"""
LangGraph ReAct agent graph with self-correction loop.

Flow:
  START → agent ──(has tool calls)──► tools → agent
                └──(no tool calls)──► END
"""
from __future__ import annotations

import os
import json
import logging
from datetime import datetime
from typing import Literal

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

from agent.state import AgentState
from agent.prompts import SYSTEM_PROMPT, FEEDBACK_PROMPT
from tools import get_all_tools

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10  # Safety cap on agent loops


def _get_llm():
    """Initialise the chat model from environment variables."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0.3,
        )
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.3,
        )


def build_agent_graph(checkpointer: MemorySaver | None = None):
    """
    Construct and compile the LangGraph ReAct agent graph.

    Args:
        checkpointer: Optional LangGraph checkpointer for state persistence.

    Returns:
        A compiled LangGraph app ready for invocation.
    """
    llm = _get_llm()
    tools = get_all_tools()
    llm_with_tools = llm.bind_tools(tools)

    # ── Node: Agent (LLM reasoning) ──────────────────────────────────────────
    def agent_node(state: AgentState) -> dict:
        messages = list(state["messages"])
        iteration = state.get("iteration_count", 0)
        tool_logs = list(state.get("tool_call_logs", []))

        # Prepend system message on first call
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

        # Inject feedback as a new human message if present and not yet processed
        feedback = state.get("user_feedback")
        if feedback:
            feedback_msg = HumanMessage(
                content=FEEDBACK_PROMPT.format(feedback=feedback)
            )
            # Only inject if not already the last message
            if not messages or messages[-1].content != feedback_msg.content:
                messages.append(feedback_msg)

        # Safety guard
        if iteration >= MAX_ITERATIONS:
            logger.warning("Max iterations reached (%d), forcing stop.", MAX_ITERATIONS)
            return {
                "messages": [AIMessage(content="Maximum analysis iterations reached. Here is my current report.")],
                "iteration_count": iteration + 1,
            }

        logger.info("Agent iteration %d: calling LLM with %d messages.", iteration, len(messages))
        response: AIMessage = llm_with_tools.invoke(messages)

        # Log any tool calls the agent chose to make
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                tool_logs.append({
                    "iteration": iteration,
                    "tool_name": tc["name"],
                    "tool_args": tc["args"],
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })
                logger.info("  → tool call: %s(%s)", tc["name"], tc["args"])

        return {
            "messages": [response],
            "iteration_count": iteration + 1,
            "tool_call_logs": tool_logs,
            # Clear processed feedback so it isn't re-injected
            "user_feedback": None,
        }

    # ── Node: Tools (tool execution) ─────────────────────────────────────────
    tool_node = ToolNode(tools)

    # ── Graph assembly ────────────────────────────────────────────────────────
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        tools_condition,           # routes to "tools" if AIMessage has tool_calls, else END
        {"tools": "tools", END: END},
    )
    graph.add_edge("tools", "agent")

    compile_kwargs: dict = {}
    if checkpointer:
        compile_kwargs["checkpointer"] = checkpointer

    return graph.compile(**compile_kwargs)


# ── Convenience helpers ───────────────────────────────────────────────────────

def run_agent(
    query: str,
    session_id: str = "default",
    budget_limits: dict | None = None,
    user_feedback: str | None = None,
    checkpointer: MemorySaver | None = None,
) -> dict:
    """
    Run the finance agent for a given query.

    Args:
        query: The user's question or instruction.
        session_id: Unique thread ID for conversation persistence.
        budget_limits: Optional per-category budget limits (INR).
        user_feedback: Optional corrective feedback from a previous run.
        checkpointer: Optional MemorySaver for state persistence.

    Returns:
        Dict with final_message, tool_call_logs, iteration_count, and full state.
    """
    app = build_agent_graph(checkpointer=checkpointer)

    initial_state: AgentState = {
        "messages": [HumanMessage(content=query)],
        "transactions": None,
        "analysis_results": None,
        "anomalies": None,
        "forecast": None,
        "recommendations": None,
        "budget_limits": budget_limits or {},
        "user_feedback": user_feedback,
        "iteration_count": 0,
        "tool_call_logs": [],
        "final_report": None,
        "session_id": session_id,
    }

    config = {"configurable": {"thread_id": session_id}} if checkpointer else {}

    try:
        final_state = app.invoke(initial_state, config=config)
        last_ai_msg = next(
            (m for m in reversed(final_state["messages"]) if isinstance(m, AIMessage)),
            None,
        )
        return {
            "status": "success",
            "session_id": session_id,
            "final_message": last_ai_msg.content if last_ai_msg else "",
            "tool_call_logs": final_state.get("tool_call_logs", []),
            "iteration_count": final_state.get("iteration_count", 0),
            "state": final_state,
        }
    except Exception as exc:
        logger.error("Agent run failed: %s", exc, exc_info=True)
        return {"status": "error", "message": str(exc)}


def stream_agent(
    query: str,
    session_id: str = "default",
    user_feedback: str | None = None,
    checkpointer: MemorySaver | None = None,
):
    """
    Stream agent events (for real-time Streamlit updates).

    Yields:
        Dicts with 'event', 'node', and 'data' keys.
    """
    app = build_agent_graph(checkpointer=checkpointer)

    initial_state: AgentState = {
        "messages": [HumanMessage(content=query)],
        "transactions": None,
        "analysis_results": None,
        "anomalies": None,
        "forecast": None,
        "recommendations": None,
        "budget_limits": {},
        "user_feedback": user_feedback,
        "iteration_count": 0,
        "tool_call_logs": [],
        "final_report": None,
        "session_id": session_id,
    }

    config = {"configurable": {"thread_id": session_id}} if checkpointer else {}

    for chunk in app.stream(initial_state, config=config, stream_mode="updates"):
        for node_name, node_output in chunk.items():
            messages = node_output.get("messages", [])
            for msg in messages:
                yield {
                    "event": "message",
                    "node": node_name,
                    "data": {
                        "type": type(msg).__name__,
                        "content": msg.content if hasattr(msg, "content") else "",
                        "tool_calls": getattr(msg, "tool_calls", []),
                    },
                }
            if "tool_call_logs" in node_output:
                yield {
                    "event": "tool_logs",
                    "node": node_name,
                    "data": node_output["tool_call_logs"],
                }
