import asyncio, random, string
from datetime import datetime, timedelta
import time

SYMBOLS = ["AAPL","MSFT","GOOGL","AMZN","META","TSLA","NVDA","JPM","V","MA",
           "UNH","JNJ","PG","HD","BAC","XOM","GS","BLK","SPGI","CAT"]
BROKERS = ["Goldman Sachs","Morgan Stanley","JP Morgan","Citadel","Two Sigma",
           "Virtu","Jane Street","Optiver","IMC","Susquehanna"]
ACCOUNTS = ["ACC001","ACC002","ACC003","ACC004","ACC005"]

def random_trade_id():
    return "TRD-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

async def generate_trades(recon_queue, throttle_ms=2):
    """Continuously generate realistic fake trades every few seconds"""
    while True:
        await asyncio.sleep(random.uniform(2, 6))
        trade_id = random_trade_id()
        sym = random.choice(SYMBOLS)
        price = round(random.uniform(50, 800), 2)
        qty = random.randint(100, 10000)
        account = random.choice(ACCOUNTS)
        venue = random.choice(BROKERS)
        settle_date = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
        exec_time = datetime.utcnow().isoformat() + "Z"

        trade = {
            "trade_id": trade_id,
            "account": account,
            "symbol": sym,
            "qty": qty,
            "price": price,
            "venue": venue,
            "settle_date": settle_date,
            "trade_time": exec_time,
            "notional": round(price * qty, 2)
        }

        # Sometimes generate a matching confirm (80% of time)
        # Sometimes introduce breaks (20% of time)
        await recon_queue.put(("trade", trade))
        await asyncio.sleep(random.uniform(0.5, 3))

        roll = random.random()
        confirm = {
            "trade_id": trade_id,
            "account": account if roll > 0.1 else random.choice(ACCOUNTS),  # 10% account mismatch
            "symbol": sym,
            "qty": qty if roll > 0.15 else qty + random.randint(1, 100),    # 15% qty mismatch
            "price": price if roll > 0.12 else round(price * random.uniform(0.98, 1.02), 2),  # 12% price mismatch
            "venue": venue,
            "settle_date": settle_date if roll > 0.08 else (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d"),
            "confirm_time": datetime.utcnow().isoformat() + "Z"
        }

        # 5% of trades never get confirmed (missing confirm break)
        if roll > 0.05:
            await recon_queue.put(("confirm", confirm))
