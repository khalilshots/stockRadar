import { AGENT_LABELS } from "@/lib/api"
import { cn } from "@/lib/utils"

const STAGES = [
  { key: "universe", label: "Scanned" },
  { key: "with_data", label: "Had price data", drops: ["data"] },
  { key: "watchlist", label: "Passed discovery", drops: ["discovery"] },
  { key: "analysis_passed", label: "Had a setup", drops: ["analysis"] },
  { key: "final", label: "Picks", drops: ["ranking"] },
]

const STAGE_NAMES = {
  starting: "Starting",
  universe: "Building the ticker list",
  "market data": "Downloading prices",
  discovery: "Discovery team",
  analysis: "Analysis team",
  scoring: "Scoring",
}

function dropSummary(dropped, stages) {
  const counts = {}
  for (const d of dropped) {
    if (!stages.includes(d.stage)) continue
    const label = AGENT_LABELS[d.agent] ?? d.agent
    counts[label] = (counts[label] ?? 0) + 1
  }
  return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 2)
}

function Drops({ items }) {
  if (!items.length) return null
  return (
    <ul className="num space-y-0.5 text-xs text-slate">
      {items.map(([label, n]) => (
        <li key={label}>
          <span className="text-down">−{n}</span> {label.toLowerCase()}
        </li>
      ))}
    </ul>
  )
}

export function Funnel({ scan }) {
  const counts = scan?.counts ?? {}
  const max = Math.max(counts.universe ?? 0, 1)
  const running = scan?.status === "running"
  const progress = scan?.progress

  const stages = STAGES.map((stage) => {
    const count = counts[stage.key] ?? 0
    return {
      ...stage,
      count,
      final: stage.key === "final",
      // sqrt so a 400 to 5 drop stays readable instead of the last bars vanishing
      size: count ? Math.max(Math.sqrt(count / max) * 100, 4) : 0,
      drops: stage.drops ? dropSummary(scan?.dropped ?? [], stage.drops) : [],
    }
  })

  return (
    <section aria-label="Scan funnel" className="relative overflow-hidden rounded-lg border border-rule bg-sheet">
      {running && <div className="radar-sweep" />}

      {/* phones: one row per stage, bar width shows what's left */}
      <ol className="flex flex-col divide-y divide-rule sm:hidden">
        {stages.map((s) => (
          <li key={s.key} className="px-4 py-3">
            <div className="flex items-baseline justify-between">
              <span className="text-sm text-slate">{s.label}</span>
              <span className="num text-xl font-semibold text-ink">{scan ? s.count : "–"}</span>
            </div>
            <div className="mt-1.5 h-2 rounded-full bg-muted">
              <div className={cn("h-full rounded-full", s.final ? "bg-blip" : "bg-ink/30")} style={{ width: `${s.size}%` }} />
            </div>
            {s.drops.length > 0 && <div className="mt-1.5"><Drops items={s.drops} /></div>}
          </li>
        ))}
      </ol>

      {/* wider screens: columns whose bars step down like a sieve */}
      <div className="hidden grid-cols-5 sm:grid">
        {stages.map((s, i) => (
          <div key={s.key} className={cn("flex flex-col", i > 0 && "border-l border-rule")}>
            <div className="px-4 pt-4">
              <div className="text-sm text-slate">{s.label}</div>
              <div className="num mt-1 text-4xl font-semibold tracking-tight text-ink">{scan ? s.count : "–"}</div>
            </div>
            <div className="mt-4 flex h-16 items-end">
              <div
                className={cn("w-full transition-[height] duration-500", s.final ? "bg-blip" : "bg-ink/20")}
                style={{ height: `${s.size}%` }}
              />
            </div>
            <div className="min-h-12 border-t border-rule px-4 py-2">
              {i === 0 && scan ? <span className="text-xs text-slate">{scan.strategy}</span> : <Drops items={s.drops} />}
            </div>
          </div>
        ))}
      </div>

      {running && progress && (
        <p className="num border-t border-rule px-4 py-2 text-xs text-slate" aria-live="polite">
          {STAGE_NAMES[progress.stage] ?? progress.stage}
          {progress.total ? `, ${progress.done} of ${progress.total}` : ""}
        </p>
      )}
    </section>
  )
}
