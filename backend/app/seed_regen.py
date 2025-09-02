import csv, random
from datetime import datetime, timedelta
from pathlib import Path

def gen(trades_path, confirms_path, n=1200, break_rate=0.06, seed_val=7):
    random.seed(seed_val)
    symbols = ["AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA","JPM","BAC","XOM","BRK.B","UNH"]
    accts = [f"FND{1000+i}" for i in range(80)]
    now = datetime.utcnow().replace(microsecond=0)
    settle = (now + timedelta(days=2)).date().isoformat()
    trades, confs = [], []
    for i in range(n):
        tid = f"T{now.strftime('%Y%m%d')}-{i:06d}"
        sym = random.choice(symbols)
        side = random.choice(["BUY","SELL"])
        qty  = random.choice([100,200,300,500,1000,1500,2000])
        price = round(random.uniform(10,500)*(1+random.uniform(-0.02,0.02)),2)
        acct = random.choice(accts)
        ttime = now - timedelta(minutes=random.randint(0,120), seconds=random.randint(0,59))  # <= 2h
        broker = random.choice(["GSCO","MSCO","JPMC","BAML","CDEL","NITE","UBSW"])
        cust = random.choice(["SELF_CLEAR","INTRODUCING"])
        trades.append({
            "trade_id": tid, "symbol": sym, "side": side, "qty": qty, "price": price,
            "notional": round(qty*price,2), "account": acct, "exec_time": ttime.isoformat(),
            "settle_date": settle, "exec_broker": broker, "customer_type": cust
        })
        is_break = random.random() < break_rate
        c_qty, c_price, c_settle, c_acct = qty, price, settle, acct
        kind = None
        if is_break:
            kind = random.choice(["QTY","PRICE","SETTLE","ACCOUNT","LATE"])  # no “MISSING” for cleaner demo
            if kind == "QTY": c_qty = qty + random.choice([-100,-50,50,100])
            elif kind == "PRICE": c_price = round(price*(1+random.choice([-1,1])*random.uniform(0.006,0.03)),2)
            elif kind == "SETTLE": c_settle = (datetime.fromisoformat(settle+"T00:00:00")+timedelta(days=random.choice([-1,1]))).date().isoformat()
            elif kind == "ACCOUNT":
                c_acct = random.choice(accts)
                while c_acct == acct: c_acct = random.choice(accts)
        ctime = ttime + timedelta(minutes=random.randint(1,120))
        if kind == "LATE": ctime = ttime + timedelta(hours=5, minutes=random.randint(1,59))
        confs.append({
            "trade_id": tid, "symbol": sym, "side": side, "qty": c_qty, "price": c_price,
            "notional": round(c_qty*c_price,2), "account": c_acct, "confirm_time": ctime.isoformat(),
            "settle_date": c_settle, "exec_broker": broker
        })

    with open(trades_path,"w",newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(trades[0].keys())); w.writeheader(); w.writerows(trades)
    with open(confirms_path,"w",newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(confs[0].keys())); w.writeheader(); w.writerows(confs)

if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    gen(root/"seed_data/dtcc_sample_trades.csv", root/"seed_data/dtcc_sample_confirms.csv")
    print("Seed regenerated.")