
from typing import List
from .models import Trade, Confirm, Break
from datetime import datetime
import time

PRICE_TOL = 0.005  # 0.5%
SLA_CONFIRM_MIN = 180  # 2 hours

def evaluate(trade: Trade, confirm: Confirm | None) -> List[Break]:
    # Return list of Breaks for this trade/confirm pair.
    start = time.perf_counter()
    brks: List[Break] = []
    now = datetime.utcnow()
    notional = float(trade.notional)

    if confirm is None:
        # Missing or late? If beyond SLA window, flag MissingConfirm
        age_min = (now - trade.exec_time).total_seconds() / 60.0
        if age_min >= SLA_CONFIRM_MIN:
            brks.append(Break(
                break_id=f"BRK-{trade.trade_id}-MISSING",
                trade_id=trade.trade_id,
                break_type="MissingConfirm",
                severity="High",
                detail=f"No confirmation received within {SLA_CONFIRM_MIN} minutes SLA.",
                detected_ms=(time.perf_counter() - start) * 1000.0,
                created_at=now,
                notional_usd=notional
            ))
        return brks

    # Quantity mismatch
    if trade.qty != confirm.qty:
        brks.append(Break(
            break_id=f"BRK-{trade.trade_id}-QTY",
            trade_id=trade.trade_id,
            break_type="QuantityMismatch",
            severity="High",
            detail=f"Trade qty {trade.qty} vs confirm qty {confirm.qty}.",
            detected_ms=(time.perf_counter() - start) * 1000.0,
            created_at=now,
            notional_usd=notional
        ))

    # Price mismatch (beyond tolerance)
    price_dev = abs(trade.price - confirm.price) / max(trade.price, 1e-9)
    if price_dev > PRICE_TOL:
        brks.append(Break(
            break_id=f"BRK-{trade.trade_id}-PRICE",
            trade_id=trade.trade_id,
            break_type="PriceMismatch",
            severity="Medium" if price_dev < 0.02 else "High",
            detail=f"Trade {trade.price} vs confirm {confirm.price} ({price_dev:.2%} off).",
            detected_ms=(time.perf_counter() - start) * 1000.0,
            created_at=now,
            notional_usd=notional
        ))

    # Settle date mismatch
    if trade.settle_date != confirm.settle_date:
        brks.append(Break(
            break_id=f"BRK-{trade.trade_id}-SETTLE",
            trade_id=trade.trade_id,
            break_type="SettleDateMismatch",
            severity="Medium",
            detail=f"Trade settle {trade.settle_date} vs confirm {confirm.settle_date}.",
            detected_ms=(time.perf_counter() - start) * 1000.0,
            created_at=now,
            notional_usd=notional
        ))

    # Account mismatch
    if trade.account != confirm.account:
        brks.append(Break(
            break_id=f"BRK-{trade.trade_id}-ACCOUNT",
            trade_id=trade.trade_id,
            break_type="AccountMismatch",
            severity="High",
            detail=f"Trade acct {trade.account} vs confirm acct {confirm.account}.",
            detected_ms=(time.perf_counter() - start) * 1000.0,
            created_at=now,
            notional_usd=notional
        ))

    # Late confirmation (if confirm after SLA)
    age_min = (confirm.confirm_time - trade.exec_time).total_seconds() / 60.0
    if age_min > SLA_CONFIRM_MIN:
        brks.append(Break(
            break_id=f"BRK-{trade.trade_id}-LATE",
            trade_id=trade.trade_id,
            break_type="LateConfirm",
            severity="Low" if age_min < SLA_CONFIRM_MIN * 1.5 else "Medium",
            detail=f"Confirmation took {age_min:.1f} minutes (SLA {SLA_CONFIRM_MIN}).",
            detected_ms=(time.perf_counter() - start) * 1000.0,
            created_at=now,
            notional_usd=notional
        ))

    for b in brks:
        if b.detected_ms > 250.0:
            b.severity = "High"

    return brks
