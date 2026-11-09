import { useState } from "react"
import { CodeXml, LoaderCircle } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input, NativeSelect } from "@/components/ui/input"
import { DEMO, REPO_URL } from "@/lib/api"
import { cn } from "@/lib/utils"

const SOURCE_NAMES = {
  yfinance: "Yahoo",
  finnhub: "Finnhub",
  alpha_vantage: "Alpha Vantage",
  fred: "FRED",
  newsapi: "NewsAPI",
}

export function RadarMark({ className }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <circle cx="16" cy="16" r="14" fill="none" stroke="currentColor" strokeOpacity=".35" strokeWidth="1.5" />
      <circle cx="16" cy="16" r="8.5" fill="none" stroke="currentColor" strokeOpacity=".35" strokeWidth="1.5" />
      <path d="M16 16 L16 2 A14 14 0 0 1 29.2 11.4 Z" fill="currentColor" fillOpacity=".14" />
      <circle cx="22.5" cy="9" r="2.6" fill="var(--blip)" />
    </svg>
  )
}

function nextRun(nextRuns) {
  const times = Object.entries(nextRuns || {}).filter(([, t]) => t)
  if (!times.length) return null
  const [session, at] = times.sort((a, b) => new Date(a[1]) - new Date(b[1]))[0]
  const when = new Date(at).toLocaleString(undefined, { weekday: "short", hour: "numeric", minute: "2-digit" })
  return `next ${session} scan ${when}`
}

export function Header({ status, strategies, strategy, onStrategy, onRun, running, apiDown }) {
  const [tickers, setTickers] = useState("")

  const submit = (e) => {
    e.preventDefault()
    const list = tickers.split(/[\s,]+/).map((t) => t.trim().toUpperCase()).filter(Boolean)
    onRun(list)
  }

  return (
    <header className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <RadarMark className="size-9 text-ink" />
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-ink">Stock Radar</h1>
            <p className="text-sm text-slate">Two agent teams screen the market, then rank what's left.</p>
          </div>
        </div>

        {DEMO ? (
          <a
            href={REPO_URL}
            className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground outline-none hover:bg-primary/85 focus-visible:ring-2 focus-visible:ring-ring/50"
          >
            <CodeXml className="size-4" />
            View code
          </a>
        ) : (
        <form onSubmit={submit} className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
          <label className="sr-only" htmlFor="strategy">Strategy</label>
          <NativeSelect id="strategy" value={strategy} onChange={(e) => onStrategy(e.target.value)} disabled={!strategies.length}>
            {strategies.map((s) => (
              <option key={s.name} value={s.name}>{s.name}</option>
            ))}
          </NativeSelect>
          <label className="sr-only" htmlFor="tickers">Tickers to scan</label>
          <Input
            id="tickers"
            value={tickers}
            onChange={(e) => setTickers(e.target.value)}
            placeholder="Tickers (optional)"
            className="w-full sm:w-44"
          />
          <Button type="submit" size="lg" className="px-4 font-semibold" disabled={running || apiDown || !strategy}>
            {running && <LoaderCircle className="animate-spin" />}
            {running ? "Scanning" : "Run scan"}
          </Button>
        </form>
        )}
      </div>

      {status && (
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-slate">
          <span>
            Model <span className="font-medium text-ink">{status.llm_model ?? "off, rules only"}</span>
          </span>
          <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
            {Object.entries(status.sources).map(([key, on]) => (
              <span key={key} className="flex items-center gap-1.5" title={on ? "connected" : "no api key"}>
                <span className={cn("size-1.5 rounded-full", on ? "bg-up" : "bg-rule")} />
                <span className={on ? "text-ink" : "text-slate/80"}>{SOURCE_NAMES[key] ?? key}</span>
              </span>
            ))}
          </span>
          {status.scheduler?.enabled && <span>{nextRun(status.scheduler.next_runs)}</span>}
        </div>
      )}
    </header>
  )
}
