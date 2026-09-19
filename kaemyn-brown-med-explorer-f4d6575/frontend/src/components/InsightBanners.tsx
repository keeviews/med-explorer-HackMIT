import { simpleAlertDetail, simpleAlertTitle } from "@/lib/copy"
import { useLanguage } from "@/lib/language"
import { cn } from "@/lib/utils"
import type { CombinationAlert, Similarity } from "@/lib/types"

type InsightBannersProps = {
  alerts: CombinationAlert[]
  overlapSummary: string | null
  talkWithClinician: string
}

export function InsightBanners({
  alerts,
  overlapSummary,
  talkWithClinician,
}: InsightBannersProps) {
  const { copy, simple } = useLanguage()
  if (alerts.length === 0) return null
  return (
    <div className="space-y-3">
      {!simple && overlapSummary ? (
        <p className="text-sm font-medium text-foreground">{overlapSummary}</p>
      ) : null}
      {alerts.map((alert) => (
        <div
          key={`${alert.code}-${alert.drug_ids.join("-")}`}
          className={
            alert.severity === "urgent_seed"
              ? "rounded-lg border border-red-300 bg-red-50 p-4 text-red-950"
              : "rounded-lg border border-amber-300 bg-amber-50 p-4 text-amber-950"
          }
          role="status"
        >
          <p className="text-xs font-semibold tracking-wide uppercase">
            {alert.severity === "urgent_seed" ? copy.alertUrgent : copy.alertDiscuss}
          </p>
          <h3 className="mt-1 font-heading text-lg">
            {simple ? simpleAlertTitle(alert) : alert.title}
          </h3>
          <p className="mt-1 text-sm leading-relaxed">
            {simple ? simpleAlertDetail(alert) : alert.detail}
          </p>
          {simple ? (
            <p className="mt-2 text-sm font-medium">{copy.alertAsk}</p>
          ) : (
            <p className="mt-2 text-sm font-medium">{alert.talk_with_clinician}</p>
          )}
          <p className="mt-1 text-xs opacity-80">{alert.drug_names.join(" · ")}</p>
        </div>
      ))}
      {simple ? null : <p className="text-sm text-muted-foreground">{talkWithClinician}</p>}
    </div>
  )
}

export function HighlightLegend() {
  const { copy } = useLanguage()
  return (
    <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
      <span className="inline-flex items-center gap-1.5">
        <span className="h-3 w-3 rounded-sm bg-emerald-200 ring-1 ring-emerald-400" />
        {copy.legendSame}
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="h-3 w-3 rounded-sm bg-red-200 ring-1 ring-red-400" />
        {copy.legendAsk}
      </span>
    </div>
  )
}

export function cellHighlightClass(
  field: string,
  drugId: number,
  similarities: Similarity[],
  alerts: CombinationAlert[],
): string | undefined {
  const urgent = alerts.some(
    (alert) =>
      alert.severity === "urgent_seed" &&
      alert.drug_ids.includes(drugId) &&
      (alert.fields.length === 0 || alert.fields.includes(field)),
  )
  if (urgent) return "bg-red-100 text-red-950"
  const discuss = alerts.some(
    (alert) =>
      alert.severity === "discuss" &&
      alert.drug_ids.includes(drugId) &&
      (alert.fields.length === 0 || alert.fields.includes(field)),
  )
  if (discuss) return "bg-amber-100 text-amber-950"
  const similar = similarities.some((row) => row.field === field && row.drug_ids.includes(drugId))
  if (similar) return "bg-emerald-100 text-emerald-950"
  return undefined
}

export function highlightNote(className: string | undefined): string | undefined {
  if (!className) return undefined
  if (className.includes("bg-red-100")) return "Ask first"
  if (className.includes("bg-amber-100")) return "Ask about this"
  if (className.includes("bg-emerald-100")) return "Same"
  return undefined
}

export function highlightedCell(className: string | undefined): string {
  return cn("px-4 py-3 align-top leading-relaxed", className)
}
