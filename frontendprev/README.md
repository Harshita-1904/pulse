# Pulse frontend

Phase 7 is a Vite and React interface for the existing Pulse FastAPI API. It does not use mock data: authentication, the stock catalogue, watchlist membership, dashboard intelligence, baseline checkpoints, and chart history all come from the backend.

## Configure and run

1. Copy `.env.example` to `.env` and set `VITE_API_BASE_URL` if the API is not on `http://127.0.0.1:8000`.
2. Start the FastAPI backend from `../backend` with `python -m uvicorn app.main:app --reload`.
3. In this folder, run `npm install` once, then `npm run dev`.
4. Open the URL shown by Vite (normally `http://localhost:5173`).

The backend default CORS configuration already permits both `http://localhost:5173` and `http://127.0.0.1:5173`.

## Data prerequisites

The home screen lists stocks already collected into the Pulse catalogue. A stock needs a stored quote before it can contribute change intelligence; use the existing collector or stock refresh process to populate quotes. The chart shows locally recorded `price_history` observations and becomes a line chart when at least two observations exist.
