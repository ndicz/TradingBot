"""FastAPI app serving the M30 analysis dashboard.

Endpoints:
  GET /api/analysis            -> all groups
  GET /api/analysis?group=crypto|lq45|nasdaq|xau
  GET /api/news                -> per-instrument headlines, refreshed hourly
  GET /api/news?group=crypto|lq45|nasdaq|xau
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
from .sentiment import combine_signal, score_headlines

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

_news_lock = threading.Lock()
_news_cache = {
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


def _build_news_targets() -> list[tuple[str, str, str, str]]:
    """(group, code, name, yahoo_symbol) for every instrument currently in
    the price cache — keeps news in sync with the live top-10 crypto list
    and whichever XAU symbol resolved."""
    with _cache_lock:
        groups = _cache["groups"]

    targets: list[tuple[str, str, str, str]] = []
    for item in groups.get("crypto", []):
        if item.get("status") == "ok":
            targets.append(("crypto", item["code"], item["name"], data_sources.crypto_to_yahoo_symbol(item["code"])))
    for item in groups.get("lq45", []):
        if item.get("status") == "ok":
            targets.append(("lq45", item["code"], item["name"], item["code"]))
    for item in groups.get("nasdaq", []):
        if item.get("status") == "ok":
            targets.append(("nasdaq", item["code"], item["name"], item["code"]))
    for item in groups.get("xau", []):
        if item.get("status") == "ok":
            targets.append(("xau", item["code"], item["name"], item["code"]))
    return targets


def _refresh_news() -> None:
    log.info("Refreshing news cache...")
    targets = _build_news_targets()
    fetched = data_sources.fetch_many_news([t[3] for t in targets])

    grouped = {"crypto": [], "lq45": [], "nasdaq": [], "xau": []}
    for group, code, name, yahoo_symbol in targets:
        items = fetched.get(yahoo_symbol) or []
        grouped[group].append({
            "code": code,
            "name": name,
            "yahoo_symbol": yahoo_symbol,
            "items": items,
            "sentiment": score_headlines(items),
        })

    with _news_lock:
        _news_cache["groups"] = grouped
        _news_cache["status"] = "ok"
        _news_cache["updated_at"] = time.time()
    log.info("News cache refreshed.")


def _refresh_news_loop() -> None:
    # Wait for the first price refresh so we know the current instrument set
    # (crypto top10 and the resolved XAU symbol aren't known until then).
    while True:
        with _cache_lock:
            ready = _cache["status"] == "ok"
        if ready:
            break
        time.sleep(5)

    while True:
        try:
            _refresh_news()
        except Exception:
            log.exception("News cache refresh failed")
        time.sleep(config.NEWS_CACHE_TTL_SECONDS)


@app.on_event("startup")
def _on_startup() -> None:
    threading.Thread(target=_refresh_loop, daemon=True).start()
    threading.Thread(target=_refresh_news_loop, daemon=True).start()


def _news_sentiment_lookup() -> dict[tuple[str, str], dict]:
    with _news_lock:
        groups = _news_cache["groups"]
    return {
        (group, entry["code"]): entry["sentiment"]
        for group, entries in groups.items()
        for entry in entries
    }


def _enrich_with_news(group_name: str, items: list[dict], lookup: dict[tuple[str, str], dict]) -> list[dict]:
    enriched = []
    for item in items:
        item = dict(item)
        sentiment = lookup.get((group_name, item.get("code")))
        if sentiment and item.get("status") == "ok":
            item["news_sentiment"] = sentiment["sentiment"]
            item["combined_signal"] = combine_signal(item["signal"], sentiment["sentiment"])
        else:
            item["news_sentiment"] = None
            item["combined_signal"] = item.get("signal")
        enriched.append(item)
    return enriched


@app.get("/api/analysis")
def get_analysis(group: str = Query(default="all", pattern="^(all|crypto|lq45|nasdaq|xau)$")):
    with _cache_lock:
        status = _cache["status"]
        updated_at = _cache["updated_at"]
        groups = _cache["groups"]
        selected = groups if group == "all" else {group: groups.get(group, [])}

    lookup = _news_sentiment_lookup()
    data = {g: _enrich_with_news(g, items, lookup) for g, items in selected.items()}
    return {"status": status, "updated_at": updated_at, "timeframe": "M30", "data": data}


@app.get("/api/news")
def get_news(group: str = Query(default="all", pattern="^(all|crypto|lq45|nasdaq|xau)$")):
    with _news_lock:
        status = _news_cache["status"]
        updated_at = _news_cache["updated_at"]
        groups = _news_cache["groups"]
        if group == "all":
            data = groups
        else:
            data = {group: groups.get(group, [])}
    return {"status": status, "updated_at": updated_at, "data": data}


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
