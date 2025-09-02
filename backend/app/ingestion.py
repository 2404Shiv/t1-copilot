
import csv
from pathlib import Path
from dateutil import parser
import asyncio

def to_trade_dict(row: dict) -> dict:
    row = row.copy()
    row["qty"] = int(row["qty"])
    row["price"] = float(row["price"])
    row["notional"] = float(row["notional"])
    row["exec_time"] = parser.isoparse(row["exec_time"]).isoformat()
    return row

def to_confirm_dict(row: dict) -> dict:
    row = row.copy()
    row["qty"] = int(row["qty"])
    row["price"] = float(row["price"])
    row["notional"] = float(row["notional"])
    row["confirm_time"] = parser.isoparse(row["confirm_time"]).isoformat()
    return row

async def load_csvs(queue, trades_csv: Path, confirms_csv: Path, throttle_ms: int = 3):
    with open(trades_csv, newline='') as f:
        trades = list(csv.DictReader(f))
    with open(confirms_csv, newline='') as f:
        confirms = list(csv.DictReader(f))

    events = []
    confirm_by_id = {c["trade_id"]: c for c in confirms}
    for t in trades[:1000]:
        events.append(("trade", to_trade_dict(t)))
        c = confirm_by_id.get(t["trade_id"])
        if c:
            events.append(("confirm", to_confirm_dict(c)))

    for topic, payload in events:
        await queue.put((topic, payload))
        await asyncio.sleep(throttle_ms/1000.0)
