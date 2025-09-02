
import asyncio
from typing import Dict, List
from .models import Trade, Confirm, Break
from . import rules
from .notifier import BreakStream
import time

class Reconciler:
    # Simple in-memory reconciler. In production, use Kafka + durable DB.
    def __init__(self, streamer: BreakStream):
        self.trades: Dict[str, Trade] = {}
        self.confirms: Dict[str, Confirm] = {}
        self.breaks: Dict[str, Break] = {}
        self.queue: "asyncio.Queue[tuple[str, dict]]" = asyncio.Queue()
        self.stream = streamer
        self.stats = {"processed":0, "detected_breaks":0, "avg_detect_ms":0.0}

    async def start(self):
        while True:
            topic, payload = await self.queue.get()
            t0 = time.perf_counter()
            if topic == "trade":
                trade = Trade(**payload)
                self.trades[trade.trade_id] = trade
                confirm = self.confirms.get(trade.trade_id)
                brks = rules.evaluate(trade, confirm)
            elif topic == "confirm":
                confirm = Confirm(**payload)
                self.confirms[confirm.trade_id] = confirm
                trade = self.trades.get(confirm.trade_id)
                brks = rules.evaluate(trade, confirm) if trade else []
            else:
                brks = []

            for b in brks:
                self.breaks[b.break_id] = b
                await self.stream.broadcast({"type":"break", "payload": b.model_dump()})

            dt_ms = (time.perf_counter() - t0) * 1000.0
            self.stats["processed"] += 1
            if brks:
                self.stats["detected_breaks"] += len(brks)
            k = max(self.stats["processed"], 1)
            self.stats["avg_detect_ms"] = ((self.stats["avg_detect_ms"]*(k-1)) + dt_ms) / k

    def get_breaks(self, limit: int = 200) -> List[Break]:
        return sorted(self.breaks.values(), key=lambda b: b.created_at, reverse=True)[:limit]
