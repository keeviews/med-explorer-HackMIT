import type { MedicineNote, UnmappedMedication } from "@/lib/types"

export const CABINET_LIMIT = 12

const STORAGE_KEY = "discussmeds.cabinet"

export type MedicineCabinet = {
  current: MedicineNote[]
  history: MedicineNote[]
  unmapped: UnmappedMedication[]
}

const EMPTY: MedicineCabinet = { current: [], history: [], unmapped: [] }

export function loadCabinet(): MedicineCabinet {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return EMPTY
    const parsed = JSON.parse(raw) as MedicineCabinet
    if (!parsed || !Array.isArray(parsed.current) || !Array.isArray(parsed.history)) {
      return EMPTY
    }
    return {
      current: parsed.current.filter(isNote).slice(0, CABINET_LIMIT),
      history: parsed.history.filter(isNote).slice(0, 40),
      unmapped: Array.isArray(parsed.unmapped) ? parsed.unmapped.filter(isUnmapped) : [],
    }
  } catch {
    return EMPTY
  }
}

export function saveCabinet(cabinet: MedicineCabinet): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(cabinet))
}

function isNote(item: MedicineNote): item is MedicineNote {
  return typeof item?.id === "number" && typeof item?.name === "string"
}

function isUnmapped(item: UnmappedMedication): item is UnmappedMedication {
  return typeof item?.name === "string" && item.name.length > 0
}

export function isCurrent(cabinet: MedicineCabinet, id: number): boolean {
  return cabinet.current.some((item) => item.id === id)
}

export function addCurrent(cabinet: MedicineCabinet, note: MedicineNote): MedicineCabinet {
  if (cabinet.current.some((item) => item.id === note.id)) return cabinet
  if (cabinet.current.length >= CABINET_LIMIT) return cabinet
  return {
    ...cabinet,
    current: [...cabinet.current, { ...note, addedAt: note.addedAt || new Date().toISOString() }],
    history: cabinet.history.filter((item) => item.id !== note.id),
  }
}

export function moveToHistory(cabinet: MedicineCabinet, id: number): MedicineCabinet {
  const match = cabinet.current.find((item) => item.id === id)
  if (!match) return cabinet
  return {
    ...cabinet,
    current: cabinet.current.filter((item) => item.id !== id),
    history: [
      { ...match, stoppedAt: new Date().toISOString() },
      ...cabinet.history.filter((item) => item.id !== id),
    ].slice(0, 40),
  }
}

export function restoreCurrent(cabinet: MedicineCabinet, id: number): MedicineCabinet {
  const match = cabinet.history.find((item) => item.id === id)
  if (!match) return cabinet
  const restored = {
    id: match.id,
    name: match.name,
    addedAt: new Date().toISOString(),
    source: match.source,
    fhir_name: match.fhir_name,
  }
  return addCurrent(
    { ...cabinet, history: cabinet.history.filter((item) => item.id !== id) },
    restored,
  )
}

export function removeHistory(cabinet: MedicineCabinet, id: number): MedicineCabinet {
  return { ...cabinet, history: cabinet.history.filter((item) => item.id !== id) }
}

export function removeUnmapped(cabinet: MedicineCabinet, name: string): MedicineCabinet {
  return {
    ...cabinet,
    unmapped: cabinet.unmapped.filter((item) => item.name !== name),
  }
}

export function mergeImport(
  cabinet: MedicineCabinet,
  notes: MedicineNote[],
  unmapped: UnmappedMedication[],
): MedicineCabinet {
  let next: MedicineCabinet = { ...cabinet, unmapped: [...cabinet.unmapped] }
  for (const note of notes) {
    next = addCurrent(next, note)
  }
  for (const item of unmapped) {
    if (!next.unmapped.some((row) => row.name.toLowerCase() === item.name.toLowerCase())) {
      next = { ...next, unmapped: [...next.unmapped, item] }
    }
  }
  return next
}
