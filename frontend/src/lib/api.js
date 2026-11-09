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

export const api = {
  status: () => request("/api/status"),
  strategies: () => request("/api/strategies"),
  scans: () => request("/api/scans?limit=10"),
  latest: () => request("/api/scans/latest"),
  scan: (id) => request(`/api/scans/${id}`),
  ticker: (id, ticker) => request(`/api/scans/${id}/tickers/${ticker}`),
  startScan: (strategy, tickers) =>
    request("/api/scans", { method: "POST", body: JSON.stringify({ strategy, tickers: tickers?.length ? tickers : null }) }),
}

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
