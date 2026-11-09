async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      // body wasn't json
    }
    const error = new Error(detail)
    error.status = res.status
    throw error
  }
  return res.json()
}

export const DEMO = import.meta.env.VITE_DEMO === "1"
export const REPO_URL = "https://github.com/khalilshots/stockRadar"

const liveApi = {
  status: () => request("/api/status"),
  strategies: () => request("/api/strategies"),
  scans: () => request("/api/scans?limit=10"),
  latest: () => request("/api/scans/latest"),
  scan: (id) => request(`/api/scans/${id}`),
  ticker: (id, ticker) => request(`/api/scans/${id}/tickers/${ticker}`),
  startScan: (strategy, tickers) =>
    request("/api/scans", { method: "POST", body: JSON.stringify({ strategy, tickers: tickers?.length ? tickers : null }) }),
}

// the public demo has no backend, it serves one real scan exported with backend/export_demo.py
let demoScan
const loadDemo = () => {
  demoScan ??= fetch(`${import.meta.env.BASE_URL}demo-scan.json`).then((res) => {
    if (!res.ok) throw new Error("No sample scan has been published yet.")
    return res.json()
  })
  return demoScan
}

const demoApi = {
  status: async () => {
    const s = await loadDemo()
    return { llm_model: s.llm?.model ?? null, sources: s.sources, scheduler: { enabled: false }, scan_running: null }
  },
  strategies: async () => [(await loadDemo()).criteria],
  scans: async () => [],
  latest: loadDemo,
  scan: loadDemo,
  ticker: async (_id, ticker) => {
    const s = await loadDemo()
    const t = ticker.toUpperCase()
    if (!s.traces[t]) throw new Error(`${t} wasn't in this scan`)
    return {
      ticker: t,
      trace: s.traces[t],
      snapshot: s.snapshots[t] ?? null,
      candidate: s.final.find((c) => c.ticker === t) ?? null,
      dropped: s.dropped.find((d) => d.ticker === t) ?? null,
    }
  },
  startScan: async () => {
    throw new Error("This demo shows a saved scan. Clone the repo to run live scans.")
  },
}

export const api = DEMO ? demoApi : liveApi

export const AGENT_LABELS = {
  market_data: "Price data",
  price_filter: "Price & float",
  volume_agent: "Volume",
  catalyst_agent: "Catalyst",
  watchlist: "Watchlist cap",
  momentum_agent: "Momentum",
  breakout_agent: "Breakout",
  reversal_agent: "Reversal",
  setup_gate: "Setup",
  risk_agent: "Risk",
  scoring_agent: "Ranking",
}

export const money = (n) =>
  n == null ? "–" : `$${Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

export const pct = (n) => (n == null ? "–" : `${n > 0 ? "+" : ""}${Number(n).toFixed(1)}%`)

export const compact = (n) =>
  n == null ? "–" : Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(n)
