"""Combine indicators into a simple BUY / SELL / HOLD signal with a
confidence score. This is a rule-based heuristic, not investment advice."""

from __future__ import annotations


def generate_signal(ind: dict) -> dict:
    price = ind["price"]
    ema9, ema21, ema50 = ind["ema9"], ind["ema21"], ind["ema50"]
    rsi = ind["rsi14"]
    macd_line, macd_signal = ind["macd_line"], ind["macd_signal"]
    bb_upper, bb_lower = ind["bb_upper"], ind["bb_lower"]

    score = 0
    reasons = []

    if None not in (ema9, ema21, ema50):
        if ema9 > ema21 > ema50:
            score += 2
            trend = "bullish"
            reasons.append("EMA9 > EMA21 > EMA50 (uptrend)")
        elif ema9 < ema21 < ema50:
            score -= 2
            trend = "bearish"
            reasons.append("EMA9 < EMA21 < EMA50 (downtrend)")
        else:
            trend = "sideways"
            reasons.append("EMA lines mixed (no clear trend)")
    else:
        trend = "unknown"

    if rsi is not None:
        if rsi < 30:
            score += 1
            reasons.append(f"RSI {rsi:.0f} (oversold)")
        elif rsi > 70:
            score -= 1
            reasons.append(f"RSI {rsi:.0f} (overbought)")

    if None not in (macd_line, macd_signal):
        if macd_line > macd_signal:
            score += 1
            reasons.append("MACD above signal line")
        else:
            score -= 1
            reasons.append("MACD below signal line")

    if None not in (bb_upper, bb_lower):
        if price <= bb_lower:
            score += 1
            reasons.append("Price at/below lower Bollinger Band")
        elif price >= bb_upper:
            score -= 1
            reasons.append("Price at/above upper Bollinger Band")

    if score >= 3:
        signal = "BUY"
    elif score >= 1:
        signal = "WEAK BUY"
    elif score <= -3:
        signal = "SELL"
    elif score <= -1:
        signal = "WEAK SELL"
    else:
        signal = "HOLD"

    confidence = min(100, round(abs(score) / 5 * 100))

    return {
        "signal": signal,
        "score": score,
        "confidence": confidence,
        "trend": trend,
        "reasons": reasons,
    }


def analyze_instrument(name: str, code: str, df, group: str, data_source: str = "rest") -> dict | None:
    from .indicators import compute_indicators

    if df is None or len(df) < 15:
        return {
            "name": name,
            "code": code,
            "group": group,
            "status": "unavailable",
        }

    ind = compute_indicators(df)
    sig = generate_signal(ind)

    return {
        "name": name,
        "code": code,
        "group": group,
        "status": "ok",
        "price": ind["price"],
        "change_pct": round(ind["change_pct"], 2),
        "rsi14": round(ind["rsi14"], 1) if ind["rsi14"] is not None else None,
        "trend": sig["trend"],
        "macd_hist": round(ind["macd_hist"], 6) if ind["macd_hist"] is not None else None,
        "support": ind["support"],
        "resistance": ind["resistance"],
        "signal": sig["signal"],
        "confidence": sig["confidence"],
        "reasons": sig["reasons"],
        "last_candle_time": ind["last_candle_time"],
        "data_source": data_source,
    }
