# backend/app/ingestion_binance.py
import asyncio, json, math, random
import websockets
from datetime import datetime, timezone

def _now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def _mk_trade(symbol, p, q):
    notional = float(p) * float(q)
    tid = f"BIN-{int(datetime.now().timestamp()*1000)}-{random.randint(1000,9999)}"
    return {
        "trade_id": tid,
        "symbol": symbol.upper(),           # e.g., BTCUSDT
        "side": "BUY",                      # unknown -> pick a side for demo
        "qty": int(max(1, round(float(q)))),# engine wants ints; ok for demo
        "price": float(p),
        "notional": round(notional, 2),
        "account": "FNDDEMO",
        "exec_time": _now_iso(),
        "settle_date": datetime.utcnow().date().isoformat(),
        "exec_broker": "BINANCE",
        "customer_type": "SELF_CLEAR",
    }

def _mk_confirm(trade):
    # 98% perfect, 2% small breaks to exercise rules
    c = dict(trade)
    c["confirm_time"] = _now_iso()
    if random.random() < 0.02:
        btype = random.choice(["QTY","PRICE","SETTLE","ACCOUNT","LATE"])
        if btype == "QTY":
            c["qty"] = trade["qty"] + random.choice([-1,1])
        elif btype == "PRICE":
            c["price"] = round(trade["price"] * (1 + random.choice([-1,1]) * 0.015), 2)
            c["notional"] = round(c["qty"] * c["price"], 2)
        elif btype == "SETTLE":
            from datetime import timedelta
            c["settle_date"] = (datetime.utcnow().date()).isoformat()
        elif btype == "ACCOUNT":
            c["account"] = "FNDALT"
        elif btype == "LATE":
            # signal late by delaying a bit; rule uses time delta
            pass
    return {
        k: c[k] for k in
        ["trade_id","symbol","side","qty","price","notional","account","confirm_time","settle_date","exec_broker"]
    }

async def stream(queue, symbols=("btcusdt","ethusdt")):
    url = "wss://stream.binance.com:9443/stream?streams=" + "/".join(f"{s}@aggTrade" for s in symbols)
    async for ws in websockets.connect(url, ping_interval=20, ping_timeout=20):
        try:
            async for raw in ws:
                msg = json.loads(raw)
                data = msg.get("data", {})
                if data.get("e") == "aggTrade":
                    sym = msg["stream"].split("@")[0].upper()
                    price = data["p"]       # string
                    qty   = data["q"]       # string
                    trade = _mk_trade(sym, price, qty)
                    await queue.put(("trade", trade))
                    # emit confirm shortly after
                    await asyncio.sleep(0.05)
                    await queue.put(("confirm", _mk_confirm(trade)))
        except Exception:
            await asyncio.sleep(1)  # reconnect backoff, keep running
            continue