"""Configuration: instrument lists and data source endpoints."""

# Stablecoins to exclude when picking "top 10 crypto" by market cap
CRYPTO_STABLECOINS = {
    "USDT", "USDC", "DAI", "FDUSD", "TUSD", "USDE", "USDS", "PYUSD", "BUSD", "USDP",
}

# NOTE: IDX revises the official LQ45 constituent list twice a year (Feb & Aug).
# This is a static snapshot — update periodically from idx.co.id.
LQ45_TICKERS = [
    "ACES.JK", "ADRO.JK", "AKRA.JK", "AMMN.JK", "AMRT.JK", "ANTM.JK", "ARTO.JK", "ASII.JK",
    "BBCA.JK", "BBNI.JK", "BBRI.JK", "BBTN.JK", "BMRI.JK", "BRIS.JK", "BRPT.JK", "BUKA.JK",
    "CPIN.JK", "CTRA.JK", "ESSA.JK", "EXCL.JK", "GGRM.JK", "GOTO.JK", "HRUM.JK", "ICBP.JK",
    "INCO.JK", "INDF.JK", "INKP.JK", "ISAT.JK", "ITMG.JK", "JPFA.JK", "JSMR.JK", "KLBF.JK",
    "MAPI.JK", "MDKA.JK", "MEDC.JK", "PGAS.JK", "PTBA.JK", "SIDO.JK", "SMGR.JK", "SMRA.JK",
    "SRTG.JK", "TLKM.JK", "TOWR.JK", "UNTR.JK", "UNVR.JK",
]

NASDAQ_SYMBOL = "^IXIC"  # NASDAQ Composite index

# Gold vs USD — try spot symbol first, fall back to COMEX futures if unavailable.
XAU_SYMBOL_CANDIDATES = ["XAUUSD=X", "GC=F"]

# api.binance.com is geo/network-blocked on some networks; data-api.binance.vision
# is Binance's public market-data mirror (same REST shape, no auth) and works as a fallback.
BINANCE_KLINES_URLS = [
    "https://api.binance.com/api/v3/klines",
    "https://data-api.binance.vision/api/v3/klines",
]
COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YAHOO_RSS_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline"

BINANCE_INTERVAL = "30m"
YAHOO_INTERVAL = "30m"
YAHOO_RANGE = "5d"
KLINES_LIMIT = 150

CACHE_TTL_SECONDS = 300
REQUEST_TIMEOUT_SECONDS = 10
YF_MAX_WORKERS = 8

# News: per-instrument headlines via Yahoo Finance's per-symbol RSS feed
# (works for stocks, ^IXIC, GC=F, and CRYPTO-USD tickers — no API key needed).
NEWS_CACHE_TTL_SECONDS = 3600
NEWS_PER_INSTRUMENT = 5
NEWS_MAX_WORKERS = 8
