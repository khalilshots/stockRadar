# Stock Radar

A stock scanner built around small LLM agents. Each agent answers one narrow question about a ticker ("is the price and float in range?", "is there a real catalyst?"), returns a small JSON verdict, and a gate decides whether the ticker moves on to the next agent or gets dropped.

The goal is to go from a broad universe of tickers to a short, ranked list of setups worth watching, using the criteria of a strategy you define.

> **Status:** early. The first agent (price filter) works end to end. Most other agents, data tools and the scheduler are stubbed out, and the frontend is still the Vite starter.

## How it's meant to work

```
universe (≤500)  ──►  Team 1: screening  ──►  watchlist (≤50)  ──►  Team 2: setups + risk  ──►  final list (≤10)
                      price · volume ·                              momentum · breakout ·
                      catalyst                                      reversal · risk · scoring
```

- **Strategies** live in `strategies.json`. Each one sets price range, max float, min volume, min gap %, max prior-day gain, preferred setups and risk per trade.
- **Agents** get the stock data plus the strategy criteria and reply with `{ticker, passed, reason}`.
- **Gates** (`utils/gates.py`) run after every agent and drop a ticker on a fail, an error, or missing data.
- **LLM calls** go through LiteLLM, defaulting to a local Llama 3.2 on Ollama at temperature 0. Swapping to a hosted model is a one-line change.
- **Scans** are planned for three windows (Eastern): night (10 PM to midnight), premarket (9:00 to 9:20 AM) and post-market (4 to 6 PM).
- **Journal:** results and outcomes get logged to Notion.

## What's built

| Piece | State |
|---|---|
| Price filter agent | Working |
| yfinance data tool | Working |
| Gates | Working |
| Strategy manager | Working |
| Settings (`config/settings.py`) | Done, not wired in yet |
| FastAPI backend | Root and `/health` endpoints |
| Volume, catalyst, momentum, breakout, reversal, risk, scoring agents | Stubs |
| Finnhub, Alpha Vantage, FRED, NewsAPI, Reddit tools | Stubs |
| Rate limiter, cache, scheduler, Notion journal | Stubs |
| React frontend | Vite + Tailwind + shadcn scaffold |

## Project layout

```
backend/
  main.py              FastAPI app
  agents/
    team1/             screening agents (price, volume, catalyst)
    team2/             setup, risk and scoring agents
    orchestrator.py
  tools/               one module per data source
  strategies/          strategies.json + strategy_manager.py
  utils/               gates, cache, rate limiter
  config/settings.py   env-driven settings
  notion/              journal agent
  scheduler.py
frontend/              React (Vite, Tailwind, shadcn/ui)
```

The top-level copies of `agents/`, `tools/`, `utils/` and friends are left over from moving everything into `backend/`. `run.py` at the root is a quick manual test of the price filter.

## Setup

Needs Python 3.10+, Node 20+ and [Ollama](https://ollama.com).

```bash
git clone https://github.com/khalilshots/stockRadar.git
cd stockRadar

python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

ollama pull llama3.2:3b

cp .env.example .env   # add your API keys
```

Keys go in `.env`: Alpha Vantage, Finnhub, FRED, NewsAPI and a Reddit app (client ID, secret, user agent). All have free tiers.

## Running it

**Price filter test**

```bash
cp backend/strategies/strategies.json strategies/
python run.py
```

Runs AAPL and HOOD through the "Small Cap Momentum" strategy and prints whether each one passes the price and float check.

**API**

```bash
cd backend
uvicorn main:app --reload
```

Serves on `http://localhost:8000`. CORS is open to the frontend on port 5173.

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

## Adding a strategy

```python
from strategies.strategy_manager import save_strategy

save_strategy({
    "id": "2",
    "name": "Low Float Gappers",
    "criteria": {
        "price_min": 1,
        "price_max": 10,
        "max_float": 5000000,
        "min_volume": 100000,
        "min_gap_percent": 20,
        "max_prior_day_gain": 30
    },
    "setup_preferences": ["breakout"],
    "risk_per_trade": 250
})
```

Saving with an existing name overwrites that strategy.

## Disclaimer

This is a personal research project, not financial advice.
