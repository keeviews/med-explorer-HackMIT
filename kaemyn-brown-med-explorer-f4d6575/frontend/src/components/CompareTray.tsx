import { Columns2, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useLanguage } from "@/lib/language"
import type { ComparePick } from "@/lib/types"

type CompareTrayProps = {
  picks: ComparePick[]
  compareOpen: boolean
  onRemove: (id: number) => void
  onClear: () => void
  onToggleCompare: () => void
}

export function CompareTray({
  picks,
  compareOpen,
  onRemove,
  onClear,
  onToggleCompare,
}: CompareTrayProps) {
  const { copy } = useLanguage()
  if (picks.length === 0) return null
  const ready = picks.length >= 2
  return (
    <div className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card/95 shadow-[0_-8px_30px_rgba(28,43,36,0.08)] backdrop-blur">
      <div className="mx-auto flex max-w-5xl flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div className="min-w-0">
          <p className="text-sm font-semibold">{copy.trayLabel(picks.length)}</p>
          <p className="text-xs text-muted-foreground">{copy.trayHint}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {picks.map((pick) => (
              <span
                key={pick.id}
                className="inline-flex items-center gap-1 rounded-full bg-secondary px-2.5 py-1 text-xs font-medium text-secondary-foreground"
              >
                {pick.name}
                <button
                  type="button"
                  className="rounded-full p-0.5 hover:bg-background/60"
                  onClick={() => onRemove(pick.id)}
                  aria-label={`${copy.removeCompare} ${pick.name}`}
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Button type="button" variant="ghost" size="sm" onClick={onClear}>
            {copy.clear}
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={onToggleCompare}
            disabled={!ready && !compareOpen}
          >
            <Columns2 className="h-4 w-4" />
            {compareOpen ? copy.hideCompare : copy.showCompare}
          </Button>
        </div>
      </div>
    </div>
  )
}
