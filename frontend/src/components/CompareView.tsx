import { useEffect, useState } from "react"
import { LoaderCircle, X } from "lucide-react"

import {
  HighlightLegend,
  InsightBanners,
  cellHighlightClass,
  highlightNote,
  highlightedCell,
} from "@/components/InsightBanners"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { fetchCompare } from "@/lib/api"
import { plainSeedNote, shortCondition } from "@/lib/copy"
import { useLanguage } from "@/lib/language"
import { ApiError, type CompareResponse, type DrugDetail } from "@/lib/types"

type CompareViewProps = {
  ids: number[]
  onRemove: (id: number) => void
  onSaveCurrent?: (id: number, name: string) => void
  currentIds?: Set<number>
  takingFull?: boolean
}

type RowKey = keyof DrugDetail | "side_effects"
type RowLabel = "rowClass" | "rowRoute" | "rowRx" | "rowUse" | "rowEffects" | "rowAsk" | "rowFor"

const ROW_KEYS: { key: RowKey; label: RowLabel }[] = [
  { key: "drug_class", label: "rowClass" },
  { key: "route", label: "rowRoute" },
  { key: "rx_otc", label: "rowRx" },
  { key: "typical_use_note", label: "rowUse" },
  { key: "side_effects", label: "rowEffects" },
  { key: "monitoring_note", label: "rowAsk" },
  { key: "linked_conditions", label: "rowFor" },
]

function cellValue(drug: DrugDetail, key: RowKey, notListed: string, simple: boolean): string {
  if (key === "side_effects") {
    return drug.common_side_effects.length > 0 ? drug.common_side_effects.join(" · ") : notListed
  }
  if (key === "linked_conditions") {
    if (drug.linked_conditions.length === 0) return notListed
    return drug.linked_conditions.map((name) => shortCondition(name, simple)).join(" · ")
  }
  const value = drug[key]
  if (Array.isArray(value)) {
    return value.length > 0 ? value.join(" · ") : notListed
  }
  if (typeof value === "string" && value.trim()) {
    if (key === "rx_otc" && simple) {
      if (value === "Rx") return "Prescription"
      if (value === "OTC") return "Store-bought"
      if (value.startsWith("OTC or Rx")) return "Store-bought or prescription (depends on the product)"
    }
    if (key === "route" && simple && value === "oral") return "By mouth"
    return plainSeedNote(value, simple)
  }
  if (typeof value === "number") return String(value)
  return notListed
}

