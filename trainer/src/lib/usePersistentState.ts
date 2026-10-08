import { useCallback, useState, type SetStateAction } from 'react'

const PREFIX = 'slide-trainer:'

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(PREFIX + key)
    return raw === null ? fallback : (JSON.parse(raw) as T)
  } catch {
    return fallback
  }
}

/** useState backed by localStorage. Switching `key` reads that key's stored value. */
export function usePersistentState<T>(key: string, fallback: T) {
  const [state, setState] = useState<{ key: string; value: T }>(() => ({ key, value: read(key, fallback) }))
  const value = state.key === key ? state.value : read(key, fallback)

  const set = useCallback(
    (action: SetStateAction<T>) => {
      setState((prev) => {
        const base = prev.key === key ? prev.value : read(key, fallback)
        const next = typeof action === 'function' ? (action as (p: T) => T)(base) : action
        try {
          localStorage.setItem(PREFIX + key, JSON.stringify(next))
        } catch {
          /* storage full or disabled: keep in memory only */
        }
        return { key, value: next }
      })
    },
    [key, fallback],
  )

  return [value, set] as const
}
