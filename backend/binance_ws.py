"""Realtime Binance kline stream via WebSocket.

Replaces REST polling for crypto (and the PAXGUSDT gold proxy) with live
push updates on the currently-forming M30 candle. A new symbol is seeded
with historical candles via one REST call (data_sources.fetch_binance_klines)
so indicators have enough history immediately; the WebSocket then keeps
that window live without further polling.

Falls back gracefully: if the WebSocket host is unreachable (blocked on
some networks — stream.binance.com is a separate host from the
data-api.binance.vision REST mirror and isn't always allowed even when
that is), get_klines() just returns None and callers fall back to REST.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import OrderedDict
from typing import Optional

import pandas as pd
import websocket

from . import config, data_sources

log = logging.getLogger(__name__)

_WS_URL = "wss://stream.binance.com:9443/ws"
_INTERVAL = config.BINANCE_INTERVAL
_MAX_CANDLES = config.KLINES_LIMIT
_RECONNECT_DELAY_SECONDS = 5

_lock = threading.Lock()
_klines: dict[str, "OrderedDict[int, dict]"] = {}
_subscribed: set[str] = set()
_ws_app: Optional[websocket.WebSocketApp] = None
_next_id = 1
_started = False


def _stream_name(symbol: str) -> str:
    return f"{symbol.lower()}@kline_{_INTERVAL}"


def _send_subscribe(ws: websocket.WebSocketApp, symbols: list[str]) -> None:
    global _next_id
    params = [_stream_name(s) for s in symbols]
    ws.send(json.dumps({"method": "SUBSCRIBE", "params": params, "id": _next_id}))
    _next_id += 1


def _on_open(ws: websocket.WebSocketApp) -> None:
    log.info("Binance WS connected")
    with _lock:
        symbols = list(_subscribed)
    if symbols:
        _send_subscribe(ws, symbols)


def _on_message(_ws: websocket.WebSocketApp, message: str) -> None:
    try:
        msg = json.loads(message)
    except Exception:
        return
    if msg.get("e") != "kline":
        return

    k = msg["k"]
    symbol = msg["s"]
    open_time_ms = int(k["t"])
    candle = {
        "open_time": pd.to_datetime(open_time_ms, unit="ms"),
        "open": float(k["o"]),
        "high": float(k["h"]),
        "low": float(k["l"]),
        "close": float(k["c"]),
        "volume": float(k["v"]),
    }
    with _lock:
        series = _klines.setdefault(symbol, OrderedDict())
        series[open_time_ms] = candle  # upsert: same key keeps its position
        while len(series) > _MAX_CANDLES:
            series.popitem(last=False)


def _on_error(_ws: websocket.WebSocketApp, error) -> None:
    log.warning("Binance WS error: %s", error)


def _on_close(_ws, status_code, msg) -> None:
    log.warning("Binance WS closed (%s %s) — reconnecting in %ss", status_code, msg, _RECONNECT_DELAY_SECONDS)


def _run_forever() -> None:
    global _ws_app
    while True:
        _ws_app = websocket.WebSocketApp(
            _WS_URL,
            on_open=_on_open,
            on_message=_on_message,
            on_error=_on_error,
            on_close=_on_close,
        )
        try:
            _ws_app.run_forever(ping_interval=180, ping_timeout=10)
        except Exception:
            log.exception("Binance WS run_forever crashed")
        time.sleep(_RECONNECT_DELAY_SECONDS)


def start() -> None:
    """Idempotent: launches the background WS thread at most once."""
    global _started
    with _lock:
        if _started:
            return
        _started = True
    threading.Thread(target=_run_forever, daemon=True, name="binance-ws").start()


def _is_connected() -> bool:
    try:
        return bool(_ws_app and _ws_app.sock and _ws_app.sock.connected)
    except Exception:
        return False


def _seed_history(symbol: str) -> None:
    """One-time REST backfill so a freshly-subscribed symbol has enough
    history for indicators immediately, instead of waiting ~KLINES_LIMIT
    candle-closes for the WebSocket alone to build up a window."""
    df = data_sources.fetch_binance_klines(symbol)
    if df is None:
        return
    with _lock:
        series = _klines.setdefault(symbol, OrderedDict())
        for row in df.itertuples(index=False):
            open_time_ms = int(row.open_time.value // 1_000_000)
            series[open_time_ms] = {
                "open_time": row.open_time, "open": row.open, "high": row.high,
                "low": row.low, "close": row.close, "volume": row.volume,
            }
        while len(series) > _MAX_CANDLES:
            series.popitem(last=False)


def ensure_subscribed(symbols: list[str]) -> None:
    """Additive and idempotent — subscribes to any symbol not already
    tracked (seeding its history first) and leaves existing subscriptions
    alone. Safe to call every refresh cycle with the current symbol list."""
    start()
    new_symbols = []
    with _lock:
        for s in symbols:
            if s not in _subscribed:
                _subscribed.add(s)
                new_symbols.append(s)

    for s in new_symbols:
        _seed_history(s)

    if new_symbols and _is_connected():
        _send_subscribe(_ws_app, new_symbols)
    # If not connected yet, _on_open sends the full _subscribed set once it opens.


def get_klines(symbol: str, min_candles: int = 15) -> Optional[pd.DataFrame]:
    with _lock:
        series = _klines.get(symbol)
        if not series or len(series) < min_candles:
            return None
        rows = list(series.values())
    df = pd.DataFrame(rows)
    return df[["open_time", "open", "high", "low", "close", "volume"]]


def is_live(symbol: str) -> bool:
    """Whether this symbol currently has an active WS connection feeding it
    (vs. only ever having been REST-seeded, e.g. because the WS host is
    unreachable on this network)."""
    with _lock:
        tracked = symbol in _subscribed
    return tracked and _is_connected()
