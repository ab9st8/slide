import { classify, type Compiled, type Transition } from '@/lib/layouts'

export type Sample = { from: string; to: string; kind: Transition; ms: number }

export type TestState = {
  words: string[]
  typed: string[]
  index: number
  startedAt: number | null
  finishedAt: number | null
  keystrokes: number
  correctKeystrokes: number
  samples: Sample[]
  /** Last correctly typed character in the current word, for transition timing. */
  chain: { ch: string; t: number } | null
  /** When true the test ends after the last word; otherwise more words are appended. */
  fixedLength: boolean
}

export type Action =
  | { type: 'reset'; words: string[]; fixedLength: boolean }
  | { type: 'append'; words: string[] }
  | { type: 'char'; ch: string; t: number; layout: Compiled }
  | { type: 'space'; t: number }
  | { type: 'backspace'; wholeWord: boolean }
  | { type: 'finish'; t: number }

/** Pauses longer than this are hesitations, not transitions. */
const MAX_SAMPLE_MS = 1000

export function initialState(words: string[], fixedLength: boolean): TestState {
  return {
    words,
    typed: [''],
    index: 0,
    startedAt: null,
    finishedAt: null,
    keystrokes: 0,
    correctKeystrokes: 0,
    samples: [],
    chain: null,
    fixedLength,
  }
}

export function reducer(s: TestState, a: Action): TestState {
  if (a.type === 'reset') return initialState(a.words, a.fixedLength)
  if (a.type === 'append') return { ...s, words: [...s.words, ...a.words] }
  if (s.finishedAt !== null) return s

  switch (a.type) {
    case 'char': {
      const word = s.words[s.index]
      const cur = s.typed[s.index]
      const expected = word[cur.length]
      const correct = a.ch === expected && cur === word.slice(0, cur.length)
      const samples = [...s.samples]
      if (correct && s.chain && a.t - s.chain.t <= MAX_SAMPLE_MS) {
        const kind = classify(a.layout, s.chain.ch, a.ch)
        if (kind) samples.push({ from: s.chain.ch, to: a.ch, kind, ms: a.t - s.chain.t })
      }
      const typed = [...s.typed]
      typed[s.index] = cur + a.ch
      const next: TestState = {
        ...s,
        typed,
        samples,
        startedAt: s.startedAt ?? a.t,
        keystrokes: s.keystrokes + 1,
        correctKeystrokes: s.correctKeystrokes + (correct ? 1 : 0),
        chain: correct ? { ch: a.ch, t: a.t } : null,
      }
      const isLast = s.fixedLength && s.index === s.words.length - 1
      if (isLast && typed[s.index] === word) next.finishedAt = a.t
      return next
    }
    case 'space': {
      const cur = s.typed[s.index]
      if (cur === '') return s
      const correct = cur === s.words[s.index]
      const base = {
        ...s,
        keystrokes: s.keystrokes + 1,
        correctKeystrokes: s.correctKeystrokes + (correct ? 1 : 0),
        chain: null,
      }
      if (s.fixedLength && s.index === s.words.length - 1) return { ...base, finishedAt: a.t }
      return { ...base, index: s.index + 1, typed: [...s.typed, ''] }
    }
    case 'backspace': {
      const cur = s.typed[s.index]
      if (cur !== '') {
        const typed = [...s.typed]
        typed[s.index] = a.wholeWord ? '' : cur.slice(0, -1)
        return { ...s, typed, chain: null }
      }
      if (s.index > 0 && s.typed[s.index - 1] !== s.words[s.index - 1]) {
        return { ...s, index: s.index - 1, typed: s.typed.slice(0, -1), chain: null }
      }
      return s
    }
    case 'finish':
      return s.startedAt === null ? s : { ...s, finishedAt: a.t }
  }
}

export type Summary = {
  wpm: number
  raw: number
  accuracy: number
  seconds: number
  words: number
}

export function summarize(s: TestState, now: number): Summary {
  const end = s.finishedAt ?? now
  const seconds = s.startedAt === null ? 0 : Math.max((end - s.startedAt) / 1000, 0.001)
  let correctChars = 0
  let rawChars = 0
  let words = 0
  for (let i = 0; i <= s.index && i < s.typed.length; i++) {
    const t = s.typed[i]
    const w = s.words[i]
    const committed = i < s.index || s.finishedAt !== null
    rawChars += t.length + (i < s.index ? 1 : 0)
    if (committed && t === w) {
      correctChars += w.length + (i < s.index ? 1 : 0)
      words++
    } else if (!committed && w.startsWith(t)) {
      correctChars += t.length
    }
  }
  const minutes = seconds / 60
  return {
    wpm: seconds ? correctChars / 5 / minutes : 0,
    raw: seconds ? rawChars / 5 / minutes : 0,
    accuracy: s.keystrokes ? (s.correctKeystrokes / s.keystrokes) * 100 : 100,
    seconds,
    words,
  }
}

export function median(xs: number[]): number {
  if (!xs.length) return NaN
  const v = [...xs].sort((a, b) => a - b)
  const m = Math.floor(v.length / 2)
  return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2
}

/** Milliseconds per keystroke -> the WPM you'd get typing only that transition. */
export function msToWpm(ms: number): number {
  return 12000 / ms
}

export type TransitionStat = { kind: Transition; count: number; medianMs: number }

export function transitionStats(samples: Sample[]): TransitionStat[] {
  const kinds: Transition[] = ['slide', 'alternate', 'roll', 'sfb']
  return kinds.map((kind) => {
    const ms = samples.filter((x) => x.kind === kind).map((x) => x.ms)
    return { kind, count: ms.length, medianMs: median(ms) }
  })
}

export function digraphStats(samples: Sample[], kind: Transition, limit = 8) {
  const by = new Map<string, number[]>()
  for (const x of samples) {
    if (x.kind !== kind) continue
    const d = x.from + x.to
    by.set(d, [...(by.get(d) ?? []), x.ms])
  }
  return [...by.entries()]
    .map(([digraph, ms]) => ({ digraph, count: ms.length, medianMs: median(ms) }))
    .sort((a, b) => b.count - a.count)
    .slice(0, limit)
}
