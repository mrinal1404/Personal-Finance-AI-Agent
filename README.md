# 💰 Personal Finance AI Agent

An **autonomous LLM-powered finance agent** built with LangGraph, LangChain, FastAPI, and Streamlit. It fetches transaction data, categorises spending patterns, detects anomalies, forecasts future expenses, and proactively generates personalised savings advice — all without manual prompting.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Streamlit Dashboard                         │
│  📊 Overview │ 💳 Transactions │ 🤖 Agent Chat │ 📈 Reports    │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP (REST)
┌───────────────────────────▼─────────────────────────────────────┐
│                      FastAPI Backend                            │
│  POST /api/v1/analyse  │  POST /api/v1/feedback                 │
│  GET  /api/v1/transactions  │  GET /api/v1/stream (SSE)         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│               LangGraph ReAct Agent Graph                       │
│                                                                  │
│   START → [agent node] ──(tool calls)──► [tools node] → agent  │
│                       └──(done)────────► END                    │
│                                                                  │
│   Self-Correction: user feedback → re-invoke → revised report   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                        Tool Suite                               │
│  📥 fetch_transactions  │  📊 analyze_budget                   │
│  🚨 detect_anomalies    │  📈 forecast_expenses                 │
│  💡 generate_savings_advice                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

| Feature | Description |
|---|---|
| **Autonomous Agent Loop** | ReAct-style LangGraph graph — the agent decides which tools to call, in what order, and when to stop |
| **Budget Analysis** | Category-wise spend breakdown vs. recommended budget percentages |
| **Anomaly Detection** | Statistical outlier detection (z-score), month-over-month spikes, duplicate charge detection |
| **Expense Forecasting** | Linear trend regression on monthly category data to predict next month's spend |
| **Savings Advisor** | Data-driven, quantified savings recommendations with a 30-day action plan |
| **Self-Correction Loop** | User can provide feedback; the agent revises recommendations accordingly |
| **Streaming (SSE)** | Real-time agent event streaming via `GET /api/v1/stream` |
| **Full Transparency** | Tool call logs, agent reasoning traces, and iteration counts visible in the dashboard |

---

## 🚀 Quick Start

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/personal-finance-agent.git
cd personal-finance-agent

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your API key:
#   OPENAI_API_KEY=sk-...         (for OpenAI)
#   ANTHROPIC_API_KEY=sk-ant-...  (for Anthropic — set LLM_PROVIDER=anthropic)
```

### 3. Start the FastAPI backend

```bash
uvicorn main:app --reload --port 8000
```

Swagger docs available at → http://localhost:8000/docs

### 4. Start the Streamlit dashboard (new terminal)

```bash
streamlit run streamlit_app.py
```

Dashboard available at → http://localhost:8501

---

## 📁 Project Structure

```
personal-finance-agent/
├── main.py                    # FastAPI app entry point
├── streamlit_app.py           # Streamlit dashboard (5 tabs)
├── requirements.txt
├── .env.example
│
├── agent/
│   ├── graph.py               # LangGraph ReAct workflow + stream_agent
│   ├── state.py               # AgentState TypedDict
│   └── prompts.py             # System + feedback prompts
│
├── tools/
│   ├── transaction_fetcher.py # @tool: load transaction history
│   ├── budget_analysis.py     # @tool: category-wise spend analysis
│   ├── anomaly_detection.py   # @tool: z-score + spike + duplicate detection
│   ├── expense_forecasting.py # @tool: linear regression forecasting
│   └── savings_advisor.py     # @tool: personalised savings recommendations
│
├── api/
│   └── routes.py              # FastAPI route handlers
│
├── models/
│   └── schemas.py             # Pydantic v2 request/response models
│
├── data/
│   ├── sample_transactions.json   # 90 days of realistic Indian transactions
│   └── categories.json            # Category config (keywords, colours, budgets)
│
└── utils/
    └── helpers.py             # Shared utility functions
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Health check + LLM config |
| `POST` | `/api/v1/analyse` | Run the full agent pipeline |
| `POST` | `/api/v1/feedback` | Submit feedback → self-correction |
| `GET` | `/api/v1/transactions` | Fetch raw transaction data |
| `GET` | `/api/v1/stream` | Stream agent events (SSE) |
| `GET` | `/api/v1/sessions/{id}` | Get last result for a session |

