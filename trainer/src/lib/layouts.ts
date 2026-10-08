export type Rows = [string, string, string]

export type LayoutDef = {
  id: string
  name: string
  description: string
  rows: Rows
}

export const PRESETS: LayoutDef[] = [
  {
    id: 'v2',
    name: 'Slide v2',
    description: 'Whole-board optimised: slides rewarded, all other same-finger pairs penalised.',
    rows: ["'WB,/Z.CFP", 'SIEOAHNTRL', 'JGXUKQDVMY'],
  },
  {
    id: 'v1',
    name: 'Slide v1',
    description: 'Greedy downward digraphs. More slides, more upward and index-finger pairs.',
    rows: ["KCMV.'P,UW", 'IOAETSLNRH', 'GFBXZQYDJ/'],
  },
  {
    id: 'qwerty',
    name: 'QWERTY',
    description: 'Baseline, so you can compare your transition timings.',
    rows: ['QWERTYUIOP', 'ASDFGHJKL;', 'ZXCVBNM,./'],
  },
]

export const CUSTOM_ID = 'custom'

/** Physical key codes of the 30 core keys, in QWERTY order (what a stock Totem sends). */
const KEY_CODES = [
  'KeyQ KeyW KeyE KeyR KeyT KeyY KeyU KeyI KeyO KeyP',
  'KeyA KeyS KeyD KeyF KeyG KeyH KeyJ KeyK KeyL Semicolon',
  'KeyZ KeyX KeyC KeyV KeyB KeyN KeyM Comma Period Slash',
]
const CODE_GRID = KEY_CODES.map((r) => r.split(' '))

/** Board columns left to right -> physical finger. The inner columns share the index finger. */
export const COL_FINGER = [0, 1, 2, 3, 3, 6, 6, 7, 8, 9]
export const FINGER_NAMES = ['pinky', 'ring', 'middle', 'index', 'inner']

export type Pos = { row: number; col: number }

export type Compiled = {
  rows: Rows
  codeToChar: Map<string, string>
  charToPos: Map<string, Pos>
}

export function compile(rows: Rows): Compiled {
  const codeToChar = new Map<string, string>()
  const charToPos = new Map<string, Pos>()
  rows.forEach((row, r) =>
    [...row].forEach((ch, c) => {
      const lower = ch.toLowerCase()
      codeToChar.set(CODE_GRID[r][c], lower)
      charToPos.set(lower, { row: r, col: c })
    }),
  )
  return { rows, codeToChar, charToPos }
}

export type Transition = 'slide' | 'sfb' | 'roll' | 'alternate'

export const TRANSITION_LABELS: Record<Transition, string> = {
  slide: 'Downward slides',
  sfb: 'Other same-finger',
  roll: 'Same hand, other finger',
  alternate: 'Hand switches',
}

export function classify(layout: Compiled, a: string, b: string): Transition | null {
  const p = layout.charToPos.get(a.toLowerCase())
  const q = layout.charToPos.get(b.toLowerCase())
  if (!p || !q || a === b) return null
  const handP = p.col < 5 ? 0 : 1
  const handQ = q.col < 5 ? 0 : 1
  if (handP !== handQ) return 'alternate'
  if (COL_FINGER[p.col] !== COL_FINGER[q.col]) return 'roll'
  if (p.col === q.col && q.row === p.row + 1) return 'slide'
  return 'sfb'
}

/** Slide digraphs of a layout: top->home and home->bottom on each column. */
export function slideDigraphs(rows: Rows): string[] {
  const out: string[] = []
  for (let c = 0; c < 10; c++) {
    const [t, h, b] = [rows[0][c], rows[1][c], rows[2][c]].map((x) => x.toLowerCase())
    out.push(t + h, h + b)
  }
  return out
}

export type ParseResult = { ok: true; rows: Rows } | { ok: false; error: string }

export function parseLayout(text: string): ParseResult {
  const lines = text
    .split('\n')
    .map((l) => l.replace(/\s+/g, ''))
    .filter(Boolean)
  if (lines.length !== 3) return { ok: false, error: 'Enter exactly 3 rows (top, home, bottom).' }
  for (const [i, l] of lines.entries()) {
    if ([...l].length !== 10)
      return { ok: false, error: `Row ${i + 1} has ${[...l].length} keys; each row needs 10.` }
  }
  const all = lines.join('').toLowerCase()
  const seen = new Set<string>()
  for (const ch of all) {
    if (seen.has(ch)) return { ok: false, error: `"${ch}" appears more than once.` }
    seen.add(ch)
  }
  const missing = [...'abcdefghijklmnopqrstuvwxyz'].filter((c) => !seen.has(c))
  if (missing.length) return { ok: false, error: `Missing letters: ${missing.join(' ')}` }
  return { ok: true, rows: lines.map((l) => l.toUpperCase()) as Rows }
}

export function formatRows(rows: Rows): string {
  return rows.map((r) => `${[...r.slice(0, 5)].join(' ')}   ${[...r.slice(5)].join(' ')}`).join('\n')
}
