
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

Side = Literal["BUY","SELL"]

class Trade(BaseModel):
    trade_id: str
    symbol: str
    side: Side
    qty: int
    price: float
    notional: float
    account: str
    exec_time: datetime
    settle_date: str
    exec_broker: str
    customer_type: str

class Confirm(BaseModel):
    trade_id: str
    symbol: str
    side: Side
    qty: int
    price: float
    notional: float
    account: str
    confirm_time: datetime
    settle_date: str
    exec_broker: str

class Break(BaseModel):
    break_id: str
    trade_id: str
    break_type: str
    severity: str
    detail: str
    detected_ms: float
    created_at: datetime
    notional_usd: float
    est_turnover_drag_bp: float = Field(0.5)
