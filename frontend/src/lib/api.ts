import { ApiError, type CompareResponse, type ConditionsResponse, type FhirImportResponse, type MedicineScanResponse, type MyChartStatus, type SuggestResponse } from "@/lib/types"

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ??
  "http://127.0.0.1:18765"

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = new ApiError(
      response.status === 0
        ? "Could not reach the suggestion service."
        : `The suggestion service returned ${response.status}.`,
    )
    error.status = response.status
    throw error
  }
  return (await response.json()) as T
}

export async function fetchSuggestions(query: string, limit = 20): Promise<SuggestResponse> {
  const url = new URL("/suggest", API_BASE)
  url.searchParams.set("q", query)
  url.searchParams.set("limit", String(limit))
  try {
    const response = await fetch(url)
    return await readJson<SuggestResponse>(response)
  } catch (cause) {
    if (cause instanceof ApiError) throw cause
    const error = new ApiError(
      "Could not reach the suggestion service. Is the backend running on port 18765?",
    )
    throw error
  }
}

export async function fetchSeededConditions(): Promise<ConditionsResponse> {
  const url = new URL("/conditions", API_BASE)
  try {
    const response = await fetch(url)
    return await readJson<ConditionsResponse>(response)
  } catch (cause) {
    if (cause instanceof ApiError) throw cause
    const error = new ApiError("Could not load seeded conditions from the API.")
    throw error
  }
}

export async function fetchCompare(ids: number[]): Promise<CompareResponse> {
  const url = new URL("/compare", API_BASE)
  url.searchParams.set("ids", ids.join(","))
  try {
    const response = await fetch(url)
    return await readJson<CompareResponse>(response)
  } catch (cause) {
    if (cause instanceof ApiError) throw cause
    const error = new ApiError("Could not load the compare table from the API.")
    throw error
  }
}

export async function fetchReview(ids: number[]): Promise<CompareResponse> {
  const url = new URL("/review", API_BASE)
  url.searchParams.set("ids", ids.join(","))
  try {
    const response = await fetch(url)
    return await readJson<CompareResponse>(response)
  } catch (cause) {
    if (cause instanceof ApiError) throw cause
    const error = new ApiError("Could not review the current-medicine list.")
    throw error
  }
}

export async function fetchMyChartStatus(): Promise<MyChartStatus> {
  const url = new URL("/integrations/mychart", API_BASE)
  try {
    const response = await fetch(url)
    return await readJson<MyChartStatus>(response)
  } catch (cause) {
    if (cause instanceof ApiError) throw cause
    throw new ApiError("Could not load MyChart connection status.")
  }
}

export async function fetchMyChartDemoImport(): Promise<FhirImportResponse> {
  const url = new URL("/integrations/mychart/demo", API_BASE)
  try {
    const response = await fetch(url)
    return await readJson<FhirImportResponse>(response)
  } catch (cause) {
    if (cause instanceof ApiError) throw cause
    throw new ApiError("Could not load the demo MyChart / FHIR medication list.")
  }
}

export async function fetchMedicineResolution(rawText: string): Promise<MedicineScanResponse> {
  const url = new URL("/medicines/resolve", API_BASE)
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_text: rawText }),
    })
    return await readJson<MedicineScanResponse>(response)
  } catch (cause) {
    if (cause instanceof ApiError) throw cause
    throw new ApiError("Could not reach the label-scanning service.")
  }
}
