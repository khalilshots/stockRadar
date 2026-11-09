import { useCallback, useEffect, useRef, useState } from "react"

import { Funnel } from "@/components/Funnel"
import { Header } from "@/components/Header"
import { DroppedTable, PicksTable, WatchlistTable } from "@/components/Tables"
import { TickerDetail } from "@/components/TickerDetail"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { DEMO, REPO_URL, api } from "@/lib/api"
import { cn } from "@/lib/utils"

const POLL_MS = 1500

function when(iso) {
  if (!iso) return ""
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })
}

export default function App() {
  const [status, setStatus] = useState(null)
  const [strategies, setStrategies] = useState([])
  const [strategy, setStrategy] = useState("")
  const [scan, setScan] = useState(null)
  const [recent, setRecent] = useState([])
  const [selected, setSelected] = useState(null)
  const [tab, setTab] = useState("picks")
  const [error, setError] = useState(null)
  const [apiDown, setApiDown] = useState(false)
  const pollRef = useRef(null)

  const refreshRecent = useCallback(() => api.scans().then(setRecent).catch(() => {}), [])

  const follow = useCallback((id) => {
    clearTimeout(pollRef.current)
    const tick = async () => {
      try {
        const s = await api.scan(id)
        setScan(s)
        if (s.status === "running") {
          pollRef.current = setTimeout(tick, POLL_MS)
        } else {
          refreshRecent()
          api.status().then(setStatus).catch(() => {})
          if (s.status === "failed") setError(`Scan failed: ${s.error}`)
        }
      } catch (e) {
        setError(e.message)
      }
    }
    tick()
  }, [refreshRecent])

  useEffect(() => {
    Promise.all([api.status(), api.strategies()])
      .then(([st, strats]) => {
        setStatus(st)
        setStrategies(strats)
        setStrategy(strats[0]?.name ?? "")
        if (st.scan_running) follow(st.scan_running)
        else api.latest().then((s) => { setScan(s); setStrategy(s.strategy) }).catch(() => {})
        refreshRecent()
      })
      .catch(() => setApiDown(true))
    return () => clearTimeout(pollRef.current)
  }, [follow, refreshRecent])

  const run = async (tickers) => {
    setError(null)
    setSelected(null)
    try {
      const { id } = await api.startScan(strategy, tickers)
      setTab("picks")
      follow(id)
    } catch (e) {
      setError(e.message)
    }
  }

  const open = (id) => {
    setSelected(null)
    setError(null)
    follow(id)
  }

  const running = scan?.status === "running"
  const picks = scan?.final ?? []

  return (
    <div className="mx-auto flex min-h-svh max-w-[1240px] flex-col gap-6 px-4 py-6 sm:px-6 lg:py-8">
      <Header
        status={status}
        strategies={strategies}
        strategy={strategy}
        onStrategy={setStrategy}
        onRun={run}
        running={running}
        apiDown={apiDown}
      />

      {DEMO && scan && (
        <p className="rounded-md border border-rule bg-sheet px-4 py-3 text-sm text-slate">
          This is a saved scan from {when(scan.started_at)}, run on real market data. Click any ticker to see each agent's
          call on it. Live scans need the backend and a local model, so{" "}
          <a href={REPO_URL} className="font-medium text-ink underline underline-offset-4">clone the repo</a> to run your own.
        </p>
      )}

      {apiDown && (
        <div role="alert" className="rounded-md border border-down/40 bg-down/8 px-4 py-3 text-sm text-ink">
          {DEMO ? "No sample scan is published yet." : <>Can't reach the API. Start it from the backend folder with <code className="rounded bg-muted px-1.5 py-0.5">uvicorn main:app --reload</code>, then refresh.</>}
        </div>
      )}
      {error && (
        <div role="alert" className="rounded-md border border-down/40 bg-down/8 px-4 py-3 text-sm text-ink">{error}</div>
      )}

      <Funnel scan={scan} />

      {!scan && !apiDown && (
        <p className="text-sm text-slate">
          No scans yet. Pick a strategy and run one. Leave tickers empty to pull from Yahoo's gainers and most-active lists.
        </p>
      )}

      {scan && (
        <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
          <section className="min-w-0 rounded-lg border border-rule bg-sheet p-4">
            <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-base font-semibold text-ink">{scan.strategy}</h2>
              <span className="text-xs text-slate">
                {running ? "Running since" : "Ran"} {when(scan.started_at)}
                {scan.llm?.model && !running && (scan.llm.used ? `, graded by ${scan.llm.model}` : ", model unreachable so rules only")}
              </span>
            </div>
            <Tabs value={tab} onValueChange={setTab}>
              <TabsList>
                <TabsTrigger value="picks">Picks <span className="num text-slate">{picks.length}</span></TabsTrigger>
                <TabsTrigger value="watchlist">Watchlist <span className="num text-slate">{scan.watchlist.length}</span></TabsTrigger>
                <TabsTrigger value="dropped">Filtered out <span className="num text-slate">{scan.dropped.length}</span></TabsTrigger>
              </TabsList>
              <TabsContent value="picks">
                {running && !picks.length
                  ? <p className="px-3 py-10 text-center text-sm text-slate">Picks show up here when the analysis team finishes.</p>
                  : <PicksTable picks={picks} selected={selected} onSelect={setSelected} />}
              </TabsContent>
              <TabsContent value="watchlist">
                <WatchlistTable items={scan.watchlist} selected={selected} onSelect={setSelected} />
              </TabsContent>
              <TabsContent value="dropped">
                <DroppedTable dropped={scan.dropped} selected={selected} onSelect={setSelected} />
              </TabsContent>
            </Tabs>
          </section>

          <aside className="rounded-lg border border-rule bg-sheet p-4 lg:sticky lg:top-6" aria-label="Ticker detail">
            <TickerDetail key={`${scan.id}-${selected}`} scanId={scan.id} ticker={selected} />
          </aside>
        </div>
      )}

      {recent.length > 1 && (
        <section className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold text-ink">Earlier scans</h2>
          <ul className="flex flex-wrap gap-2">
            {recent.map((r) => (
              <li key={r.id}>
                <button
                  onClick={() => open(r.id)}
                  className={cn(
                    "rounded-md border border-rule bg-sheet px-3 py-1.5 text-left text-xs outline-none hover:border-ink/30 focus-visible:ring-2 focus-visible:ring-ring/50",
                    scan?.id === r.id && "border-blip"
                  )}
                >
                  <span className="block font-medium text-ink">{when(r.started_at)}</span>
                  <span className="num text-slate">
                    {r.status === "done" ? `${r.counts?.final ?? 0} picks from ${r.counts?.universe ?? 0}` : r.status}
                    {r.trigger && r.trigger !== "manual" ? `, ${r.trigger}` : ""}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <footer className="mt-auto pt-4 text-xs text-slate">
        Research tool, not financial advice. Plans assume you size every trade to the strategy's dollar risk.
      </footer>
    </div>
  )
}
