
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import asyncio
from pathlib import Path
from .reconciler import Reconciler
from .notifier import BreakStream
from . import ingestion
from fastapi.encoders import jsonable_encoder
from . import ingestion_binance

app = FastAPI(title="T+1 Copilot — Same‑Day Affirmation Compliance")

from pydantic import BaseModel
import sqlite3, datetime as dt, json, os
from fastapi.responses import JSONResponse

DB_PATH   = os.getenv("T1C_DB_PATH", "t1copilot.db")
SLA_MIN   = int(os.getenv("T1C_SLA_MINUTES", "180"))

def db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

# schema bootstrap
with db() as _c:
    _c.execute("""CREATE TABLE IF NOT EXISTS trades(
        id INTEGER PRIMARY KEY,
        trade_id TEXT, account TEXT, symbol TEXT,
        qty REAL, price REAL, venue TEXT,
        trade_time TEXT, raw TEXT)""")
    _c.execute("CREATE INDEX IF NOT EXISTS idx_trades_tid ON trades(trade_id)")
    _c.execute("""CREATE TABLE IF NOT EXISTS confirmations(
        id INTEGER PRIMARY KEY,
        trade_id TEXT, account TEXT, symbol TEXT,
        qty REAL, price REAL, venue TEXT,
        confirm_time TEXT, raw TEXT)""")
    _c.execute("CREATE INDEX IF NOT EXISTS idx_conf_tid ON confirmations(trade_id)")

class TradeIn(BaseModel):
    trade_id: str
    account: str | None = None
    symbol:  str | None = None
    qty:     float | None = None
    price:   float | None = None
    venue:   str | None = None
    trade_time: str | None = None   # ISO8601 Z

class ConfirmIn(BaseModel):
    trade_id: str
    account: str | None = None
    symbol:  str | None = None
    qty:     float | None = None
    price:   float | None = None
    venue:   str | None = None
    confirm_time: str | None = None # ISO8601 Z

def iso_now():
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def _find_match(conn, trade):
    # exact by trade_id
    row = conn.execute(
        "SELECT confirm_time FROM confirmations WHERE trade_id=? LIMIT 1",
        (trade["trade_id"],)
    ).fetchone()
    if row: return row[0]
    # tolerant composite match
    rows = conn.execute("""SELECT qty, confirm_time FROM confirmations
                           WHERE (account IS NULL OR account=?)
                             AND (symbol  IS NULL OR symbol =?)""",
                        (trade.get("account"), trade.get("symbol"))).fetchall()
    if rows and trade.get("qty") is not None:
        for q, cts in rows:
            if q is None: continue
            if abs(q - float(trade["qty"])) <= max(1e-9, 0.0001*abs(float(trade["qty"]))):
                return cts
    return None

@app.post("/ingest/trade")
def ingest_trade(t: TradeIn):
    ts = t.trade_time or iso_now()
    with db() as conn:
        conn.execute("""INSERT INTO trades(trade_id,account,symbol,qty,price,venue,trade_time,raw)
                        VALUES (?,?,?,?,?,?,?,?)""",
                     (t.trade_id, t.account, t.symbol, t.qty, t.price, t.venue, ts, json.dumps(t.dict())))
    return {"ok": True, "trade_id": t.trade_id, "trade_time": ts}

@app.post("/ingest/confirm")
def ingest_confirm(c: ConfirmIn):
    ts = c.confirm_time or iso_now()
    with db() as conn:
        conn.execute("""INSERT INTO confirmations(trade_id,account,symbol,qty,price,venue,confirm_time,raw)
                        VALUES (?,?,?,?,?,?,?,?)""",
                     (c.trade_id, c.account, c.symbol, c.qty, c.price, c.venue, ts, json.dumps(c.dict())))
    return {"ok": True, "trade_id": c.trade_id, "confirm_time": ts}

@app.get("/missing")
def missing(limit: int = 100):
    now = dt.datetime.utcnow()
    cutoff = (now - dt.timedelta(minutes=SLA_MIN)).replace(microsecond=0).isoformat() + "Z"
    out = []
    with db() as conn:
        rows = conn.execute("""SELECT trade_id,account,symbol,qty,price,venue,trade_time
                               FROM trades WHERE trade_time <= ?
                               ORDER BY trade_time DESC LIMIT ?""", (cutoff, limit)).fetchall()
        for tid, acc, sym, qty, price, venue, ttime in rows:
            if _find_match(conn, {"trade_id": tid, "account": acc, "symbol": sym, "qty": qty}) is None:
                out.append({"trade_id": tid, "account": acc, "symbol": sym, "qty": qty,
                            "detail": f"No confirmation within {SLA_MIN} minutes SLA.", "trade_time": ttime})
    return out

root = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(root / "static")), name="static")
templates = Jinja2Templates(directory=str(root / "templates"))

stream = BreakStream()
recon = Reconciler(streamer=stream)

@app.on_event("startup")
async def _startup():
    asyncio.create_task(recon.start())
    # keep CSV demo too (optional)
    trades = root / "seed_data" / "dtcc_sample_trades.csv"
    confs  = root / "seed_data" / "dtcc_sample_confirms.csv"
    asyncio.create_task(ingestion.load_csvs(recon.queue, trades, confs, throttle_ms=2))
    # start live crypto stream
    asyncio.create_task(ingestion_binance.stream(recon.queue, symbols=("btcusdt","ethusdt")))

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health():
    return {"status":"ok", "processed": recon.stats["processed"], "breaks": recon.stats["detected_breaks"], "avg_detect_ms": recon.stats["avg_detect_ms"]}

@app.get("/breaks")
async def get_breaks(limit: int = 200):
    brks = [b.model_dump() for b in recon.get_breaks(limit=limit)]
    return jsonable_encoder(brks)

@app.websocket("/ws")
async def ws(ws: WebSocket):
    await stream.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        stream.disconnect(ws)
