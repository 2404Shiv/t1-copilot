import asyncio, random, string
from datetime import datetime, timedelta

SYMBOLS = ["AAPL","MSFT","GOOGL","AMZN","META","TSLA","NVDA","JPM","V","MA"]
VENUES = ["Goldman","Morgan Stanley","JP Morgan","Citadel","Virtu"]
ACCOUNTS = ["ACC001","ACC002","ACC003","ACC004","ACC005"]

def rand_id():
    return "TRD-" + "".join(random.choices(string.ascii_uppercase+string.digits, k=6))

async def generate_trades(queue):
    from .models import Trade, Confirm
    while True:
        await asyncio.sleep(random.uniform(1, 3))
        tid = rand_id()
        sym = random.choice(SYMBOLS)
        price = round(random.uniform(50, 800), 2)
        qty = random.randint(100, 5000)
        acc = random.choice(ACCOUNTS)
        venue = random.choice(VENUES)
        settle = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
        now = datetime.utcnow().isoformat() + "Z"

        trade = Trade(
            trade_id=tid, account=acc, symbol=sym,
            qty=qty, price=price, venue=venue,
            settle_date=settle, trade_time=now,
            notional=round(price*qty, 2)
        )
        await queue.put(trade)

        await asyncio.sleep(random.uniform(0.2, 1.0))

        roll = random.random()
        confirm = Confirm(
            trade_id=tid,
            account=acc if roll > 0.1 else random.choice(ACCOUNTS),
            symbol=sym,
            qty=qty if roll > 0.15 else qty + random.randint(1, 50),
            price=price if roll > 0.12 else round(price*random.uniform(0.98,1.02),2),
            venue=venue,
            settle_date=settle if roll > 0.08 else (datetime.utcnow()+timedelta(days=2)).strftime("%Y-%m-%d"),
            confirm_time=datetime.utcnow().isoformat() + "Z"
        )
        if roll > 0.05:
            await queue.put(confirm)
