import { Columns2, Minus, Plus } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { plainSeedNote, shortCondition } from "@/lib/copy"
import { useLanguage } from "@/lib/language"
import type { Suggestion } from "@/lib/types"

type ResultCardProps = {
  suggestion: Suggestion
  inCompare: boolean
  compareFull: boolean
  onToggleCompare: () => void
  taking: boolean
  takingFull: boolean
  onToggleTaking: () => void
}

export function ResultCard({
  suggestion,
  inCompare,
  compareFull,
  onToggleCompare,
  taking,
  takingFull,
  onToggleTaking,
}: ResultCardProps) {
  const { copy, simple } = useLanguage()
  const addDisabled = compareFull && !inCompare
  const takingDisabled = takingFull && !taking
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3 pb-2">
        <div>
          <CardTitle>{suggestion.drug_name}</CardTitle>
          {!simple && suggestion.rxnorm_id ? (
            <p className="mt-1 font-mono text-xs text-muted-foreground">
              RxNorm {suggestion.rxnorm_id}
            </p>
          ) : null}
        </div>
        {simple ? null : <Badge variant="warning">{copy.sampleBadge}</Badge>}
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            {copy.indication}
          </p>
          <p className="mt-1 text-sm leading-relaxed">
            {simple && suggestion.matched_condition
              ? shortCondition(suggestion.matched_condition, true)
              : plainSeedNote(suggestion.indication_snippet, simple)}
          </p>
        </div>
        {!simple && suggestion.matched_condition ? (
          <Badge variant="secondary">{suggestion.matched_condition}</Badge>
        ) : null}
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant={inCompare ? "outline" : "secondary"}
            onClick={onToggleCompare}
            disabled={addDisabled}
            aria-pressed={inCompare}
          >
            {inCompare ? (
              <Minus className="h-4 w-4" />
            ) : addDisabled ? (
              <Columns2 className="h-4 w-4" />
            ) : (
              <Plus className="h-4 w-4" />
            )}
            {inCompare ? copy.removeCompare : addDisabled ? copy.compareFull : copy.addCompare}
          </Button>
          <Button
            type="button"
            variant={taking ? "outline" : "ghost"}
            onClick={onToggleTaking}
            disabled={takingDisabled}
            aria-pressed={taking}
          >
            {taking ? copy.onMyList : copy.takingThis}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}