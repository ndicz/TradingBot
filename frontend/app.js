const REFRESH_MS = 60_000;
let activeGroup = "crypto";

const tabs = document.querySelectorAll(".tab");
const tbody = document.getElementById("table-body");
const statusEl = document.getElementById("status");

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    activeGroup = tab.dataset.group;
    render();
  });
});

function signalBadge(signal) {
  let cls = "badge-hold";
  if (signal.includes("BUY")) cls = "badge-buy";
  else if (signal.includes("SELL")) cls = "badge-sell";
  return `<span class="badge ${cls}">${signal}</span>`;
}

function fmtNum(n, digits = 2) {
  if (n === null || n === undefined) return "-";
  return Number(n).toLocaleString("en-US", { maximumFractionDigits: digits });
}

function rowHtml(item) {
  if (item.status !== "ok") {
    return `<tr><td>${item.name} (${item.code})</td><td colspan="9" style="color:#8b93a7">Data tidak tersedia</td></tr>`;
  }
  const chgClass = item.change_pct >= 0 ? "pos" : "neg";
  const chgSign = item.change_pct >= 0 ? "+" : "";
  return `<tr>
    <td>${item.name} <span style="color:#8b93a7">(${item.code})</span></td>
    <td>${fmtNum(item.price, item.price < 10 ? 4 : 2)}</td>
    <td class="${chgClass}">${chgSign}${fmtNum(item.change_pct)}%</td>
    <td>${item.trend}</td>
    <td>${fmtNum(item.rsi14, 1)}</td>
    <td>${fmtNum(item.support, item.support < 10 ? 4 : 2)}</td>
    <td>${fmtNum(item.resistance, item.resistance < 10 ? 4 : 2)}</td>
    <td>${signalBadge(item.signal)}</td>
    <td>${item.confidence}%</td>
    <td>${item.last_candle_time ? new Date(item.last_candle_time).toLocaleString() : "-"}</td>
  </tr>`;
}

let latestData = null;

function render() {
  if (!latestData) return;
  const items = latestData.data[activeGroup] || [];
  tbody.innerHTML = items.length
    ? items.map(rowHtml).join("")
    : `<tr><td colspan="10">Tidak ada data untuk grup ini.</td></tr>`;
}

async function fetchAnalysis() {
  try {
    const res = await fetch("/api/analysis");
    const json = await res.json();
    latestData = json;
    statusEl.textContent = json.updated_at
      ? `Status: ${json.status} · Update terakhir: ${new Date(json.updated_at * 1000).toLocaleTimeString()}`
      : `Status: ${json.status}`;
    render();
  } catch (err) {
    statusEl.textContent = "Gagal memuat data dari server.";
    console.error(err);
  }
}

fetchAnalysis();
setInterval(fetchAnalysis, REFRESH_MS);
