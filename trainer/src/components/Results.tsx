import { digraphStats, msToWpm, transitionStats, type Sample, type Summary } from '@/lib/engine'
import { TRANSITION_LABELS, type Transition } from '@/lib/layouts'
import { cn } from '@/lib/utils'

const TONE: Record<Transition, string> = {
  slide: 'bg-emerald-400',
  alternate: 'bg-indigo-400',
  roll: 'bg-sky-400',
  sfb: 'bg-rose-400',
}

export type HistoryEntry = {
  at: number
  wpm: number
  accuracy: number
  slideMs: number | null
  alternateMs: number | null
}

type Props = {
  summary: Summary
  samples: Sample[]
  history: HistoryEntry[]
  layoutName: string
}

export function Results({ summary, samples, history, layoutName }: Props) {
  const stats = transitionStats(samples)
  const slide = stats.find((s) => s.kind === 'slide')!
  const alt = stats.find((s) => s.kind === 'alternate')!
  const maxWpm = Math.max(...stats.filter((s) => s.count).map((s) => msToWpm(s.medianMs)), 1)
  const slides = digraphStats(samples, 'slide', 6)
  const sfbs = digraphStats(samples, 'sfb', 4)

  let verdict: string
  if (slide.count < 5 || alt.count < 5) {
    verdict = 'Not enough slides or hand switches yet for a comparison. Try a longer test or slide drill.'
  } else {
    const diff = (slide.medianMs - alt.medianMs) / alt.medianMs
    const pct = Math.abs(diff * 100).toFixed(0)
    verdict =
      Math.abs(diff) < 0.05
        ? `Your slides are as fast as hand switches (within ${pct}%). The bet is paying off.`
        : diff < 0
          ? `Your slides are ${pct}% faster than hand switches.`
          : `Your slides are ${pct}% slower than hand switches.`
  }

  return (
    <div className="grid gap-6 md:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
      <div className="space-y-5">
        <div className="flex items-end gap-6">
          <Stat label="wpm" value={summary.wpm.toFixed(0)} big />
          <Stat label="accuracy" value={`${summary.accuracy.toFixed(0)}%`} />
          <Stat label="raw" value={summary.raw.toFixed(0)} />
          <Stat label="time" value={`${summary.seconds.toFixed(0)}s`} />
        </div>
        <p className="text-sm leading-relaxed text-zinc-300">{verdict}</p>
        {history.length > 1 && (
          <div>
            <h3 className="mb-2 text-xs font-medium tracking-wide text-zinc-500 uppercase">
              Last {history.length} runs on {layoutName}
            </h3>
            <Sparkline values={history.map((h) => h.wpm)} />
          </div>
        )}
      </div>

      <div className="space-y-4">
        <h3 className="text-xs font-medium tracking-wide text-zinc-500 uppercase">
          Median time per transition
        </h3>
        <div className="space-y-2.5">
          {stats.map((s) => (
            <div key={s.kind} className="grid grid-cols-[11rem_1fr_6.5rem] items-center gap-3 text-sm">
              <span className="text-zinc-300">{TRANSITION_LABELS[s.kind]}</span>
              <div className="h-2 overflow-hidden rounded-full bg-white/5">
                {s.count > 0 && (
                  <div
                    className={cn('h-full rounded-full', TONE[s.kind])}
                    style={{ width: `${(msToWpm(s.medianMs) / maxWpm) * 100}%` }}
                  />
                )}
              </div>
              <span className="text-right font-mono text-xs text-zinc-400 tabular-nums">
                {s.count ? `${s.medianMs.toFixed(0)}ms · ${s.count}×` : '—'}
              </span>
            </div>
          ))}
        </div>
        <p className="text-xs text-zinc-500">
          Bar length is the speed that transition would sustain (12,000 ÷ ms = wpm). Pauses over 1s
          and anything after a typo are skipped.
        </p>
        {(slides.length > 0 || sfbs.length > 0) && (
          <div className="flex flex-wrap gap-x-8 gap-y-3 pt-1">
            <DigraphList title="Your slides" items={slides} tone="text-emerald-300" />
            <DigraphList title="Same-finger misses" items={sfbs} tone="text-rose-300" />
          </div>
        )}
      </div>
    </div>
  )
}

function Stat({ label, value, big }: { label: string; value: string; big?: boolean }) {
  return (
    <div>
      <div className="text-xs tracking-wide text-zinc-500 uppercase">{label}</div>
      <div className={cn('font-mono font-semibold tabular-nums', big ? 'text-6xl text-amber-300' : 'text-2xl text-zinc-100')}>
        {value}
      </div>
    </div>
  )
}

function DigraphList({
  title,
  items,
  tone,
}: {
  title: string
  items: { digraph: string; count: number; medianMs: number }[]
  tone: string
}) {
  if (!items.length) return null
  return (
    <div>
      <h4 className="mb-1.5 text-xs text-zinc-500">{title}</h4>
      <ul className="space-y-0.5 font-mono text-xs">
        {items.map((d) => (
          <li key={d.digraph} className="flex gap-3">
            <span className={cn('w-6', tone)}>{d.digraph}</span>
            <span className="text-zinc-400 tabular-nums">
              {d.medianMs.toFixed(0)}ms · {d.count}×
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function Sparkline({ values }: { values: number[] }) {
  const max = Math.max(...values)
  const min = Math.min(...values)
  const span = Math.max(max - min, 1)
  const w = 220
  const h = 44
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * w},${h - ((v - min) / span) * (h - 6) - 3}`)
  return (
    <div className="flex items-center gap-3">
      <svg width={w} height={h} className="overflow-visible">
        <polyline points={pts.join(' ')} fill="none" className="stroke-amber-300" strokeWidth={2} strokeLinejoin="round" />
      </svg>
      <span className="font-mono text-xs text-zinc-400">
        {min.toFixed(0)}–{max.toFixed(0)} wpm
      </span>
    </div>
  )
}
