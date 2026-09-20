import { useEffect, useRef, useState, type FormEvent } from "react"
import { createPortal } from "react-dom"
import { LoaderCircle, LocateFixed, MapPin, Navigation, Phone, Search, X } from "lucide-react"

import { NearbyMap } from "@/components/NearbyMap"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  availabilityNote,
  directionsUrl,
  fetchGeocode,
  fetchNearby,
  fetchRxOtc,
  milesLabel,
  NearbyError,
  RADII,
  telHref,
  type NearbyResponse,
  type Radius,
  type Spot,
} from "@/lib/nearby"
import { cn } from "@/lib/utils"

type FindNearbyButtonProps = {
  drugId: number
  drugName: string
  variant?: "secondary" | "ghost" | "outline"
  size?: "sm" | "default"
}

/** A "Find nearby" button that opens a pharmacy map for one medicine. */
export function FindNearbyButton({ drugId, drugName, variant = "secondary", size = "default" }: FindNearbyButtonProps) {
  const [open, setOpen] = useState(false)
  const opener = useRef<HTMLElement | null>(null)

  function openDialog() {
    opener.current = document.activeElement as HTMLElement | null
    setOpen(true)
  }

  function closeDialog() {
    setOpen(false)
    window.requestAnimationFrame(() => opener.current?.focus())
  }

  return (
    <>
      <Button type="button" variant={variant} size={size} onClick={openDialog}>
        <MapPin className="h-4 w-4" />
        Find nearby
      </Button>
      {/* Shown at the top level of the page, not inside the card or its live-region, so screen readers and
          stacking behave. */}
      {open
        ? createPortal(<NearbyDialog drugId={drugId} drugName={drugName} onClose={closeDialog} />, document.body)
        : null}
    </>
  )
}

type Status = "idle" | "locating" | "loading" | "ok" | "error"

function shortPlace(label: string): string {
  return label.split(",").slice(0, 3).join(",").trim()
}

