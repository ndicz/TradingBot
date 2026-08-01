"""Technical indicators computed on an OHLCV DataFrame."""

from __future__ import annotations

import pandas as pd


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period).mean()


def compute_indicators(df: pd.DataFrame, swing_lookback: int = 20) -> dict:
    """Compute a standard indicator set on the most recent candle of df.

    Requires at least ~50 candles for EMA50 to be meaningful; degrades
    gracefully (indicators still computed, just less reliable) on shorter
    history.
    """
    close = df["close"]

    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    rsi14 = _rsi(close, 14)

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - macd_signal

    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20

    atr14 = _atr(df, 14)

    window = df.tail(swing_lookback)
    support = float(window["low"].min())
    resistance = float(window["high"].max())

    price = float(close.iloc[-1])
    prev_price = float(close.iloc[-2]) if len(close) > 1 else price
    change_pct = ((price - prev_price) / prev_price * 100) if prev_price else 0.0

    def last(series: pd.Series) -> float:
        val = series.iloc[-1]
        return float(val) if pd.notna(val) else None

    return {
        "price": price,
        "change_pct": change_pct,
        "ema9": last(ema9),
        "ema21": last(ema21),
        "ema50": last(ema50),
        "rsi14": last(rsi14),
        "macd_line": last(macd_line),
        "macd_signal": last(macd_signal),
        "macd_hist": last(macd_hist),
        "bb_upper": last(bb_upper),
        "bb_lower": last(bb_lower),
        "atr14": last(atr14),
        "support": support,
        "resistance": resistance,
        "candles": len(df),
        "last_candle_time": df["open_time"].iloc[-1].isoformat(),
    }
