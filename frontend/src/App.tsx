import { useEffect, useMemo, useState, type FormEvent } from "react"
import { LoaderCircle, Search } from "lucide-react"

import { CompareTray } from "@/components/CompareTray"
import { CompareView } from "@/components/CompareView"
import { DisclaimerBanner } from "@/components/DisclaimerBanner"
import { LanguageToggle } from "@/components/LanguageToggle"
import { MyMedicines } from "@/components/MyMedicines"
import { ResultCard } from "@/components/ResultCard"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { fetchSeededConditions, fetchSuggestions } from "@/lib/api"
import {
  addCurrent,
  CABINET_LIMIT,
  isCurrent,
  loadCabinet,
  mergeImport,
  moveToHistory,
  removeHistory,
  removeUnmapped,
  restoreCurrent,
  saveCabinet,
} from "@/lib/cabinet"
import { COMPARE_LIMIT, loadComparePicks, saveComparePicks } from "@/lib/compare"
import { shortCondition } from "@/lib/copy"
import { useLanguage } from "@/lib/language"
import { ApiError, type ComparePick, type ConditionSummary, type MedicineNote, type SuggestResponse } from "@/lib/types"

const FALLBACK_CHIPS = [
  "Hypertension",
  "Type 2 diabetes mellitus",
  "Seasonal allergic rhinitis",
  "Gastroesophageal reflux disease",
  "Migraine",
]

type Status = "idle" | "loading" | "ok" | "empty" | "error"

