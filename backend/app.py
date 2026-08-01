"""FastAPI app serving the M30 analysis dashboard.

Endpoints:
  GET /api/analysis            -> all groups
  GET /api/analysis?group=crypto|lq45|nasdaq|xau
  GET /                        -> dashboard (static frontend)
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config, data_sources
from .analysis import analyze_instrument

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="TradingBot M30 Analysis")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_cache_lock = threading.Lock()
_cache = {
    "status": "loading",
    "updated_at": None,
    "groups": {"crypto": [], "lq45": [], "nasdaq": [], "xau": []},
}


def _refresh_crypto() -> list[dict]:
    items = []
    try:
        top10 = data_sources.get_top10_crypto()
    except Exception:
        log.exception("Failed to fetch top10 crypto list")
        return items

    for coin in top10:
        df = data_sources.fetch_binance_klines(coin["binance_symbol"])
        result = analyze_instrument(coin["name"], coin["binance_symbol"], df, "crypto")
        if result:
            items.append(result)
    return items


def _refresh_lq45() -> list[dict]:
    items = []
    fetched = data_sources.fetch_many_yahoo(config.LQ45_TICKERS)
    for ticker in config.LQ45_TICKERS:
        df = fetched.get(ticker)
        result = analyze_instrument(ticker.replace(".JK", ""), ticker, df, "lq45")
        if result:
            items.append(result)
    return items


def _refresh_nasdaq() -> list[dict]:
    df = data_sources.fetch_yahoo_klines(config.NASDAQ_SYMBOL)
    result = analyze_instrument("NASDAQ Composite", config.NASDAQ_SYMBOL, df, "nasdaq")
    return [result] if result else []


def _refresh_xau() -> list[dict]:
    symbol, df = data_sources.fetch_xau_klines()
    result = analyze_instrument("Gold / USD", symbol or "XAUUSD", df, "xau")
    return [result] if result else []


def _refresh_all() -> None:
    log.info("Refreshing analysis cache...")
    groups = {
        "crypto": _refresh_crypto(),
        "lq45": _refresh_lq45(),
        "nasdaq": _refresh_nasdaq(),
        "xau": _refresh_xau(),
    }
    with _cache_lock:
        _cache["groups"] = groups
        _cache["status"] = "ok"
        _cache["updated_at"] = time.time()
    log.info("Cache refreshed.")


def _refresh_loop() -> None:
    while True:
        try:
            _refresh_all()
        except Exception:
            log.exception("Cache refresh failed")
        time.sleep(config.CACHE_TTL_SECONDS)


@app.on_event("startup")
def _on_startup() -> None:
    thread = threading.Thread(target=_refresh_loop, daemon=True)
    thread.start()


@app.get("/api/analysis")
def get_analysis(group: str = Query(default="all", pattern="^(all|crypto|lq45|nasdaq|xau)$")):
    with _cache_lock:
        status = _cache["status"]
        updated_at = _cache["updated_at"]
        groups = _cache["groups"]
        if group == "all":
            data = groups
        else:
            data = {group: groups.get(group, [])}
    return {"status": status, "updated_at": updated_at, "timeframe": "M30", "data": data}


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
