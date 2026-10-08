import { useMemo } from 'react'

import { WORDS } from '@/data/words'
import { classify, FINGER_NAMES, type Compiled } from '@/lib/layouts'
import { cn } from '@/lib/utils'

/** Column stagger (pinky -> inner) as a fraction of key size, highest column = 0. */
const STAGGER = [0.72, 0.24, 0, 0.24, 0.4]

/** Share of (rank-weighted) digraphs in common words that each slide accounts for. */
function useSlideShares(layout: Compiled) {
  return useMemo(() => {
    const counts = new Map<string, number>()
    let total = 0
    WORDS.forEach((w, rank) => {
      const weight = 1 / (rank + 10)
      for (let i = 0; i + 1 < w.length; i++) {
        const d = w.slice(i, i + 2)
        counts.set(d, (counts.get(d) ?? 0) + weight)
        total += weight
      }
    })
    const shares = new Map<string, number>()
    for (let c = 0; c < 10; c++) {
      const [t, h, b] = layout.rows.map((r) => r[c].toLowerCase())
      shares.set(`top:${c}`, (counts.get(t + h) ?? 0) / total)
      shares.set(`bottom:${c}`, (counts.get(h + b) ?? 0) / total)
    }
    return shares
  }, [layout])
}

type Props = {
  layout: Compiled
  prevChar: string | null
  nextChar: string | null
  flash: { ch: string; id: number } | null
}

export function Keymap({ layout, prevChar, nextChar, flash }: Props) {
  const shares = useSlideShares(layout)
  const activeSlide =
    prevChar && nextChar && classify(layout, prevChar, nextChar) === 'slide'
      ? layout.charToPos.get(prevChar)!
      : null
  const activeSlideRow = activeSlide
    ? activeSlide.row === 0
      ? 'top'
      : 'bottom'
    : null

  const half = (side: 'left' | 'right') => {
    const cols = side === 'left' ? [0, 1, 2, 3, 4] : [5, 6, 7, 8, 9]
    return (
      <div className="flex items-start gap-[calc(var(--k)*0.1)]">
        {side === 'left' && <Ghost className="mt-[calc(var(--k)*3)]" />}
        {cols.map((col) => {
          const fi = col < 5 ? col : 9 - col
          const slideCol = activeSlide?.col === col ? activeSlideRow : null
          return (
            <div key={col} className="flex flex-col items-center" style={{ marginTop: `calc(var(--k) * ${STAGGER[fi]})` }}>
              {[0, 1, 2].map((row) => {
                const ch = layout.rows[row][col].toLowerCase()
                const kind = row === 1 ? 'home' : row === 0 ? 'top' : 'bottom'
                const share = row === 1 ? 0 : (shares.get(`${kind}:${col}`) ?? 0)
                const strong = share >= 0.002
                const inSlide =
                  slideCol !== null &&
                  ((slideCol === 'top' && row <= 1) || (slideCol === 'bottom' && row >= 1))
                return (
                  <div key={row} className="flex flex-col items-center">
                    {row === 1 && (
                      <Arrow active={slideCol === 'top'} visible={(shares.get(`top:${col}`) ?? 0) >= 0.002} tone="top" />
                    )}
                    <Key
                      ch={ch}
                      kind={kind}
                      strong={strong}
                      next={nextChar === ch}
                      inSlide={inSlide}
                      flashId={flash?.ch === ch ? flash.id : null}
                    />
                    {row === 1 && (
                      <Arrow active={slideCol === 'bottom'} visible={(shares.get(`bottom:${col}`) ?? 0) >= 0.002} tone="bottom" />
                    )}
                  </div>
                )
              })}
              <span className="mt-1.5 hidden text-[10px] tracking-wide text-muted-foreground/70 uppercase sm:block">
                {FINGER_NAMES[fi]}
              </span>
            </div>
          )
        })}
        {side === 'right' && <Ghost className="mt-[calc(var(--k)*3)]" />}
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center [--k:clamp(21px,5.4vw,56px)]">
      <div className="flex items-start gap-[calc(var(--k)*1.4)]">
        {half('left')}
        {half('right')}
      </div>
      <div className="-mt-[calc(var(--k)*0.2)] flex gap-[calc(var(--k)*3.1)]">
        <div className="flex gap-[calc(var(--k)*0.12)] pl-[calc(var(--k)*2.6)]">
          <Ghost />
          <Ghost />
          <Ghost label="space" />
        </div>
        <div className="flex gap-[calc(var(--k)*0.12)] pr-[calc(var(--k)*2.6)]">
          <Ghost label="space" />
          <Ghost />
          <Ghost />
        </div>
      </div>
    </div>
  )
}

function Key({
  ch,
  kind,
  strong,
  next,
  inSlide,
  flashId,
}: {
  ch: string
  kind: 'home' | 'top' | 'bottom'
  strong: boolean
  next: boolean
  inSlide: boolean
  flashId: number | null
}) {
  return (
    <div
      key={flashId ?? 'idle'}
      className={cn(
        'relative grid size-(--k) place-items-center rounded-[calc(var(--k)*0.2)] border font-mono text-[calc(var(--k)*0.42)] font-semibold transition-[transform,box-shadow] duration-100 select-none',
        kind === 'home' && 'border-indigo-400/40 bg-indigo-500/25 text-indigo-100',
        kind === 'top' && (strong ? 'border-teal-400/45 bg-teal-400/10 text-teal-100' : 'border-white/10 bg-white/[0.03] text-zinc-400'),
        kind === 'bottom' && (strong ? 'border-amber-400/45 bg-amber-400/10 text-amber-100' : 'border-white/10 bg-white/[0.03] text-zinc-400'),
        inSlide && 'border-emerald-300 shadow-[0_0_0_2px_rgba(110,231,183,0.35),0_0_18px_rgba(110,231,183,0.35)]',
        next && 'scale-105 border-white bg-white text-zinc-900 shadow-[0_0_20px_rgba(255,255,255,0.25)]',
        flashId !== null && 'animate-key-flash',
      )}
    >
      {ch}
    </div>
  )
}

function Arrow({ active, visible, tone }: { active: boolean; visible: boolean; tone: 'top' | 'bottom' }) {
  return (
    <div className="relative h-[calc(var(--k)*0.14)] w-full">
      <svg
        viewBox="0 0 10 6"
        className={cn(
          'absolute left-1/2 top-1/2 h-[calc(var(--k)*0.2)] -translate-x-1/2 -translate-y-1/2 transition-opacity',
          !visible && !active && 'opacity-0',
          visible && !active && 'opacity-60',
          active && 'opacity-100 drop-shadow-[0_0_6px_rgba(110,231,183,0.9)]',
          active ? 'fill-emerald-300' : tone === 'top' ? 'fill-teal-300' : 'fill-amber-300',
        )}
        aria-hidden
      >
        <path d="M0 0 L10 0 L5 6 Z" />
      </svg>
    </div>
  )
}

function Ghost({ label, className }: { label?: string; className?: string }) {
  return (
    <div
      className={cn(
        'grid size-(--k) place-items-center rounded-[calc(var(--k)*0.2)] border border-dashed border-white/10 text-[10px] text-zinc-600',
        className,
      )}
    >
      {label}
    </div>
  )
}
