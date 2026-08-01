# TradingBot — Analisa M30

Dashboard web yang menampilkan analisa teknikal timeframe M30 (30 menit) untuk:

- **Top 10 Crypto** (by market cap, non-stablecoin) — data dari Binance, ranking dari CoinGecko
- **LQ45 Saham** (45 saham IDX) — data dari Yahoo Finance
- **NASDAQ Composite** (`^IXIC`) — data dari Yahoo Finance
- **XAUUSD** (emas vs USD, fallback ke futures `GC=F`) — data dari Yahoo Finance

Untuk tiap instrumen dihitung EMA9/21/50, RSI14, MACD, Bollinger Bands, ATR14,
serta support/resistance dari 20 candle terakhir, lalu digabung jadi sinyal
sederhana **BUY / WEAK BUY / HOLD / WEAK SELL / SELL** dengan confidence score.

Dashboard juga menampilkan **berita per instrumen**, di-refresh tiap 1 jam,
diambil dari RSS feed per-simbol Yahoo Finance (gratis, tanpa API key) —
berlaku untuk crypto, saham, index, maupun emas.

> Sinyal ini heuristik rule-based, bukan nasihat keuangan.

## Menjalankan

Butuh akses internet ke `api.coingecko.com`, `query1.finance.yahoo.com`,
`feeds.finance.yahoo.com`, dan Binance (`api.binance.com`, dengan fallback
otomatis ke mirror publik `data-api.binance.vision` kalau host utama
diblokir jaringan/geo-restricted).

```bash
pip install -r requirements.txt
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Buka `http://localhost:8000` di browser. Dashboard auto-refresh harga tiap 60
detik (backend refresh cache harga tiap 5 menit — `CACHE_TTL_SECONDS`) dan
berita tiap 5 menit di frontend (backend refresh cache berita tiap 1 jam —
`NEWS_CACHE_TTL_SECONDS`, keduanya di `backend/config.py`).

## Struktur

```
backend/
  config.py       daftar instrumen & endpoint data source
  data_sources.py fetch OHLCV & news dari Binance / Yahoo Finance / CoinGecko
  indicators.py   perhitungan EMA, RSI, MACD, Bollinger, ATR, support/resistance
  analysis.py     gabungkan indikator jadi sinyal BUY/SELL/HOLD
  app.py          FastAPI app + background cache refresher (harga + berita) + API endpoint
frontend/
  index.html, app.js, style.css   dashboard statis (vanilla JS)
```

## Catatan

- Daftar LQ45 di `backend/config.py` adalah snapshot statis — IDX merevisi
  konstituen LQ45 dua kali setahun (Feb & Agu), jadi perlu di-update berkala.
- Cakupan berita untuk saham LQ45 yang lebih kecil/kurang liputan bahasa
  Inggris bisa kosong — itu keterbatasan sumber (Yahoo Finance RSS bahasa
  Inggris), bukan bug.
- Endpoint API: `GET /api/analysis?group=all|crypto|lq45|nasdaq|xau`,
  `GET /api/news?group=all|crypto|lq45|nasdaq|xau`
