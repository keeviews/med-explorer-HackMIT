import { useEffect, useState } from "react"
import { ClipboardList, Hospital, LoaderCircle } from "lucide-react"

import { InsightBanners } from "@/components/InsightBanners"
import { MedicineScanner } from "@/components/MedicineScanner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { fetchMyChartDemoImport, fetchMyChartStatus, fetchReview } from "@/lib/api"
import { CABINET_LIMIT, type MedicineCabinet } from "@/lib/cabinet"
import { useLanguage } from "@/lib/language"
import {
  ApiError,
  type CompareResponse,
  type FhirImportResponse,
  type MedicineNote,
  type MyChartStatus,
  type UnmappedMedication,
} from "@/lib/types"

type MyMedicinesProps = {
  cabinet: MedicineCabinet
  onMoveToHistory: (id: number) => void
  onRestore: (id: number) => void
  onRemoveHistory: (id: number) => void
  onClearCurrent: () => void
  onClearHistory: () => void
  onAddToCompare: (note: MedicineNote) => void
  onImport: (notes: MedicineNote[], unmapped: UnmappedMedication[]) => void
  onRemoveUnmapped: (name: string) => void
}

export function MyMedicines({
  cabinet,
  onMoveToHistory,
  onRestore,
  onRemoveHistory,
  onClearCurrent,
  onClearHistory,
  onAddToCompare,
  onImport,
  onRemoveUnmapped,
}: MyMedicinesProps) {
  const { copy, simple } = useLanguage()
  const [status, setStatus] = useState<"idle" | "loading" | "ok" | "error" | "short">("idle")
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [review, setReview] = useState<CompareResponse | null>(null)
  const [mychart, setMychart] = useState<MyChartStatus | null>(null)
  const [importing, setImporting] = useState(false)
  const [importNotice, setImportNotice] = useState<string | null>(null)

  const currentIds = cabinet.current.map((item) => item.id).join(",")

  useEffect(() => {
    setStatus("idle")
    setReview(null)
  }, [currentIds])

  useEffect(() => {
    let cancelled = false
    fetchMyChartStatus()
      .then((data) => {
        if (!cancelled) setMychart(data)
      })
      .catch(() => {
        /* demo import still works if this fails later */
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function runReview() {
    if (cabinet.current.length < 2) {
      setStatus("short")
      setReview(null)
      return
    }
    setStatus("loading")
    setErrorMessage(null)
    try {
      const data = await fetchReview(cabinet.current.map((item) => item.id))
      setReview(data)
      setStatus("ok")
    } catch (cause) {
      setReview(null)
      setStatus("error")
      setErrorMessage(cause instanceof ApiError ? cause.message : copy.compareErrorTitle)
    }
  }

  async function runDemoImport() {
    setImporting(true)
    setImportNotice(null)
    try {
      const data: FhirImportResponse = await fetchMyChartDemoImport()
      const now = new Date().toISOString()
      onImport(
        data.mapped.map((row) => ({
          id: row.id,
          name: row.name,
          addedAt: now,
          source: row.source,
          fhir_name: row.fhir_name,
        })),
        data.unmapped,
      )
      setImportNotice(copy.importOk(data.mapped_count, data.unmapped_count))
    } catch (cause) {
      setImportNotice(
        cause instanceof ApiError ? cause.message : copy.compareErrorTitle,
      )
    } finally {
      setImporting(false)
    }
  }

  function sourceLabel(source?: string): string | null {
    if (source === "fhir_demo") return copy.sourceDemo
    if (source === "mychart") return copy.sourceMyChart
    if (source === "label_scan") return "label scan"
    if (source === "manual") return null
    return source ?? null
  }

  function confirmClear(listName: "currently taking" | "past medicines", onConfirm: () => void) {
    if (window.confirm(`Clear all ${listName}? This cannot be undone.`)) {
      onConfirm()
    }
  }

  return (
    <section id="my-medicines" className="scroll-mt-6 space-y-4">
      <div>
        <h2 className="text-2xl">{copy.myTitle}</h2>
        <p className="mt-1 max-w-xl text-sm text-muted-foreground">{copy.myIntro}</p>
      </div>

      <div className="space-y-3 border-b border-border pb-5">
        <div className="flex items-start gap-3">
          <Hospital className="mt-0.5 h-5 w-5 text-primary" aria-hidden="true" />
          <div>
            <h3 className="font-heading text-lg">{copy.connectTitle}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{copy.connectBody}</p>
          </div>
        </div>
        {!simple && mychart?.setup_note ? (
          <p className="text-sm text-muted-foreground">{mychart.setup_note}</p>
        ) : null}
        {simple && mychart && !mychart.authorize_url ? (
          <p className="text-sm text-muted-foreground">{copy.signInNeedsSetup}</p>
        ) : null}
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            disabled={!mychart?.authorize_url}
            onClick={() => {
              if (mychart?.authorize_url) window.location.href = mychart.authorize_url
            }}
          >
            {copy.signInMyChart}
          </Button>
          <Button type="button" variant="secondary" disabled={importing} onClick={() => void runDemoImport()}>
            {importing ? <LoaderCircle className="h-4 w-4 animate-spin" /> : null}
            {copy.loadDemo}
          </Button>
        </div>
        {importNotice ? <p className="text-sm">{importNotice}</p> : null}
      </div>

      <div className="grid border-y border-border md:grid-cols-2">
        <div className="py-4 md:pr-6">
          <div className="flex items-center justify-between gap-2">
            <h3 className="font-heading text-lg">{copy.currentlyTaking}</h3>
            <div className="flex items-center gap-2">
              <Badge variant="outline">
                {cabinet.current.length}/{CABINET_LIMIT}
              </Badge>
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={cabinet.current.length === 0}
                onClick={() => confirmClear("currently taking", onClearCurrent)}
              >
                Clear current list
              </Button>
            </div>
          </div>
          {cabinet.current.length === 0 ? (
            <p className="mt-3 text-sm text-muted-foreground">{copy.takingEmpty}</p>
          ) : (
            <ul className="mt-3 max-h-[32rem] space-y-2 overflow-y-scroll pr-2">
              {cabinet.current.map((item) => (
                <li
                  key={item.id}
                  className="flex flex-wrap items-center justify-between gap-2 border-b border-border/70 py-3 text-sm last:border-b-0"
                >
                  <span>
                    <span className="font-medium">{item.name}</span>
                    {sourceLabel(item.source) ? (
                      <span className="ml-2 text-xs text-muted-foreground">
                        {sourceLabel(item.source)}
                      </span>
                    ) : null}
                  </span>
                  <span className="flex flex-wrap gap-1">
                    <Button type="button" size="sm" variant="ghost" onClick={() => onAddToCompare(item)}>
                      {copy.addCompare}
                    </Button>
                    <Button type="button" size="sm" variant="outline" onClick={() => onMoveToHistory(item.id)}>
                      {copy.movePast}
                    </Button>
                  </span>
                </li>
              ))}
            </ul>
          )}
          {cabinet.unmapped.length > 0 ? (
            <div className="mt-4 border-t border-dashed border-border pt-3">
              <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                {copy.unmappedTitle}
              </p>
              <ul className="mt-2 space-y-2">
                {cabinet.unmapped.map((item) => (
                  <li key={item.name} className="flex items-center justify-between gap-2 text-sm">
                    <span>{item.name}</span>
                    <Button type="button" size="sm" variant="ghost" onClick={() => onRemoveUnmapped(item.name)}>
                      {copy.dismiss}
                    </Button>
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-muted-foreground">{copy.unmappedBody}</p>
            </div>
          ) : null}
          <div className="mt-4">
            <Button type="button" onClick={() => void runReview()} disabled={status === "loading"}>
              {status === "loading" ? (
                <LoaderCircle className="h-4 w-4 animate-spin" />
              ) : (
                <ClipboardList className="h-4 w-4" />
              )}
              {copy.reviewList}
            </Button>
          </div>
        </div>

        <div className="border-t border-border py-4 md:border-t-0 md:border-l md:pl-6">
          <div className="flex items-center justify-between gap-2">
            <h3 className="font-heading text-lg">{copy.pastNotes}</h3>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={cabinet.history.length === 0}
              onClick={() => confirmClear("past medicines", onClearHistory)}
            >
              Clear past list
            </Button>
          </div>
          {cabinet.history.length === 0 ? (
            <p className="mt-3 text-sm text-muted-foreground">{copy.pastEmpty}</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {cabinet.history.map((item) => (
                <li
                  key={`${item.id}-${item.stoppedAt ?? ""}`}
                  className="flex flex-wrap items-center justify-between gap-2 border-b border-border/70 py-3 text-sm last:border-b-0"
                >
                  <span>{item.name}</span>
                  <span className="flex flex-wrap gap-1">
                    <Button type="button" size="sm" variant="ghost" onClick={() => onRestore(item.id)}>
                      {copy.backCurrent}
                    </Button>
                    <Button type="button" size="sm" variant="outline" onClick={() => onRemoveHistory(item.id)}>
                      {copy.removeNote}
                    </Button>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {status === "short" ? (
        <p className="rounded-lg border border-dashed border-border bg-card/70 p-3 text-sm text-muted-foreground">
          {copy.reviewShort}
        </p>
      ) : null}

      {status === "error" ? (
        <p className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm">{errorMessage}</p>
      ) : null}

      {status === "ok" && review ? (
        <div className="space-y-3 border-y border-border py-4">
          <h3 className="font-heading text-lg">{copy.reviewTitle}</h3>
          {!simple && review.overlap_note ? (
            <p className="text-sm text-muted-foreground">{review.overlap_note}</p>
          ) : null}
          {(review.alerts ?? []).length === 0 ? (
            <p className="text-sm">{copy.reviewNone}</p>
          ) : (
            <InsightBanners
              alerts={review.alerts}
              overlapSummary={review.overlap_summary}
              talkWithClinician={review.talk_with_clinician}
            />
          )}
        </div>
      ) : null}

      <MedicineScanner
        disabled={cabinet.current.length >= CABINET_LIMIT}
        onAdd={(candidates) =>
          onImport(
            candidates.map((candidate) => ({
              id: candidate.id,
              name: candidate.name,
              addedAt: new Date().toISOString(),
              source: "label_scan",
            })),
            [],
          )
        }
      />
    </section>
  )
}
