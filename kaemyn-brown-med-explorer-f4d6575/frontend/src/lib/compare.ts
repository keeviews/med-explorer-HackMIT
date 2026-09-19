import type { ComparePick } from "@/lib/types"

export const COMPARE_LIMIT = 4

const STORAGE_KEY = "discussmeds.compare"

export function loadComparePicks(): ComparePick[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as ComparePick[]
    if (!Array.isArray(parsed)) return []
    return parsed
      .filter((item) => typeof item?.id === "number" && typeof item?.name === "string")
      .slice(0, COMPARE_LIMIT)
  } catch {
    return []
  }
}

export function saveComparePicks(picks: ComparePick[]): void {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(picks.slice(0, COMPARE_LIMIT)))
}