export default function App() {
  const { copy, simple } = useLanguage()
  const [query, setQuery] = useState("")
  const [status, setStatus] = useState<Status>("idle")
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [payload, setPayload] = useState<SuggestResponse | null>(null)
  const [conditions, setConditions] = useState<ConditionSummary[]>([])
  const [picks, setPicks] = useState<ComparePick[]>(() => loadComparePicks())
  const [compareOpen, setCompareOpen] = useState(false)
  const [cabinet, setCabinet] = useState(() => loadCabinet())

  useEffect(() => {
    let cancelled = false
    fetchSeededConditions()
      .then((data) => {
        if (!cancelled) setConditions(data.conditions)
      })
      .catch(() => {
        /* chips still work from the local fallback list */
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    saveComparePicks(picks)
    if (picks.length === 0) setCompareOpen(false)
  }, [picks])

  useEffect(() => {
    saveCabinet(cabinet)
  }, [cabinet])

  const chips = useMemo(() => {
    const names = conditions.length > 0 ? conditions.map((row) => row.name) : FALLBACK_CHIPS
    return names.map((name) => ({ name, label: shortCondition(name, simple) }))
  }, [conditions, simple])

  const compareIds = useMemo(() => picks.map((pick) => pick.id), [picks])
  const selectedIds = useMemo(() => new Set(compareIds), [compareIds])
  const compareFull = picks.length >= COMPARE_LIMIT
  const takingIds = useMemo(() => new Set(cabinet.current.map((item) => item.id)), [cabinet])
  const takingFull = cabinet.current.length >= CABINET_LIMIT

  async function runSearch(nextQuery: string) {
    const trimmed = nextQuery.trim()
    if (trimmed.length < 2) {
      setStatus("error")
      setErrorMessage(copy.searchTooShort)
      setPayload(null)
      return
    }
    setQuery(trimmed)
    setStatus("loading")
    setErrorMessage(null)
    try {
      const data = await fetchSuggestions(trimmed)
      setPayload(data)
      setStatus(data.result_count === 0 ? "empty" : "ok")
    } catch (cause) {
      setPayload(null)
      setStatus("error")
      setErrorMessage(!simple && cause instanceof ApiError ? cause.message : copy.searchFail)
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void runSearch(query)
  }

  function togglePick(pick: ComparePick) {
    setPicks((current) => {
      if (current.some((item) => item.id === pick.id)) {
        return current.filter((item) => item.id !== pick.id)
      }
      if (current.length >= COMPARE_LIMIT) return current
      return [...current, pick]
    })
  }

  function toggleTaking(note: MedicineNote) {
    setCabinet((current) =>
      isCurrent(current, note.id) ? moveToHistory(current, note.id) : addCurrent(current, note),
    )
  }

  function openCompare() {
    setCompareOpen(true)
    window.requestAnimationFrame(() => {
      document.getElementById("compare-panel")?.scrollIntoView({ behavior: "smooth", block: "start" })
    })
  }

  return (
    <div className={picks.length > 0 ? "min-h-svh pb-28" : "min-h-svh"}>
      <DisclaimerBanner text={copy.disclaimer} />
      <header className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm font-semibold tracking-[0.16em] text-primary uppercase">
            DiscussMeds
          </p>
          <LanguageToggle />
        </div>
        <h1 className="mt-4 max-w-2xl text-3xl leading-tight text-foreground sm:text-4xl">
          {copy.headline}
        </h1>
        <p className="mt-2 max-w-xl text-base text-muted-foreground">{copy.intro}</p>
        <div className="mt-5">
          <Button
            type="button"
            variant="secondary"
            onClick={() =>
              document.getElementById("my-medicines")?.scrollIntoView({ behavior: "smooth" })
            }
          >
            {copy.myMedicines} ({cabinet.current.length})
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 pb-16 sm:px-6">
        <form onSubmit={onSubmit} className="flex flex-col gap-3 sm:flex-row">
          <label className="sr-only" htmlFor="condition-query">
            {copy.searchLabel}
          </label>
          <Input
            id="condition-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={copy.searchPlaceholder}
            autoComplete="off"
          />
          <Button type="submit" size="lg" disabled={status === "loading"}>
            {status === "loading" ? (
              <LoaderCircle className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
            {copy.search}
          </Button>
        </form>

        <div className="mt-4 flex flex-wrap gap-2">
          {chips.map((chip) => (
            <Button
              key={chip.name}
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => void runSearch(chip.name)}
            >
              {chip.label}
            </Button>
          ))}
        </div>

        <section className="mt-8" aria-live="polite">
          {status === "idle" ? <EmptyPanel title={copy.idleTitle} body={copy.idleBody} /> : null}

          {status === "loading" ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <LoaderCircle className="h-4 w-4 animate-spin" />
              {copy.loading}
            </div>
          ) : null}

          {status === "error" ? (
            <EmptyPanel title={copy.errorTitle} body={errorMessage ?? copy.searchFail} tone="error" />
          ) : null}

          {status === "empty" && payload ? (
            <EmptyPanel title={copy.emptyTitle(payload.query)} body={copy.emptyBody} />
          ) : null}

          {status === "ok" && payload ? (
            <div className="space-y-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2 className="text-2xl">{copy.resultsTitle}</h2>
                  <p className="text-sm text-muted-foreground">
                    {copy.resultsCount(payload.result_count, payload.query)}
                  </p>
                </div>
                <Badge variant="warning">{copy.sampleBadge}</Badge>
              </div>
              {!simple && payload.data_notice ? (
                <p className="rounded-lg border border-border bg-card/70 p-3 text-sm leading-relaxed text-muted-foreground">
                  {payload.data_notice}
                </p>
              ) : null}
              <div className="grid gap-3">
                {payload.results.map((suggestion) => (
                  <ResultCard
                    key={suggestion.id}
                    suggestion={suggestion}
                    inCompare={selectedIds.has(suggestion.id)}
                    compareFull={compareFull}
                    onToggleCompare={() =>
                      togglePick({ id: suggestion.id, name: suggestion.drug_name })
                    }
                    taking={takingIds.has(suggestion.id)}
                    takingFull={takingFull}
                    onToggleTaking={() =>
                      toggleTaking({
                        id: suggestion.id,
                        name: suggestion.drug_name,
                        addedAt: new Date().toISOString(),
                      })
                    }
                  />
                ))}
              </div>
            </div>
          ) : null}
        </section>

        {compareOpen ? (
          <div className="mt-10">
            <CompareView
              ids={compareIds}
              onRemove={(id) => togglePick({ id, name: "" })}
              currentIds={takingIds}
              takingFull={takingFull}
              onSaveCurrent={(id, name) =>
                toggleTaking({ id, name, addedAt: new Date().toISOString() })
              }
            />
          </div>
        ) : null}

        <div className="mt-12">
          <MyMedicines
            cabinet={cabinet}
            onMoveToHistory={(id) => setCabinet((current) => moveToHistory(current, id))}
            onRestore={(id) => setCabinet((current) => restoreCurrent(current, id))}
            onRemoveHistory={(id) => setCabinet((current) => removeHistory(current, id))}
            onAddToCompare={(note) => togglePick({ id: note.id, name: note.name })}
            onImport={(notes, unmapped) =>
              setCabinet((current) => mergeImport(current, notes, unmapped))
            }
            onRemoveUnmapped={(name) =>
              setCabinet((current) => removeUnmapped(current, name))
            }
          />
        </div>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto max-w-5xl px-4 py-5 text-sm text-muted-foreground sm:px-6">
          {copy.footer}
        </div>
      </footer>

      <CompareTray
        picks={picks}
        compareOpen={compareOpen}
        onRemove={(id) => togglePick({ id, name: "" })}
        onClear={() => setPicks([])}
        onToggleCompare={() => {
          if (compareOpen) setCompareOpen(false)
          else openCompare()
        }}
      />
    </div>
  )
}

function EmptyPanel({
  title,
  body,
  tone = "neutral",
}: {
  title: string
  body: string
  tone?: "neutral" | "error"
}) {
  return (
    <div
      className={
        tone === "error"
          ? "rounded-xl border border-destructive/30 bg-destructive/5 p-5"
          : "rounded-xl border border-dashed border-border bg-card/50 p-5"
      }
    >
      <h2 className="font-heading text-xl">{title}</h2>
      <p className="mt-1 max-w-xl text-sm text-muted-foreground">{body}</p>
    </div>
  )
}
