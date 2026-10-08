import { WORDS } from '@/data/words'
import { slideDigraphs, type Compiled } from '@/lib/layouts'

export type WordSource = 'top200' | 'top1k' | 'slides'

export const WORD_SOURCE_LABELS: Record<WordSource, string> = {
  top200: 'top 200',
  top1k: 'top 1k',
  slides: 'slide drill',
}

const CONTRACTIONS = ["it's", "don't", "that's", "can't", "he's", "didn't", "there's", "isn't", "won't", "world's", "people's", "i'm"]

function pick<T>(xs: T[]): T {
  return xs[Math.floor(Math.random() * xs.length)]
}

export function slideWords(layout: Compiled): string[] {
  const slides = new Set(slideDigraphs(layout.rows))
  return WORDS.filter((w) => {
    for (let i = 0; i + 1 < w.length; i++) if (slides.has(w.slice(i, i + 2))) return true
    return false
  })
}

export function generateWords(
  count: number,
  source: WordSource,
  layout: Compiled,
  punctuation: boolean,
): string[] {
  const typeable = (w: string) => [...w].every((ch) => layout.charToPos.has(ch))
  let pool = source === 'top200' ? WORDS.slice(0, 200) : source === 'top1k' ? WORDS : slideWords(layout)
  pool = pool.filter(typeable)
  if (pool.length === 0) pool = WORDS.slice(0, 200).filter(typeable)
  const contractions = CONTRACTIONS.filter(typeable)
  const hasComma = layout.charToPos.has(',')
  const hasPeriod = layout.charToPos.has('.')

  const out: string[] = []
  let prev = ''
  while (out.length < count) {
    let w = punctuation && contractions.length && Math.random() < 0.07 ? pick(contractions) : pick(pool)
    if (w === prev) continue
    prev = w
    if (punctuation) {
      const r = Math.random()
      if (hasComma && r < 0.1) w += ','
      else if (hasPeriod && r < 0.17) w += '.'
    }
    out.push(w)
  }
  return out
}