function NearbyDialog({ drugId, drugName, onClose }: { drugId: number; drugName: string; onClose: () => void }) {
  const [spot, setSpot] = useState<Spot | null>(null)
  const [miles, setMiles] = useState<Radius>(10)
  const [status, setStatus] = useState<Status>("idle")
  const [message, setMessage] = useState<string | null>(null)
  const [data, setData] = useState<NearbyResponse | null>(null)
  const [rxOtc, setRxOtc] = useState<string | null>(null)
  const [query, setQuery] = useState("")
  const [selected, setSelected] = useState<string | null>(null)
  const panel = useRef<HTMLDivElement>(null)
  const closeButton = useRef<HTMLButtonElement>(null)
  const busy = status === "locating" || status === "loading"

  // Say whether the medicine is over the counter, prescription, or both.
  useEffect(() => {
    const controller = new AbortController()
    fetchRxOtc(drugId, controller.signal)
      .then(setRxOtc)
      .catch(() => {
        /* aborted */
      })
    return () => controller.abort()
  }, [drugId])

  // Look up pharmacies whenever the place or the distance changes.
  useEffect(() => {
    if (!spot) return
    const controller = new AbortController()
    // The free public map servers are sometimes slow. Never leave people waiting on a spinner.
    let timedOut = false
    const timer = window.setTimeout(() => {
      timedOut = true
      controller.abort()
    }, 90_000)
    setStatus("loading")
    setMessage(null)
    setSelected(null)
    fetchNearby(spot.lat, spot.lon, miles, controller.signal)
      .then((result) => {
        setData(result)
        setStatus("ok")
      })
      .catch((cause) => {
        if (cause instanceof DOMException && cause.name === "AbortError") {
          if (timedOut) {
            setStatus("error")
            setMessage("This is taking longer than usual. Try a smaller distance, or try again in a minute.")
          }
          return
        }
        setStatus("error")
        setMessage(cause instanceof NearbyError ? cause.message : "Something went wrong while looking up pharmacies.")
      })
      .finally(() => window.clearTimeout(timer))
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [spot, miles])

  // Popup behavior: focus starts inside, the page behind does not scroll, Escape closes, and Tab stays inside.
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose
  useEffect(() => {
    closeButton.current?.focus()
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
    // Listen on the whole page, not just the popup: when focus is lost (for example a button is removed
    // while a lookup runs) the keys must still work.
    function onDocumentKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault()
        onCloseRef.current()
        return
      }
      if (event.key !== "Tab" || !panel.current) return
      const focusable = Array.from(
        panel.current.querySelectorAll<HTMLElement>("a[href], button:not([disabled]), input, [tabindex]:not([tabindex='-1'])"),
      )
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const active = document.activeElement
      if (!(active instanceof Node) || !panel.current.contains(active)) {
        event.preventDefault()
        ;(event.shiftKey ? last : first).focus()
      } else if (event.shiftKey && active === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && active === last) {
        event.preventDefault()
        first.focus()
      }
    }
    document.addEventListener("keydown", onDocumentKeyDown)
    return () => {
      document.removeEventListener("keydown", onDocumentKeyDown)
      document.body.style.overflow = previousOverflow
    }
  }, [])

  function locateMe() {
    if (busy) return
    if (!navigator.geolocation) {
      setStatus("error")
      setMessage("This browser cannot share your location. Type a ZIP code or address instead.")
      return
    }
    setStatus("locating")
    setMessage(null)
    navigator.geolocation.getCurrentPosition(
      (position) =>
        setSpot({ lat: position.coords.latitude, lon: position.coords.longitude, label: "your location" }),
      (error) => {
        setStatus("error")
        setMessage(
          error.code === error.PERMISSION_DENIED
            ? "Location sharing is turned off for this site. Type a ZIP code or address instead."
            : "We could not find your location. Type a ZIP code or address instead.",
        )
      },
      { timeout: 15000, maximumAge: 300000 },
    )
  }

  async function searchPlace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    const text = query.trim()
    if (text.length < 3) {
      setStatus("error")
      setMessage("Type at least 3 characters, such as a ZIP code.")
      return
    }
    setStatus("locating")
    setMessage(null)
    try {
      const matches = await fetchGeocode(text)
      if (matches.length === 0) {
        setStatus("error")
        setMessage("We could not find that place. Try a ZIP code or a street address.")
        return
      }
      setSpot({ lat: matches[0].lat, lon: matches[0].lon, label: shortPlace(matches[0].label) })
    } catch (cause) {
      setStatus("error")
      setMessage(cause instanceof NearbyError ? cause.message : "Something went wrong. Please try again.")
    }
  }

  const note = availabilityNote(rxOtc)
  const results = data?.results ?? []

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-2 sm:p-6"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby="nearby-title"
        className="max-h-[94vh] w-full max-w-3xl overflow-y-auto rounded-xl border border-border bg-background shadow-2xl"
      >
        <div className="flex items-start justify-between gap-3 border-b border-border p-4 sm:p-5">
          <div>
            <h2 id="nearby-title" className="text-2xl leading-tight">
              Find {drugName} nearby
            </h2>
            <p className="mt-1 text-sm font-medium">{note.headline}</p>
            <p className="text-sm text-muted-foreground">{note.detail}</p>
          </div>
          <Button ref={closeButton} type="button" variant="ghost" size="sm" onClick={onClose} aria-label="Close">
            <X className="h-5 w-5" />
          </Button>
        </div>

        <div className="space-y-4 p-4 sm:p-5">
          <p className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950">
            We can’t see what each pharmacy has on its shelves. <strong>Call before you go</strong> to make sure they
            have it.
          </p>

          <div className="space-y-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
              <Button type="button" onClick={locateMe} aria-disabled={busy} className={cn(busy && "opacity-60")}>
                <LocateFixed className="h-4 w-4" />
                Use my location
              </Button>
              <form onSubmit={(event) => void searchPlace(event)} className="flex flex-1 gap-2">
                <label className="sr-only" htmlFor="nearby-place">
                  ZIP code or address
                </label>
                <input
                  id="nearby-place"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="or type a ZIP code or address"
                  autoComplete="postal-code"
                  className="h-10 min-w-0 flex-1 rounded-md border border-input bg-card px-3 text-sm"
                />
                <Button type="submit" variant="secondary" aria-disabled={busy} className={cn(busy && "opacity-60")}>
                  <Search className="h-4 w-4" />
                  Search
                </Button>
              </form>
            </div>
            <p className="text-xs text-muted-foreground">
              Your location is only used to look up pharmacies. We don’t save it.
            </p>
          </div>

          <div role="group" aria-label="Distance" className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium">Show pharmacies within</span>
            {RADII.map((radius) => (
              <Button
                key={radius}
                type="button"
                size="sm"
                variant={miles === radius ? "default" : "outline"}
                aria-pressed={miles === radius}
                onClick={() => setMiles(radius)}
              >
                {milesLabel(radius)}
              </Button>
            ))}
          </div>

          <div aria-live="polite" className="min-h-6 text-sm">
            {status === "idle" ? (
              <p className="text-muted-foreground">Choose “Use my location” or type a ZIP code to see the map.</p>
            ) : null}
            {status === "locating" ? (
              <p className="flex items-center gap-2 text-muted-foreground">
                <LoaderCircle className="h-4 w-4 animate-spin" /> Finding your location…
              </p>
            ) : null}
            {status === "loading" ? (
              <p className="flex items-center gap-2 text-muted-foreground">
                <LoaderCircle className="h-4 w-4 animate-spin" /> Looking for pharmacies
                {miles === 25 ? " (a 25 mile search can take up to half a minute)" : ""}…
              </p>
            ) : null}
            {status === "error" && message ? (
              <p className="rounded-lg border border-destructive/30 bg-destructive/5 p-3">{message}</p>
            ) : null}
            {status === "ok" && spot && data ? (
              <p>
                {data.total_found === 0 ? (
                  <>
                    No pharmacies found within {milesLabel(miles)} of {spot.label}.
                    {miles < 25 ? " Try a larger distance." : ""}
                  </>
                ) : (
                  <>
                    <strong>
                      {data.total_found} {data.total_found === 1 ? "pharmacy" : "pharmacies"}
                    </strong>{" "}
                    within {milesLabel(miles)} of {spot.label}
                    {data.total_found > results.length ? `. Showing the closest ${results.length}.` : "."}
                  </>
                )}
              </p>
            ) : null}
          </div>

          {spot ? (
            <div className="relative overflow-hidden rounded-lg border border-border">
              <NearbyMap
                center={spot}
                miles={miles}
                pharmacies={results}
                selectedId={selected}
                onSelect={setSelected}
              />
              {busy ? <div className="absolute inset-0 bg-background/40" aria-hidden="true" /> : null}
            </div>
          ) : null}

          {status === "ok" && spot && results.length > 0 ? (
            <ol className="space-y-2">
              {results.map((pharmacy, index) => (
                <li
                  key={pharmacy.id}
                  className={cn(
                    "flex gap-3 rounded-lg border p-3 text-sm",
                    selected === pharmacy.id ? "border-primary bg-secondary/60" : "border-border bg-card",
                  )}
                >
                  <span
                    aria-hidden="true"
                    className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground"
                  >
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                      <button
                        type="button"
                        onClick={() => setSelected(pharmacy.id)}
                        aria-pressed={selected === pharmacy.id}
                        className="text-left font-semibold underline-offset-2 hover:underline"
                      >
                        {pharmacy.name}
                      </button>
                      <span className="text-muted-foreground">{pharmacy.distance_miles} mi</span>
                    </div>
                    {pharmacy.address ? <p className="text-muted-foreground">{pharmacy.address}</p> : null}
                    {pharmacy.hours ? <p>{pharmacy.hours}</p> : null}
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      {pharmacy.fills_prescriptions === true ? <Badge variant="secondary">Fills prescriptions</Badge> : null}
                      {pharmacy.fills_prescriptions === false ? (
                        <Badge variant="outline">Does not fill prescriptions</Badge>
                      ) : null}
                      {pharmacy.phone ? (
                        <a
                          href={telHref(pharmacy.phone)}
                          className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 font-medium hover:bg-secondary"
                        >
                          <Phone className="h-3.5 w-3.5" />
                          Call {pharmacy.phone}
                        </a>
                      ) : (
                        <span className="text-xs text-muted-foreground">No phone number on the map</span>
                      )}
                      <a
                        href={directionsUrl(spot, pharmacy)}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 font-medium hover:bg-secondary"
                      >
                        <Navigation className="h-3.5 w-3.5" />
                        Directions
                      </a>
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          ) : null}

          <p className="text-xs text-muted-foreground">
            {data?.notice ??
              "Pharmacy locations come from OpenStreetMap contributors and can be incomplete or out of date."}
          </p>
        </div>
      </div>
    </div>
  )
}
