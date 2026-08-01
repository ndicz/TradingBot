# TradingBot — Analisa M30

Dashboard web yang menampilkan analisa teknikal timeframe M30 (30 menit) untuk:

- **Top 10 Crypto** (by market cap, non-stablecoin) — data dari Binance, ranking dari CoinGecko
- **LQ45 Saham** (45 saham IDX) — data dari Yahoo Finance
- **Top 100 US Stocks** (basket S&P 100, saham cap besar NYSE/NASDAQ) — data dari Yahoo Finance
- **NASDAQ Composite** (`^IXIC`) — data dari Yahoo Finance
- **XAUUSD** (emas vs USD, fallback ke futures `GC=F`) — data dari Yahoo Finance

Untuk tiap instrumen dihitung EMA9/21/50, RSI14, MACD, Bollinger Bands, ATR14,
serta support/resistance dari 20 candle terakhir, lalu digabung jadi sinyal
sederhana **BUY / WEAK BUY / HOLD / WEAK SELL / SELL** dengan confidence score.

Dashboard juga menampilkan **berita per instrumen**, di-refresh tiap 1 jam,
diambil dari RSS feed per-simbol Yahoo Finance (gratis, tanpa API key) —
berlaku untuk crypto, saham, index, maupun emas.

Crypto dan emas (lewat proxy **PAXGUSDT**, token yang backed 1:1 fisik emas)
di-stream **realtime lewat Binance WebSocket** — bukan polling REST tiap 5
menit lagi. Kalau host WebSocket-nya tidak bisa diakses (jaringan/firewall
tertentu), otomatis fallback ke REST polling seperti biasa; kolom "Data" di
tabel menunjukkan mana yang 🔴 Live vs Polling.

> Sinyal ini heuristik rule-based, bukan nasihat keuangan.

## Menjalankan

Butuh akses internet ke `api.coingecko.com`, `query1.finance.yahoo.com`,
`feeds.finance.yahoo.com`, dan Binance — baik REST (`api.binance.com`,
fallback ke mirror publik `data-api.binance.vision`) maupun WebSocket
(`stream.binance.com:9443`, host terpisah dari REST, kadang diblokir
jaringan meski REST-nya jalan — kalau begitu otomatis fallback ke polling).

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
  binance_ws.py   realtime kline streaming via Binance WebSocket (crypto + PAXGUSDT)
  indicators.py   perhitungan EMA, RSI, MACD, Bollinger, ATR, support/resistance
  analysis.py     gabungkan indikator jadi sinyal BUY/SELL/HOLD
  sentiment.py    scoring sentimen berita + gabungan sinyal teknikal+news
  app.py          FastAPI app + background cache refresher (harga + berita) + API endpoint
frontend/
  index.html, app.js, style.css   dashboard statis (vanilla JS)
```

## Catatan

- Daftar LQ45 dan Top 100 US Stocks di `backend/config.py` adalah snapshot
  statis — IDX (Feb & Agu) dan S&P (berkala) merevisi konstituennya, jadi
  perlu di-update sesekali.
- Cakupan berita untuk saham LQ45 yang lebih kecil/kurang liputan bahasa
  Inggris bisa kosong — itu keterbatasan sumber (Yahoo Finance RSS bahasa
  Inggris), bukan bug.
- Endpoint API: `GET /api/analysis?group=all|crypto|lq45|us100|nasdaq|xau`,
  `GET /api/news?group=all|crypto|lq45|us100|nasdaq|xau`
