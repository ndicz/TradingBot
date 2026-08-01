"""Fetchers for crypto (Binance), stocks/index/gold (Yahoo Finance), and
the CoinGecko market-cap ranking used to pick the top 10 crypto."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import pandas as pd
import requests

from . import config

log = logging.getLogger(__name__)

_session = requests.Session()
_session.headers.update({"User-Agent": "Mozilla/5.0 (TradingBot analysis dashboard)"})


def get_top10_crypto() -> list[dict]:
    """Return the top 10 non-stablecoin coins by market cap, with their
    Binance USDT trading pair, e.g. [{"symbol": "BTC", "binance_symbol": "BTCUSDT", ...}]."""
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 25,
        "page": 1,
        "sparkline": "false",
    }
    resp = _session.get(config.COINGECKO_MARKETS_URL, params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()

    result = []
    for coin in data:
        symbol = coin["symbol"].upper()
        if symbol in config.CRYPTO_STABLECOINS:
            continue
        result.append({
            "id": coin["id"],
            "name": coin["name"],
            "symbol": symbol,
            "binance_symbol": f"{symbol}USDT",
            "market_cap": coin.get("market_cap"),
        })
        if len(result) == 10:
            break
    return result


def fetch_binance_klines(symbol: str, interval: str = config.BINANCE_INTERVAL,
                          limit: int = config.KLINES_LIMIT) -> Optional[pd.DataFrame]:
    """Fetch OHLCV candles for a Binance spot symbol (e.g. BTCUSDT)."""
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        resp = _session.get(config.BINANCE_KLINES_URL, params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        raw = resp.json()
    except Exception:
        log.exception("Binance klines fetch failed for %s", symbol)
        return None

    if not raw:
        return None

    df = pd.DataFrame(raw, columns=[
        "open_time", "open", "high", "low", "close", "volume", "close_time",
        "quote_volume", "trades", "taker_base", "taker_quote", "ignore",
    ])
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    return df[["open_time", "open", "high", "low", "close", "volume"]]


def fetch_yahoo_klines(symbol: str, interval: str = config.YAHOO_INTERVAL,
                        range_: str = config.YAHOO_RANGE) -> Optional[pd.DataFrame]:
    """Fetch OHLCV candles from Yahoo Finance's chart endpoint for a stock,
    index (^IXIC) or FX/futures symbol (XAUUSD=X, GC=F)."""
    url = config.YAHOO_CHART_URL.format(symbol=symbol)
    params = {"interval": interval, "range": range_}
    try:
        resp = _session.get(url, params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        log.warning("Yahoo klines fetch failed for %s", symbol)
        return None

    result = payload.get("chart", {}).get("result")
    if not result:
        return None

    result = result[0]
    timestamps = result.get("timestamp")
    quote = result.get("indicators", {}).get("quote", [{}])[0]
    if not timestamps or not quote.get("close"):
        return None

    df = pd.DataFrame({
        "open_time": pd.to_datetime(timestamps, unit="s"),
        "open": quote.get("open"),
        "high": quote.get("high"),
        "low": quote.get("low"),
        "close": quote.get("close"),
        "volume": quote.get("volume"),
    })
    df = df.dropna(subset=["close"]).reset_index(drop=True)
    return df if not df.empty else None


def fetch_xau_klines() -> tuple[Optional[str], Optional[pd.DataFrame]]:
    """Try each XAU symbol candidate until one returns data."""
    for sym in config.XAU_SYMBOL_CANDIDATES:
        df = fetch_yahoo_klines(sym)
        if df is not None:
            return sym, df
    return None, None


def fetch_many_yahoo(symbols: list[str], max_workers: int = config.YF_MAX_WORKERS) -> dict[str, Optional[pd.DataFrame]]:
    """Fetch Yahoo Finance klines for many symbols concurrently."""
    results: dict[str, Optional[pd.DataFrame]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fetch_yahoo_klines, sym): sym for sym in symbols}
        for fut in as_completed(futures):
            sym = futures[fut]
            try:
                results[sym] = fut.result()
            except Exception:
                log.exception("Unexpected error fetching %s", sym)
                results[sym] = None
    return results
