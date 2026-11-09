import { useEffect, useState } from "react"
import { Check, ExternalLink, Minus, X } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { AGENT_LABELS, api, compact, money, pct } from "@/lib/api"
import { cn } from "@/lib/utils"

function Stat({ label, value, className }) {
  return (
    <div>
      <dt className="text-xs text-slate">{label}</dt>
      <dd className={cn("num font-medium text-ink", className)}>{value}</dd>
    </div>
  )
}

function StepIcon({ step }) {
  if (step.source === "skipped") return <Minus className="size-3.5 text-slate" aria-label="skipped" />
  return step.passed
    ? <Check className="size-3.5 text-up" aria-label="passed" />
    : <X className="size-3.5 text-down" aria-label="failed" />
}

export function TickerDetail({ scanId, ticker }) {
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!scanId || !ticker) return
    let live = true
    api.ticker(scanId, ticker).then((d) => live && setDetail(d)).catch((e) => live && setError(e.message))
    return () => { live = false }
  }, [scanId, ticker])

  if (!ticker) {
    return (
      <p className="text-sm text-slate">
        Pick a ticker to see each agent's call on it, in the order they ran.
      </p>
    )
  }
  if (error) return <p className="text-sm text-down">{error}</p>
  if (!detail) return <p className="text-sm text-slate">Loading {ticker}</p>

  const { candidate: c, snapshot: s, trace, dropped } = detail
  const catalyst = trace.find((t) => t.agent === "catalyst_agent")?.data

  return (
    <article className="flex flex-col gap-5">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold tracking-wide text-ink">{ticker}</h2>
          <p className="text-sm text-slate">{c?.name ?? (dropped ? `Dropped by ${(AGENT_LABELS[dropped.agent] ?? dropped.agent).toLowerCase()}` : "On the watchlist")}</p>
        </div>
        {c && (
          <div className="text-right">
            <div className="num text-3xl font-semibold leading-none text-ink">{c.score}</div>
            <div className="text-xs text-slate">score</div>
          </div>
        )}
      </header>

      {c && <p className="text-[15px] leading-relaxed text-ink">{c.summary}</p>}

      {c && (
        <dl className="grid grid-cols-3 gap-x-4 gap-y-3 rounded-md bg-muted/70 p-3">
          <Stat label="Entry" value={money(c.plan.entry)} />
          <Stat label="Stop" value={money(c.plan.stop)} className="text-down" />
          <Stat label="Risk" value={`${c.plan.stop_percent}%`} />
          <Stat label="Target 2R" value={money(c.plan.target_1)} className="text-up" />
          <Stat label="Target 3R" value={money(c.plan.target_2)} className="text-up" />
          <Stat label="Shares" value={c.plan.shares.toLocaleString()} />
        </dl>
      )}

      {catalyst?.headline && (
        <a href={catalyst.url} target="_blank" rel="noreferrer" className="group flex items-start gap-2 text-sm text-ink hover:underline">
          <span className="leading-snug">{catalyst.headline}</span>
          <ExternalLink className="mt-0.5 size-3.5 shrink-0 text-slate" />
        </a>
      )}

      {s && (
        <dl className="grid grid-cols-3 gap-x-4 gap-y-3 text-sm">
          <Stat label="Price" value={money(s.price)} />
          <Stat label="Today" value={pct(s.change_percent)} className={s.change_percent >= 0 ? "text-up" : "text-down"} />
          <Stat label="Gap" value={pct(s.gap_percent)} />
          <Stat label="Volume" value={`${compact(s.volume)}, ${s.relative_volume}x`} />
          <Stat label="RSI 14" value={s.rsi_14 ?? "–"} />
          <Stat label="20d high" value={money(s.high_20)} />
        </dl>
      )}

      <section>
        <h3 className="mb-2 text-sm font-semibold text-ink">Agent calls</h3>
        <ol className="flex flex-col">
          {trace.map((step, i) => (
            <li key={`${step.agent}-${i}`} className="grid grid-cols-[1.5rem_1fr] gap-x-2 border-t border-rule py-2.5 first:border-t-0">
              <span className="num pt-0.5 text-xs text-slate">{i + 1}</span>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <StepIcon step={step} />
                  <span className="text-sm font-medium text-ink">{AGENT_LABELS[step.agent] ?? step.agent}</span>
                  {step.source === "llm" && <Badge variant="blip">LLM</Badge>}
                  {step.data?.score != null && step.agent !== "scoring_agent" && (
                    <span className="num ml-auto text-xs text-slate">{step.data.score}</span>
                  )}
                </div>
                <p className="mt-0.5 text-sm text-slate first-letter:uppercase">{step.reason}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </article>
  )
}
