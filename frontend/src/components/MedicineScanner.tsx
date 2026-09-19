import { useEffect, useRef, useState } from "react"
import { Camera, Check, Images, LoaderCircle, RefreshCw, ScanLine, ShieldCheck, Trash2, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { fetchMedicineResolution } from "@/lib/api"
import { ApiError, type ScanCandidate, type MedicineScanResponse } from "@/lib/types"

type MedicineScannerProps = { disabled: boolean; onAdd: (candidates: ScanCandidate[]) => void }
type CapturedLabel = { blob: Blob; previewUrl: string }
type ScanResult = CapturedLabel & { scan: MedicineScanResponse }
type OcrItem = { text: string; score: number }
type BrowserOcr = { predict: (input: Blob) => Promise<Array<{ items: OcrItem[] }>> }

let browserOcr: Promise<BrowserOcr> | null = null

function getBrowserOcr(): Promise<BrowserOcr> {
  browserOcr ??= import("@paddleocr/paddleocr-js").then(({ PaddleOCR }) =>
    PaddleOCR.create({ lang: "en", ocrVersion: "PP-OCRv5", ortOptions: { backend: "auto" } }),
  )
  return browserOcr
}

export function MedicineScanner({ disabled, onAdd }: MedicineScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const urlsRef = useRef(new Set<string>())
  const [state, setState] = useState<"idle" | "camera" | "scanning" | "result" | "error">("idle")
  const [queue, setQueue] = useState<CapturedLabel[]>([])
  const [results, setResults] = useState<ScanResult[]>([])
  const [selections, setSelections] = useState<Record<number, ScanCandidate>>({})
  const [ocrStatus, setOcrStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  function stopCamera() {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }

  useEffect(() => () => {
    stopCamera()
    urlsRef.current.forEach((url) => URL.revokeObjectURL(url))
  }, [])

  async function startCamera() {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      })
      streamRef.current = stream
      setState("camera")
      window.requestAnimationFrame(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          void videoRef.current.play()
        }
      })
    } catch {
      setState("error")
      setError("Camera access was unavailable. Allow camera permission, then try again.")
    }
  }

  function capturePhoto() {
    const video = videoRef.current
    if (!video || video.videoWidth === 0) return
    const canvas = document.createElement("canvas")
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext("2d")?.drawImage(video, 0, 0, canvas.width, canvas.height)
    canvas.toBlob((blob) => {
      if (!blob) return
      const previewUrl = URL.createObjectURL(blob)
      urlsRef.current.add(previewUrl)
      setQueue((current) => [...current, { blob, previewUrl }])
    }, "image/jpeg", 0.9)
  }

  function removePhoto(index: number) {
    setQueue((current) => {
      const found = current[index]
      if (found) {
        URL.revokeObjectURL(found.previewUrl)
        urlsRef.current.delete(found.previewUrl)
      }
      return current.filter((_, itemIndex) => itemIndex !== index)
    })
  }

  async function processQueue() {
    if (queue.length === 0) return
    stopCamera()
    setState("scanning")
    setError(null)
    try {
      setOcrStatus("Preparing the private, in-browser reader…")
      const ocr = await getBrowserOcr()
      const scanned: ScanResult[] = []
      for (const [index, label] of queue.entries()) {
        setOcrStatus(`Reading label ${index + 1} of ${queue.length} in your browser…`)
        try {
          const [result] = await ocr.predict(label.blob)
          const rawText = (result?.items ?? []).filter((item) => item.score >= 0.5).map((item) => item.text.trim()).filter(Boolean).join("\n")
          if (!rawText) throw new ApiError("No readable label text was found.")
          setOcrStatus(`Finding medicine ${index + 1} of ${queue.length}…`)
          scanned.push({ ...label, scan: await fetchMedicineResolution(rawText) })
        } catch (cause) {
          scanned.push({
            ...label,
            scan: {
              disclaimer: "",
              mode: "ocr",
              notice: cause instanceof ApiError ? cause.message : "This label could not be read. Retake it in brighter light.",
              raw_text: "",
              candidates: [],
            },
          })
        }
      }
      setResults(scanned)
      setState("result")
    } catch (cause) {
      setState("error")
      setError(cause instanceof ApiError ? cause.message : "We could not start the label reader. Please try again.")
    }
  }

  function reset() {
    stopCamera()
    urlsRef.current.forEach((url) => URL.revokeObjectURL(url))
    urlsRef.current.clear()
    setQueue([])
    setResults([])
    setSelections({})
    setOcrStatus(null)
    setError(null)
    setState("idle")
  }

  const selected = Object.values(selections)

  return (
    <section className="relative overflow-hidden rounded-3xl bg-[#2c3e50] p-5 text-[#f7f9f9] shadow-[0_22px_55px_rgba(44,62,80,0.18)] sm:p-7">
      <div className="relative space-y-5">
        <header className="flex flex-col gap-5 border-b border-white/15 pb-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h3 className="mt-3 font-heading text-2xl leading-tight">Build your medicine list from labels.</h3>
            <p className="mt-1 max-w-xl text-sm text-white/75">Photograph every label first. One review step adds the medicines you approve.</p>
          </div>
          <div className="grid grid-cols-3 gap-3 text-center text-xs text-white/65">
            <div><span className="mx-auto mb-1 flex h-7 w-7 items-center justify-center rounded-full border border-white/30 text-white">1</span>Capture</div>
            <div><span className="mx-auto mb-1 flex h-7 w-7 items-center justify-center rounded-full border border-white/30 text-white">2</span>Review</div>
            <div><span className="mx-auto mb-1 flex h-7 w-7 items-center justify-center rounded-full border border-white/30 text-white">3</span>Add</div>
          </div>
        </header>
        {(state === "idle" || state === "error") ? <div className="grid gap-5 rounded-2xl border border-white/15 bg-white/5 p-5 sm:grid-cols-[auto_1fr_auto] sm:items-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#f39c12] text-[#2c3e50] shadow-lg"><ScanLine className="h-8 w-8" /></div>
          <div><p className="font-heading text-xl">Start a label session</p><p className="mt-1 text-sm text-white/70">Queue every bottle or box before the reader starts. Your photos stay on this device.</p></div>
          <Button className="h-12 bg-[#f7f9f9] px-5 text-[#16a085] hover:bg-white" type="button" onClick={() => void startCamera()} disabled={disabled}><Camera className="h-4 w-4" /> Start capturing</Button>
          {disabled ? <span className="text-sm text-[#f39c12] sm:col-span-3">Your current list is full.</span> : null}
          {error ? <p className="text-sm text-[#f39c12] sm:col-span-3">{error}</p> : null}
        </div> : null}
        {state === "camera" ? <div className="space-y-4">
          <div className="relative overflow-hidden rounded-2xl border border-white/20 bg-black shadow-2xl"><video ref={videoRef} className="w-full max-h-[28rem] object-contain" muted playsInline /><div className="pointer-events-none absolute inset-5 rounded-xl border-2 border-[#16a085]/80"><span className="absolute -top-3 left-4 bg-[#2c3e50] px-2 text-xs text-white/70">Keep the full label inside the frame</span></div></div>
          <div className="flex flex-wrap items-center justify-between gap-3"><p className="text-sm text-white/70">Center one printed label at a time in good light. Do not scan loose pills.</p><span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-sm"><Images className="h-4 w-4 text-[#f39c12]" /> {queue.length} ready</span></div>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Button className="h-16 w-16 rounded-full border-4 border-[#f7f9f9] bg-[#16a085] p-0 hover:bg-[#16a085]/90" type="button" onClick={capturePhoto} aria-label="Take label photo"><Camera className="h-6 w-6" /></Button>
            <Button className="bg-[#f39c12] text-[#2c3e50] hover:bg-[#f39c12]/90" type="button" disabled={queue.length === 0} onClick={() => void processQueue()}><Check className="h-4 w-4" /> Review {queue.length} {queue.length === 1 ? "label" : "labels"}</Button>
            <Button className="text-white hover:bg-white/10 hover:text-white" type="button" variant="ghost" onClick={reset}><X className="h-4 w-4" /> Cancel</Button>
          </div>
        {queue.length > 0 ? <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">{queue.map((label, index) => <div key={label.previewUrl} className="relative">
          <img className="h-20 w-full rounded-lg border border-white/25 object-cover" src={label.previewUrl} alt={`Label ${index + 1}`} />
          <span className="absolute bottom-1 left-1 rounded bg-[#2c3e50]/90 px-1.5 py-0.5 text-[10px]">{index + 1}</span>
          <Button className="absolute right-1 top-1 h-6 w-6 bg-[#f7f9f9] p-0 text-[#2c3e50] hover:bg-white" type="button" size="icon" variant="secondary" onClick={() => removePhoto(index)} aria-label={`Remove label ${index + 1}`}><Trash2 className="h-3 w-3" /></Button>
        </div>)}</div> : null}
      </div> : null}
      {state === "scanning" ? <div className="flex min-h-40 flex-col items-center justify-center gap-3 rounded-2xl border border-white/15 bg-white/5 text-center"><LoaderCircle className="h-8 w-8 animate-spin text-[#f39c12]" /><p className="font-heading text-xl">Reading your labels</p><p className="text-sm text-white/70">{ocrStatus ?? "Reading labels…"}</p></div> : null}
      {state === "result" ? <div className="space-y-4 rounded-2xl bg-[#f7f9f9] p-4 text-[#2c3e50] sm:p-5">
        <div className="flex items-center justify-between gap-3"><div><p className="font-heading text-xl">Review your matches</p><p className="mt-1 text-sm text-[#34495e]">Choose only the medicines that match the printed labels.</p></div><span className="rounded-full bg-[#16a085]/15 px-3 py-1 text-sm font-medium text-[#16a085]">{results.length} labels</span></div>
        {results.map((result, resultIndex) => <div key={result.previewUrl} className="space-y-2 rounded-xl border border-[#cfd9dc] bg-white p-3">
          <div className="flex gap-3"><img className="h-20 w-20 rounded border border-border object-cover" src={result.previewUrl} alt={`Captured label ${resultIndex + 1}`} /><div><p className="text-sm font-medium">Label {resultIndex + 1}</p><p className="text-xs text-muted-foreground">{result.scan.notice}</p></div></div>
          {result.scan.raw_text ? <p className="text-xs text-muted-foreground whitespace-pre-line">{result.scan.raw_text}</p> : null}
          {result.scan.candidates.length > 0 ? result.scan.candidates.map((candidate) => <button key={candidate.id} type="button" className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left text-sm ${selections[resultIndex]?.id === candidate.id ? "border-primary bg-primary/10" : "border-border bg-card hover:bg-accent"}`} onClick={() => setSelections((current) => ({ ...current, [resultIndex]: candidate }))}>
            <span><span className="font-medium">{candidate.name}</span>{candidate.strength ? ` · ${candidate.strength}` : ""}{candidate.form ? ` · ${candidate.form}` : ""}</span><span className="text-xs text-muted-foreground">{selections[resultIndex]?.id === candidate.id ? "Selected" : "Select"}</span>
          </button>) : <p className="text-sm text-muted-foreground">No medicine match found. Retake this label or add it manually.</p>}
        </div>)}
        <div className="flex flex-wrap gap-2 border-t border-[#cfd9dc] pt-4"><Button type="button" disabled={selected.length === 0 || disabled} onClick={() => { onAdd(selected); reset() }}><Check className="h-4 w-4" /> Add {selected.length} selected {selected.length === 1 ? "medicine" : "medicines"}</Button><Button type="button" variant="ghost" onClick={reset}><RefreshCw className="h-4 w-4" /> Start over</Button></div>
      </div> : null}
      </div>
    </section>
  )
}
