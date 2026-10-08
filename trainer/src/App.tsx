import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import { Keyboard, Pencil, RotateCcw } from 'lucide-react'

import { CustomLayoutDialog } from '@/components/CustomLayoutDialog'
import { Keymap } from '@/components/Keymap'
import { Results, type HistoryEntry } from '@/components/Results'
import { WordsView } from '@/components/WordsView'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { initialState, reducer, summarize, transitionStats } from '@/lib/engine'
import { compile, CUSTOM_ID, PRESETS, type Rows } from '@/lib/layouts'
import { generateWords, WORD_SOURCE_LABELS, type WordSource } from '@/lib/text'
import { usePersistentState } from '@/lib/usePersistentState'

type Length = '25' | '50' | '30s' | '60s'
const LENGTHS: Length[] = ['25', '50', '30s', '60s']
const NO_HISTORY: HistoryEntry[] = []

function lengthSpec(l: Length) {
  return l.endsWith('s')
    ? { fixed: false, seconds: parseInt(l), count: 80 }
    : { fixed: true, seconds: 0, count: parseInt(l) }
}

export default function App() {
  const [layoutId, setLayoutId] = usePersistentState('layout', 'v2')
  const [customRows, setCustomRows] = usePersistentState<Rows>('custom-rows', PRESETS[0].rows)
  const [length, setLength] = usePersistentState<Length>('length', '50')
  const [source, setSource] = usePersistentState<WordSource>('source', 'top200')
  const [punctuation, setPunctuation] = usePersistentState('punctuation', false)
  const [emulate, setEmulate] = usePersistentState('emulate', true)
  const [dialogOpen, setDialogOpen] = useState(false)

  const preset = PRESETS.find((p) => p.id === layoutId)
  const rows = preset ? preset.rows : customRows
  const layoutName = preset ? preset.name : 'Custom'
  const layout = useMemo(() => compile(rows), [rows])
  const historyKey = `history:${preset ? preset.id : rows.join('|')}`
  const [history, setHistory] = usePersistentState<HistoryEntry[]>(historyKey, NO_HISTORY)

  const spec = lengthSpec(length)
  const makeWords = useCallback(
    (n: number) => generateWords(n, source, layout, punctuation),
    [source, layout, punctuation],
  )
  const [state, dispatch] = useReducer(reducer, null, () =>
    initialState(makeWords(spec.count), spec.fixed),
  )
  const [now, setNow] = useState(() => performance.now())
  const [flash, setFlash] = useState<{ ch: string; id: number } | null>(null)

  const restart = useCallback(() => {
    dispatch({ type: 'reset', words: makeWords(spec.count), fixedLength: spec.fixed })
  }, [makeWords, spec.count, spec.fixed])

  useEffect(restart, [restart])

  const running = state.startedAt !== null && state.finishedAt === null

  useEffect(() => {
    if (!running) return
    const id = setInterval(() => setNow(performance.now()), 100)
    return () => clearInterval(id)
  }, [running])

  useEffect(() => {
    if (!running || spec.fixed || state.startedAt === null) return
    if (now - state.startedAt >= spec.seconds * 1000) {
      dispatch({ type: 'finish', t: state.startedAt + spec.seconds * 1000 })
    }
  }, [now, running, spec.fixed, spec.seconds, state.startedAt])

  useEffect(() => {
    if (!spec.fixed && state.words.length - state.index < 30) {
      dispatch({ type: 'append', words: makeWords(50) })
    }
  }, [spec.fixed, state.index, state.words.length, makeWords])

  const recorded = useRef<number | null>(null)
  useEffect(() => {
    if (state.finishedAt === null || recorded.current === state.finishedAt) return
    recorded.current = state.finishedAt
    const s = summarize(state, state.finishedAt)
    if (s.words === 0) return
    const t = transitionStats(state.samples)
    const ms = (k: string) => {
      const x = t.find((y) => y.kind === k)
      return x && x.count ? x.medianMs : null
    }
    setHistory((h) =>
      [...h, { at: Date.now(), wpm: s.wpm, accuracy: s.accuracy, slideMs: ms('slide'), alternateMs: ms('alternate') }].slice(-20),
    )
  }, [state, setHistory])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (dialogOpen) return
      if (e.key === 'Tab' || e.key === 'Escape') {
        e.preventDefault()
        restart()
        return
      }
      if (e.key === 'Backspace') {
        e.preventDefault()
        dispatch({ type: 'backspace', wholeWord: e.ctrlKey || e.altKey || e.metaKey })
        return
      }
      if (e.ctrlKey || e.metaKey || e.altKey) return
      if (e.code === 'Space' || e.key === ' ') {
        e.preventDefault()
        ;(document.activeElement as HTMLElement | null)?.blur()
        dispatch({ type: 'space', t: e.timeStamp })
        return
      }
      let ch: string | undefined
      if (emulate) {
        ch = layout.codeToChar.get(e.code)
        if (ch && e.shiftKey && /[a-z]/.test(ch)) ch = ch.toUpperCase()
      } else if (e.key.length === 1) {
        ch = e.key
      }
      if (!ch) return
      e.preventDefault()
      ;(document.activeElement as HTMLElement | null)?.blur()
      dispatch({ type: 'char', ch, t: e.timeStamp, layout })
      setFlash({ ch: ch.toLowerCase(), id: e.timeStamp })
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [dialogOpen, emulate, layout, restart])

  const summary = summarize(state, now)
  const finished = state.finishedAt !== null
  const currentWord = state.words[state.index] ?? ''
  const currentTyped = state.typed[state.index] ?? ''
  const onTrack = currentWord.startsWith(currentTyped)
  const nextChar = finished || !onTrack ? null : (currentWord[currentTyped.length] ?? null)
  const prevChar = onTrack && currentTyped.length ? currentTyped[currentTyped.length - 1] : null
  const remaining =
    !spec.fixed && state.startedAt !== null
      ? Math.max(0, Math.ceil(spec.seconds - (now - state.startedAt) / 1000))
      : spec.seconds

  return (
    <div className="min-h-svh bg-background text-foreground">
      <div className="mx-auto flex max-w-5xl flex-col gap-8 px-5 py-8 sm:px-8 sm:py-10">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="flex items-center gap-2 text-xl font-semibold tracking-tight">
              <Keyboard className="size-5 text-amber-300" />
              slide trainer
            </h1>
            <p className="mt-1 text-sm text-zinc-400">
              Try a Totem layout in the browser and time your downward slides. No flashing required.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <ToggleGroup
              type="single"
              variant="outline"
              size="sm"
              spacing={0}
              value={layoutId}
              onValueChange={(v) => {
                if (!v) return
                if (v === CUSTOM_ID) setDialogOpen(true)
                else setLayoutId(v)
              }}
              aria-label="Layout"
            >
              {PRESETS.map((p) => (
                <ToggleGroupItem key={p.id} value={p.id} className="px-3">
                  {p.name}
                </ToggleGroupItem>
              ))}
              <ToggleGroupItem value={CUSTOM_ID} className="px-3">
                Custom
              </ToggleGroupItem>
            </ToggleGroup>
            {layoutId === CUSTOM_ID && (
              <Button variant="ghost" size="icon-sm" onClick={() => setDialogOpen(true)} aria-label="Edit custom layout">
                <Pencil />
              </Button>
            )}
          </div>
        </header>

        <section className="flex flex-wrap items-center gap-x-6 gap-y-3 text-sm">
          <ToggleGroup
            type="single"
            size="sm"
            value={length}
            onValueChange={(v) => v && setLength(v as Length)}
            aria-label="Test length"
          >
            {LENGTHS.map((l) => (
              <ToggleGroupItem key={l} value={l} className="px-2.5 font-mono text-xs">
                {l.endsWith('s') ? l : `${l} words`}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
          <ToggleGroup
            type="single"
            size="sm"
            value={source}
            onValueChange={(v) => v && setSource(v as WordSource)}
            aria-label="Word source"
          >
            {(Object.keys(WORD_SOURCE_LABELS) as WordSource[]).map((s) => (
              <ToggleGroupItem key={s} value={s} className="px-2.5 text-xs">
                {WORD_SOURCE_LABELS[s]}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
          <label className="flex items-center gap-2 text-xs text-zinc-300">
            <Switch checked={punctuation} onCheckedChange={setPunctuation} />
            punctuation
          </label>
          <label className="flex items-center gap-2 text-xs text-zinc-300" title="Remaps your keys by physical position, so your keyboard can stay on QWERTY. Turn off once the layout is flashed.">
            <Switch checked={emulate} onCheckedChange={setEmulate} />
            emulate from QWERTY positions
          </label>
        </section>

        <section className="rounded-2xl border border-white/8 bg-card/60 p-6 sm:p-8">
          {finished ? (
            <Results summary={summary} samples={state.samples} history={history} layoutName={layoutName} />
          ) : (
            <>
              <div className="mb-4 flex h-8 items-baseline gap-5 font-mono text-amber-300">
                {state.startedAt === null ? (
                  <span className="text-sm text-zinc-500">
                    {emulate
                      ? `Start typing. Keys are remapped to ${layoutName}.`
                      : 'Start typing.'}
                  </span>
                ) : (
                  <>
                    <span className="text-2xl tabular-nums">
                      {spec.fixed ? `${state.index}/${state.words.length}` : remaining}
                    </span>
                    <span className="text-sm text-zinc-400 tabular-nums">{summary.wpm.toFixed(0)} wpm</span>
                  </>
                )}
              </div>
              <WordsView words={state.words} typed={state.typed} index={state.index} idle={state.startedAt === null} />
            </>
          )}
          <div className="mt-6 flex items-center justify-between gap-4 text-xs text-zinc-500">
            <span>
              <kbd className="rounded border border-white/10 px-1.5 py-0.5 font-mono text-[11px] text-zinc-300">tab</kbd>{' '}
              or{' '}
              <kbd className="rounded border border-white/10 px-1.5 py-0.5 font-mono text-[11px] text-zinc-300">esc</kbd>{' '}
              to restart
            </span>
            <Button variant="ghost" size="sm" onClick={restart} className="text-zinc-400">
              <RotateCcw /> new test
            </Button>
          </div>
        </section>

        <section className="space-y-4">
          <Keymap layout={layout} prevChar={prevChar} nextChar={nextChar} flash={flash} />
          <p className="mx-auto max-w-2xl text-center text-xs leading-relaxed text-zinc-500">
            {preset?.description ?? 'Your custom layout.'} Teal and amber keys slide into or out of
            the home key below or above them; the column lights up when the next keystroke is a slide.
          </p>
        </section>

        <p className="text-center text-xs text-zinc-600 [@media(pointer:fine)]:hidden">
          This trainer needs a physical keyboard.
        </p>
      </div>

      <CustomLayoutDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        initial={customRows}
        onSave={(r) => {
          setCustomRows(r)
          setLayoutId(CUSTOM_ID)
          setDialogOpen(false)
        }}
      />
    </div>
  )
}
