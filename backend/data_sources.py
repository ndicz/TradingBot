"""Fetchers for crypto (Binance), stocks/index/gold (Yahoo Finance), and
the CoinGecko market-cap ranking used to pick the top 10 crypto."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.utils import parsedate_to_datetime
from typing import Optional
from xml.etree import ElementTree

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
    """Fetch OHLCV candles for a Binance spot symbol (e.g. BTCUSDT).

    Tries each URL in config.BINANCE_KLINES_URLS in order (primary API host,
    then the public data-mirror fallback) since api.binance.com is blocked on
    some networks.
    """
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    raw = None
    for url in config.BINANCE_KLINES_URLS:
        try:
            resp = _session.get(url, params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)
            resp.raise_for_status()
            raw = resp.json()
            break
        except Exception:
            log.warning("Binance klines fetch failed for %s via %s", symbol, url)
            continue

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


def crypto_to_yahoo_symbol(binance_symbol: str) -> str:
    """BTCUSDT -> BTC-USD (Yahoo Finance's crypto ticker format)."""
    base = binance_symbol[:-4] if binance_symbol.endswith("USDT") else binance_symbol
    return f"{base}-USD"


def fetch_yahoo_rss_news(symbol: str, limit: int = config.NEWS_PER_INSTRUMENT) -> Optional[list[dict]]:
    """Fetch the latest headlines for a symbol from Yahoo Finance's
    per-ticker RSS feed. Works for stocks (BBCA.JK), indices (^IXIC),
    futures/FX (GC=F), and crypto (BTC-USD)."""
    params = {"s": symbol, "region": "US", "lang": "en-US"}
    try:
        resp = _session.get(config.YAHOO_RSS_URL, params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        root = ElementTree.fromstring(resp.content)
    except Exception:
        log.warning("Yahoo RSS news fetch failed for %s", symbol)
        return None

    items = []
    for item in root.findall("./channel/item")[:limit]:
        title = item.findtext("title")
        link = item.findtext("link")
        pub_date_raw = item.findtext("pubDate")
        if not title or not link:
            continue
        published_at = None
        if pub_date_raw:
            try:
                published_at = parsedate_to_datetime(pub_date_raw).isoformat()
            except (TypeError, ValueError):
                published_at = pub_date_raw
        items.append({"title": title, "link": link, "published_at": published_at})

    return items if items else None


def fetch_many_news(symbols: list[str], max_workers: int = config.NEWS_MAX_WORKERS) -> dict[str, Optional[list[dict]]]:
    """Fetch Yahoo RSS news for many symbols concurrently."""
    results: dict[str, Optional[list[dict]]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fetch_yahoo_rss_news, sym): sym for sym in symbols}
        for fut in as_completed(futures):
            sym = futures[fut]
            try:
                results[sym] = fut.result()
            except Exception:
                log.exception("Unexpected error fetching news for %s", sym)
                results[sym] = None
    return results
