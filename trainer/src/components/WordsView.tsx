import { useLayoutEffect, useRef, useState } from 'react'

import { cn } from '@/lib/utils'

type Props = {
  words: string[]
  typed: string[]
  index: number
  idle: boolean
}

const LINE_HEIGHT = 2.6 // rem, keep in sync with leading below

export function WordsView({ words, typed, index, idle }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const activeRef = useRef<HTMLSpanElement>(null)
  const [offset, setOffset] = useState(0)

  useLayoutEffect(() => {
    const el = activeRef.current
    const box = containerRef.current
    if (!el || !box) return
    const line = el.offsetTop
    const lh = parseFloat(getComputedStyle(document.documentElement).fontSize) * LINE_HEIGHT
    setOffset(Math.max(0, line - lh))
  }, [index, words])

  return (
    <div className="relative h-[7.8rem] overflow-hidden" aria-live="off">
      <div
        ref={containerRef}
        className="relative flex flex-wrap gap-x-[0.6em] font-mono text-[1.6rem] leading-[2.6rem] transition-transform duration-150"
        style={{ transform: `translateY(-${offset}px)` }}
      >
        {words.slice(0, Math.max(index + 60, 60)).map((word, i) => {
          const t = typed[i] ?? ''
          const done = i < index
          const wrong = done && t !== word
          const active = i === index
          const chars = [...word]
          const extra = t.length > word.length ? [...t.slice(word.length)] : []
          return (
            <span
              key={i}
              ref={active ? activeRef : undefined}
              className={cn('relative', wrong && 'underline decoration-rose-400/70 decoration-2 underline-offset-[6px]')}
            >
              {chars.map((ch, j) => {
                const typedCh = t[j]
                const state =
                  typedCh === undefined ? 'pending' : typedCh === ch ? 'ok' : 'bad'
                return (
                  <span
                    key={j}
                    className={cn(
                      'relative',
                      state === 'pending' && 'text-zinc-500',
                      state === 'ok' && 'text-zinc-100',
                      state === 'bad' && 'text-rose-400',
                    )}
                  >
                    {active && j === t.length && <Caret idle={idle} />}
                    {ch}
                  </span>
                )
              })}
              {extra.map((ch, j) => (
                <span key={`x${j}`} className="relative text-rose-400/60">
                  {ch}
                </span>
              ))}
              {active && t.length >= word.length && <Caret idle={idle} trailing />}
            </span>
          )
        })}
      </div>
    </div>
  )
}

function Caret({ idle, trailing }: { idle: boolean; trailing?: boolean }) {
  return (
    <span
      className={cn(
        'absolute top-[0.35rem] h-[1.9rem] w-[2px] rounded-full bg-amber-300',
        trailing ? 'right-[-2px]' : 'left-[-1px]',
        idle && 'animate-caret',
      )}
      aria-hidden
    />
  )
}
