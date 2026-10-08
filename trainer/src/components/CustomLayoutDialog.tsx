import { useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { formatRows, parseLayout, type Rows } from '@/lib/layouts'

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  initial: Rows
  onSave: (rows: Rows) => void
}

export function CustomLayoutDialog({ open, onOpenChange, initial, onSave }: Props) {
  const [text, setText] = useState(() => formatRows(initial))
  const parsed = parseLayout(text)

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (o) setText(formatRows(initial))
        onOpenChange(o)
      }}
    >
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Custom layout</DialogTitle>
          <DialogDescription>
            Three rows of ten keys: top, home, bottom, left to right. Spaces are ignored, so you can
            paste the output of <code className="font-mono text-xs">totem_layout_v2.py</code> as-is.
          </DialogDescription>
        </DialogHeader>
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          spellCheck={false}
          rows={4}
          className="font-mono text-lg tracking-wider"
          aria-invalid={!parsed.ok}
        />
        <p className={parsed.ok ? 'text-sm text-emerald-400' : 'text-sm text-rose-400'}>
          {parsed.ok ? 'Looks good: 30 unique keys, all 26 letters.' : parsed.error}
        </p>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!parsed.ok}
            onClick={() => {
              if (parsed.ok) onSave(parsed.rows)
            }}
          >
            Use this layout
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