### Example: Run analysis

```bash
curl -X POST http://localhost:8000/api/v1/analyse \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyse my finances and give me savings advice",
    "session_id": "user_123",
    "monthly_income": 85000
  }'
```

### Example: Submit feedback (self-correction)

```bash
curl -X POST http://localhost:8000/api/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user_123",
    "feedback": "My rent is fixed and cannot be reduced. Focus on other categories."
  }'
```

---

## 🧠 How the Agent Works

1. **User sends a query** (e.g., "Analyse my finances")
2. **Agent reasons** (LLM with tools bound via `bind_tools`)
3. **Agent calls `fetch_transactions`** → gets 3 months of transaction data
4. **Agent calls `analyze_budget`** → gets category-wise spend vs. budget limits
5. **Agent calls `detect_anomalies`** → identifies unusual transactions
6. **Agent calls `forecast_expenses`** → predicts next month's spend
7. **Agent calls `generate_savings_advice`** → produces ranked recommendations
8. **Agent generates final report** → formatted markdown with action plan
9. **[Optional] User provides feedback** → agent re-runs, revises recommendations

The LangGraph `tools_condition` edge handles routing: if the LLM's response contains tool calls, execution continues to the tools node and back; once the LLM produces a plain text response, the graph exits.

---

## 🔧 LLM Configuration

The agent supports both **OpenAI** and **Anthropic** models:

```bash
# Use OpenAI (default)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini    # cheapest, fast — recommended for dev
# OPENAI_MODEL=gpt-4o       # best quality

# Use Anthropic
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

---

## 💡 Extending the Agent

### Add a new tool

```python
# tools/my_new_tool.py
from langchain_core.tools import tool

@tool
def my_new_tool(input_param: str) -> str:
    """Description of what this tool does. The LLM uses this to decide when to call it."""
    # ... implementation
    return json.dumps({"result": "..."})
```

Then register it in `tools/__init__.py`:

```python
from tools.my_new_tool import my_new_tool

def get_all_tools():
    return [..., my_new_tool]
```

### Connect to a real bank/API

Replace the `fetch_transactions` tool's file-reading logic with calls to:
- [Plaid](https://plaid.com/docs/) (US)
- [Fi Money API](https://fi.money/) (India)
- [Setu](https://setu.co/) (India — Account Aggregator)
- Any CSV export from your bank

---

## 🧪 Running Tests

```bash
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

---

## 📊 Sample Data

The `data/sample_transactions.json` file contains **89 realistic Indian transactions** across **Feb–Apr 2025** covering:

- 🍔 Food delivery (Swiggy, Zomato, Zepto, BigBasket)
- 🚗 Transport (Uber, Ola, Rapido, Metro)
- 🛍️ Shopping (Amazon, Flipkart, Myntra, Lenskart)
- 🎬 Entertainment (Netflix, Spotify, PVR, INOX)
- 💡 Utilities (BESCOM, ACT Fibernet, Airtel)
- 🏋️ Healthcare (Cult.fit, Apollo Pharmacy)
- 📚 Education (Udemy, Coursera, Crossword)
- 🏠 Rent (HSR Layout flat)
- 💰 Insurance (LIC premiums)

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| LLM | OpenAI GPT-4o-mini / Anthropic Claude 3.5 Sonnet |
| Agent Framework | LangGraph 0.2 + LangChain 0.3 |
| Backend API | FastAPI + Uvicorn |
| Frontend | Streamlit + Plotly |
| Data Validation | Pydantic v2 |
| State Persistence | LangGraph MemorySaver (in-memory) |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
