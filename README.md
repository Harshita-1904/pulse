# Pulse

Pulse is a smart market watchlist that highlights what changed since a user last checked.

## Phase 1

This initial foundation includes a FastAPI backend, a frontend placeholder, environment-variable template, and a health endpoint.

## Project layout

```text
pulse/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── database/
│   │   ├── jobs/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   └── requirements.txt
├── frontend/
│   └── README.md
└── .env.example
```

## Run the backend

From the `backend` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/health`. The expected response is:

```json
{"status":"ok"}
```

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Phase 2: database and authentication

Copy `.env.example` to `.env` and set a real `JWT_SECRET_KEY`. Create a PostgreSQL database named `pulse`, then apply the initial local schema:

```powershell
Copy-Item ..\.env.example .env
python -m app.database.create_tables
```

For local-only setup, set `AUTO_CREATE_TABLES=true` in `.env` to create the schema when the API starts. Use the explicit command above once migrations are introduced.

The initial endpoints are:

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me` (Bearer token required)

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Phase 3: market data

Pulse uses an Alpha Vantage adapter by default. Add your provider key as `MARKET_DATA_API_KEY` in `.env`; quotes are cached for five minutes by default and every successful refresh is recorded in `market_data` and `price_history`.

Authenticated market endpoints:

- `GET /stocks`
- `POST /stocks`
- `GET /stocks/{symbol}/quote?refresh=false`
- `POST /stocks/{symbol}/refresh`

Refresh a batch manually with:

```powershell
python -m app.jobs.market_collector AAPL MSFT
```

Set `MARKET_DATA_MAX_AGE_SECONDS` to control quote-cache freshness. The provider is isolated in `app/services/market_data.py`, ready to swap when the final data vendor is selected.

## Phase 4: change intelligence

Phase 4 records each user's most recently seen price and volume for a stock, then calculates an explainable change score from price movement, historical unusualness, volume, and volatility when sufficient data exists. Cold-start scores use fixed thresholds and report low confidence. Before running the API after this upgrade, apply the schema addition:

```powershell
python -m app.database.migrate
```

Authenticated endpoints:

- `POST /changes/{symbol}/mark-seen` stores the current quote as the comparison baseline.
- `GET /changes/{symbol}` returns the direction, price/volume movement, score, severity, confidence, method, reasons, verdict, and freshness state.

The first `GET` returns `direction: first_view` because there is no checkpoint yet. The dashboard automatically stores the displayed quote as the next baseline after returning its snapshot, so the next visit shows the true comparison. `mark-seen` remains available for an explicit reset.

## Phase 5: watchlist state management

Watchlists are private to their owner and enforce a simple state flow: adding a stock creates a `tracked_unseen` state, marking it seen creates the Phase 4 baseline, and removing it from the user's final watchlist clears that state.

Authenticated endpoints:

- `GET /watchlists` and `POST /watchlists`
- `GET /watchlists/default`
- `GET /watchlists/{watchlist_id}`
- `POST /watchlists/{watchlist_id}/stocks`
- `DELETE /watchlists/{watchlist_id}/stocks/{symbol}`

Stocks must first exist in the market catalogue—use `POST /stocks` or refresh a symbol—before adding them to a watchlist.

## Phase 6: dashboard API

The dashboard API composes watchlist membership, stored quotes, and the Phase 4 comparison state into frontend-ready responses, then automatically advances available quote baselines after the response snapshot is calculated. A stock with no quote is returned as an unavailable item rather than failing the whole dashboard. Browser clients listed in `CORS_ORIGINS` can call the API during frontend development.

Authenticated endpoints:

- `GET /watchlists/{watchlist_id}/overview` returns all change summaries plus up/down/unseen counts.
- `POST /watchlists/{watchlist_id}/refresh` refreshes every stock independently and reports individual failures without discarding successful updates.

## Phase 7: frontend

The React frontend is now in `frontend/`. It authenticates against the existing FastAPI API and uses the default watchlist plus the Phase 6 overview endpoint for the dashboard. Run it with the instructions in `frontend/README.md`.

The stock-details screen also uses the authenticated `GET /stocks/{symbol}/history` endpoint. This small read-only addition exposes existing `price_history` data for the chart; it does not modify collection, authentication, or change-intelligence behavior.