export function CompareView({ ids, onRemove, onSaveCurrent, currentIds, takingFull }: CompareViewProps) {
  const { copy, simple } = useLanguage()
  const [status, setStatus] = useState<"empty" | "loading" | "ok" | "error">(
    ids.length < 2 ? "empty" : "loading",
  )
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [payload, setPayload] = useState<CompareResponse | null>(null)

  useEffect(() => {
    if (ids.length < 2) {
      setStatus("empty")
      setPayload(null)
      return
    }
    let cancelled = false
    setStatus("loading")
    fetchCompare(ids)
      .then((data) => {
        if (cancelled) return
        setPayload(data)
        setStatus("ok")
      })
      .catch((cause: unknown) => {
        if (cancelled) return
        setPayload(null)
        setStatus("error")
        setErrorMessage(
          cause instanceof ApiError ? cause.message : copy.compareErrorTitle,
        )
      })
    return () => {
      cancelled = true
    }
  }, [ids, copy.compareErrorTitle])

  return (
    <section id="compare-panel" className="scroll-mt-6 space-y-4">
      <div>
        <h2 className="text-2xl">{copy.compareTitle}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{copy.compareIntro}</p>
      </div>

      {status === "empty" ? (
        <div className="rounded-xl border border-dashed border-border bg-card/50 p-5">
          <h3 className="font-heading text-xl">{copy.compareEmptyTitle}</h3>
          <p className="mt-1 max-w-xl text-sm text-muted-foreground">{copy.compareEmptyBody}</p>
        </div>
      ) : null}

      {status === "loading" ? (
        <div className="flex items-center gap-2 text-muted-foreground">
          <LoaderCircle className="h-4 w-4 animate-spin" />
          {copy.compareLoading}
        </div>
      ) : null}

      {status === "error" ? (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-5">
          <h3 className="font-heading text-xl">{copy.compareErrorTitle}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{errorMessage}</p>
        </div>
      ) : null}

      {status === "ok" && payload ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="warning">{copy.sampleBadge}</Badge>
            <Badge variant="outline">{copy.medicinesCount(payload.result_count)}</Badge>
          </div>
          {!simple ? (
            <p className="rounded-lg border border-border bg-card/70 p-3 text-sm leading-relaxed text-muted-foreground">
              {payload.compare_note} {payload.overlap_note}
            </p>
          ) : null}
          <HighlightLegend />
          <InsightBanners
            alerts={payload.alerts ?? []}
            overlapSummary={payload.overlap_summary}
            talkWithClinician={payload.talk_with_clinician}
          />

          <div className="hidden overflow-x-auto rounded-xl border border-border bg-card md:block">
            <table className="w-full min-w-[40rem] border-collapse text-sm">
              <thead>
                <tr className="border-b border-border bg-secondary/60">
                  <th className="sticky left-0 bg-secondary/60 px-4 py-3 text-left font-semibold">
                    {copy.topic}
                  </th>
                  {payload.drugs.map((drug) => (
                    <th key={drug.id} className="px-4 py-3 text-left align-bottom">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="font-heading text-lg leading-tight">{drug.drug_name}</p>
                          {!simple && drug.rxnorm_id ? (
                            <p className="mt-1 font-mono text-xs font-normal text-muted-foreground">
                              RxNorm {drug.rxnorm_id}
                            </p>
                          ) : null}
                          {onSaveCurrent ? (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="mt-2 h-8 px-2"
                              disabled={currentIds?.has(drug.id) || (takingFull && !currentIds?.has(drug.id))}
                              onClick={() => onSaveCurrent(drug.id, drug.drug_name)}
                            >
                              {currentIds?.has(drug.id) ? copy.onCurrent : copy.takingThis}
                            </Button>
                          ) : null}
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => onRemove(drug.id)}
                          aria-label={`${copy.removeCompare} ${drug.drug_name}`}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ROW_KEYS.map((row) => (
                  <tr key={row.key} className="border-b border-border last:border-0">
                    <th className="sticky left-0 bg-card px-4 py-3 text-left align-top text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                      {copy[row.label]}
                    </th>
                    {payload.drugs.map((drug) => {
                      const tone = cellHighlightClass(
                        row.key,
                        drug.id,
                        payload.similarities ?? [],
                        payload.alerts ?? [],
                      )
                      return (
                        <td
                          key={drug.id}
                          className={highlightedCell(tone)}
                          title={highlightNote(tone)}
                        >
                          {cellValue(drug, row.key, copy.notListed, simple)}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid gap-4 md:hidden">
            {payload.drugs.map((drug) => (
              <Card
                key={drug.id}
                className={
                  (payload.alerts ?? []).some(
                    (alert) => alert.severity === "urgent_seed" && alert.drug_ids.includes(drug.id),
                  )
                    ? "ring-1 ring-red-300"
                    : undefined
                }
              >
                <CardHeader className="flex flex-row items-start justify-between gap-2">
                  <CardTitle>{drug.drug_name}</CardTitle>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => onRemove(drug.id)}
                    aria-label={`${copy.removeCompare} ${drug.drug_name}`}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </CardHeader>
                <CardContent className="space-y-3">
                  {ROW_KEYS.map((row) => {
                    const tone = cellHighlightClass(
                      row.key,
                      drug.id,
                      payload.similarities ?? [],
                      payload.alerts ?? [],
                    )
                    return (
                      <div key={row.key} className={tone ? `rounded-md px-2 py-1 ${tone}` : undefined}>
                        <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                          {copy[row.label]}
                        </p>
                        <p className="mt-1 text-sm leading-relaxed">
                          {cellValue(drug, row.key, copy.notListed, simple)}
                        </p>
                      </div>
                    )
                  })}
                  {onSaveCurrent ? (
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      disabled={currentIds?.has(drug.id) || (takingFull && !currentIds?.has(drug.id))}
                      onClick={() => onSaveCurrent(drug.id, drug.drug_name)}
                    >
                      {currentIds?.has(drug.id) ? copy.onCurrent : copy.takingThis}
                    </Button>
                  ) : null}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  )
}
