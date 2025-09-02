
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
