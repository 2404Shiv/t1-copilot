
# T+1 Copilot — Same‑Day‑Affirmation (SDA) Compliance Engine

Open‑source prototype that ingests trade/confirm messages and flags equity‑settlement breaks in real‑time ahead of the 2025 **T+1** rules. Built for clarity and speed.

## What it does

- Streams trades and confirmations (DTCC‑like CSV included).
- Detects common **breaks** in under ~250 ms per event on a laptop:
  - Missing confirmation (beyond 2h SLA)
  - Late confirmation
  - Quantity mismatch
  - Price mismatch (beyond 0.5% tolerance)
  - Settle date mismatch
  - Account mismatch
- Live UI (WebSocket) to monitor breaks.
- Estimates turnover drag impact (illustrative **5 bps**).

> Addressable market: ≈ 2,000 self‑clearing U.S. funds (public DTCC tallies).

## Quick start

**Backend (FastAPI)**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit: http://127.0.0.1:8000/

**Data** loads automatically from `app/seed_data/*.csv` and starts streaming into the reconciler. Open the UI to watch breaks appear in real time.

## Design

- **Ingestion:** CSV -> asyncio queue (swap with Kafka in prod).
- **Core:** In‑memory `Reconciler` joins trade/confirm by `trade_id` and evaluates rules.
- **Rules:** `app/rules.py` keeps tolerances centralized.
- **Streaming:** `BreakStream` sends JSON to browsers via WebSocket.
- **UI:** Minimal vanilla JS/HTML/CSS for zero‑friction demo.

## Evaluate performance

Call the health endpoint:

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok","processed":1234,"breaks":456,"avg_detect_ms":1.73}
```

The *avg_detect_ms* should be well below 250 ms on commodity hardware for this rule set.

## Extending

- Replace CSV ingestion with:
  - DTCC/Omgeo/CTM feed adapters
  - FIX dropcopy or MQ
- Add persistence (Postgres + SQLAlchemy) and replay.
- Add case management (assign, comment, resolve).
- Enrich rules: broker cutoffs, buy‑ins, NSCC netting windows, prime/IB mappings.
- Add alerting (Slack/Teams/Email) and escalation policies.

## Legal

MIT License. Educational example; **not** production compliance advice.
