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

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

BINANCE_INTERVAL = "30m"
YAHOO_INTERVAL = "30m"
YAHOO_RANGE = "5d"
KLINES_LIMIT = 150

CACHE_TTL_SECONDS = 300
REQUEST_TIMEOUT_SECONDS = 10
YF_MAX_WORKERS = 8
