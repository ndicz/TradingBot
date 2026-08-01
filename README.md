# TradingBot — Analisa M30

Dashboard web yang menampilkan analisa teknikal timeframe M30 (30 menit) untuk:

- **Top 10 Crypto** (by market cap, non-stablecoin) — data dari Binance, ranking dari CoinGecko
- **LQ45 Saham** (45 saham IDX) — data dari Yahoo Finance
- **NASDAQ Composite** (`^IXIC`) — data dari Yahoo Finance
- **XAUUSD** (emas vs USD, fallback ke futures `GC=F`) — data dari Yahoo Finance

Untuk tiap instrumen dihitung EMA9/21/50, RSI14, MACD, Bollinger Bands, ATR14,
serta support/resistance dari 20 candle terakhir, lalu digabung jadi sinyal
sederhana **BUY / WEAK BUY / HOLD / WEAK SELL / SELL** dengan confidence score.

> Sinyal ini heuristik rule-based, bukan nasihat keuangan.

## Menjalankan

Butuh akses internet ke `api.binance.com`, `api.coingecko.com`, dan
`query1.finance.yahoo.com` (tidak tersedia di sandbox tempat kode ini
ditulis — jalankan di mesin/VPS dengan akses internet normal).

```bash
pip install -r requirements.txt
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Buka `http://localhost:8000` di browser. Dashboard auto-refresh tiap 60 detik;
backend refresh cache data setiap 5 menit (`CACHE_TTL_SECONDS` di `backend/config.py`).

## Struktur

```
backend/
  config.py       daftar instrumen & endpoint data source
  data_sources.py fetch OHLCV dari Binance / Yahoo Finance / CoinGecko
  indicators.py   perhitungan EMA, RSI, MACD, Bollinger, ATR, support/resistance
  analysis.py     gabungkan indikator jadi sinyal BUY/SELL/HOLD
  app.py          FastAPI app + background cache refresher + API endpoint
frontend/
  index.html, app.js, style.css   dashboard statis (vanilla JS)
```

## Catatan

- Daftar LQ45 di `backend/config.py` adalah snapshot statis — IDX merevisi
  konstituen LQ45 dua kali setahun (Feb & Agu), jadi perlu di-update berkala.
- Endpoint API: `GET /api/analysis?group=all|crypto|lq45|nasdaq|xau`
