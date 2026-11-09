import { useMemo, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Input, NativeSelect } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { AGENT_LABELS, money, pct } from "@/lib/api"
import { cn } from "@/lib/utils"

function Change({ value }) {
  return <span className={cn("num", value > 0 ? "text-up" : value < 0 ? "text-down" : "text-slate")}>{pct(value)}</span>
}

function Ticker({ ticker, name }) {
  return (
    <div className="min-w-0">
      <div className="font-semibold tracking-wide text-ink">{ticker}</div>
      {name && name !== ticker && <div className="max-w-44 truncate text-xs text-slate">{name}</div>}
    </div>
  )
}

function rowProps(ticker, selected, onSelect) {
  return {
    "data-selected": selected === ticker,
    tabIndex: 0,
    className: "cursor-pointer hover:bg-muted/70 focus-visible:bg-muted focus-visible:outline-none",
    onClick: () => onSelect(ticker),
    onKeyDown: (e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onSelect(ticker)),
  }
}

function Empty({ children }) {
  return <p className="px-3 py-10 text-center text-sm text-slate">{children}</p>
}

export function PicksTable({ picks, selected, onSelect }) {
  if (!picks.length) return <Empty>Nothing made the final list. The filtered-out tab shows where each ticker dropped.</Empty>

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-8">#</TableHead>
          <TableHead>Ticker</TableHead>
          <TableHead>Setup</TableHead>
          <TableHead>Score</TableHead>
          <TableHead className="text-right">Price</TableHead>
          <TableHead className="text-right">Stop</TableHead>
          <TableHead className="text-right">Target</TableHead>
          <TableHead className="text-right">Size</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {picks.map((p, i) => (
          <TableRow key={p.ticker} {...rowProps(p.ticker, selected, onSelect)}>
            <TableCell className="text-slate">{i + 1}</TableCell>
            <TableCell><Ticker ticker={p.ticker} name={p.name} /></TableCell>
            <TableCell><Badge variant="blip">{p.setup}</Badge></TableCell>
            <TableCell>
              <div className="flex items-center gap-2">
                <span className="w-7 font-semibold text-ink">{p.score}</span>
                <span className="hidden h-1.5 w-16 overflow-hidden rounded-full bg-muted md:block">
                  <span className="block h-full rounded-full bg-ink/70" style={{ width: `${p.score}%` }} />
                </span>
              </div>
            </TableCell>
            <TableCell className="text-right">
              <div className="text-ink">{money(p.price)}</div>
              <Change value={p.change_percent} />
            </TableCell>
            <TableCell className="text-right text-down">{money(p.plan.stop)}</TableCell>
            <TableCell className="text-right text-up">{money(p.plan.target_1)}</TableCell>
            <TableCell className="text-right">
              <div className="text-ink">{p.plan.shares.toLocaleString()} sh</div>
              <div className="text-xs text-slate">{money(p.plan.position_value)}</div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

export function WatchlistTable({ items, selected, onSelect }) {
  if (!items.length) return <Empty>No ticker got through the discovery team on this scan.</Empty>

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Ticker</TableHead>
          <TableHead className="text-right">Price</TableHead>
          <TableHead className="text-right">Today</TableHead>
          <TableHead className="text-right">Rel. volume</TableHead>
          <TableHead>Catalyst</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((w) => (
          <TableRow key={w.ticker} {...rowProps(w.ticker, selected, onSelect)}>
            <TableCell><Ticker ticker={w.ticker} name={w.name} /></TableCell>
            <TableCell className="text-right">{money(w.price)}</TableCell>
            <TableCell className="text-right"><Change value={w.change_percent} /></TableCell>
            <TableCell className="text-right">{w.relative_volume}x</TableCell>
            <TableCell className="max-w-72 truncate text-slate">{w.catalyst ?? "not checked"}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

const PAGE = 100

export function DroppedTable({ dropped, selected, onSelect }) {
  const [query, setQuery] = useState("")
  const [agent, setAgent] = useState("")
  const [limit, setLimit] = useState(PAGE)

  const agents = useMemo(() => [...new Set(dropped.map((d) => d.agent))], [dropped])
  const rows = useMemo(() => {
    const q = query.trim().toUpperCase()
    return dropped.filter((d) => (!agent || d.agent === agent) && (!q || d.ticker.includes(q) || d.reason.toUpperCase().includes(q)))
  }, [dropped, query, agent])

  if (!dropped.length) return <Empty>Nothing was filtered out.</Empty>

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        <label className="sr-only" htmlFor="drop-search">Search filtered tickers</label>
        <Input id="drop-search" placeholder="Search ticker or reason" value={query} onChange={(e) => setQuery(e.target.value)} className="w-full sm:w-60" />
        <label className="sr-only" htmlFor="drop-agent">Filter by agent</label>
        <NativeSelect id="drop-agent" value={agent} onChange={(e) => setAgent(e.target.value)}>
          <option value="">Every agent</option>
          {agents.map((a) => (
            <option key={a} value={a}>{AGENT_LABELS[a] ?? a}</option>
          ))}
        </NativeSelect>
        <span className="num self-center text-xs text-slate">{rows.length} tickers</span>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Ticker</TableHead>
            <TableHead>Dropped by</TableHead>
            <TableHead>Why</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.slice(0, limit).map((d) => (
            <TableRow key={d.ticker} {...rowProps(d.ticker, selected, onSelect)}>
              <TableCell className="font-semibold tracking-wide text-ink">{d.ticker}</TableCell>
              <TableCell><Badge variant="outline">{AGENT_LABELS[d.agent] ?? d.agent}</Badge></TableCell>
              <TableCell className="text-slate first-letter:uppercase">{d.reason}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {rows.length > limit && (
        <button className="self-start text-sm font-medium text-ink underline underline-offset-4" onClick={() => setLimit(limit + PAGE)}>
          Show {Math.min(PAGE, rows.length - limit)} more
        </button>
      )}
    </div>
  )
}

