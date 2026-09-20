// Types and calls for the "Find nearby" pharmacy map.

const API_BASE =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "http://127.0.0.1:18765"

export const RADII = [1, 10, 25] as const
export type Radius = (typeof RADII)[number]

export type Pharmacy = {
  id: string
  name: string
  lat: number
  lon: number
  distance_miles: number
  address: string | null
  phone: string | null
  website: string | null
  hours: string | null
  fills_prescriptions: boolean | null
}

export type NearbyResponse = {
  notice: string
  source: string
  lat: number
  lon: number
  radius_miles: number
  total_found: number
  results: Pharmacy[]
}

export type GeocodeMatch = { label: string; lon: number; lat: number }

export type Spot = { lat: number; lon: number; label: string }

export class NearbyError extends Error {}

async function getJson<T>(path: string, params: Record<string, string>, signal?: AbortSignal): Promise<T> {
  const url = new URL(path, API_BASE)
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, value)
  let response: Response
  try {
    response = await fetch(url, { signal })
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause
    throw new NearbyError("We could not reach the app's server. Is the backend running?")
  }
  if (!response.ok) {
    let detail = ""
    try {
      detail = ((await response.json()) as { detail?: unknown }).detail as string
    } catch {
      /* fall back to the generic message */
    }
    throw new NearbyError(
      typeof detail === "string" && detail ? detail : "Something went wrong while looking up pharmacies.",
    )
  }
  return (await response.json()) as T
}

export function fetchNearby(lat: number, lon: number, miles: number, signal?: AbortSignal) {
  return getJson<NearbyResponse>(
    "/pharmacies/nearby",
    { lat: String(lat), lon: String(lon), miles: String(miles) },
    signal,
  )
}

export async function fetchGeocode(query: string, signal?: AbortSignal): Promise<GeocodeMatch[]> {
  const body = await getJson<{ matches: GeocodeMatch[] }>("/geocode", { q: query }, signal)
  return body.matches
}

/** Whether the medicine is sold over the counter, by prescription, or both (from FDA labels). */
export async function fetchRxOtc(drugId: number, signal?: AbortSignal): Promise<string | null> {
  try {
    const body = await getJson<{ drug: { rx_otc: string | null } }>(`/drugs/${drugId}`, {}, signal)
    return body.drug.rx_otc
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause
    return null // the map still works without it
  }
}

/** What people can expect at a pharmacy, in plain words. We cannot know what is in stock. */
export function availabilityNote(rxOtc: string | null): { headline: string; detail: string } {
  if (rxOtc === "OTC") {
    return {
      headline: "You can buy this without a prescription.",
      detail: "Most pharmacies sell it, and so do many grocery and discount stores.",
    }
  }
  if (rxOtc === "Rx") {
    return {
      headline: "This medicine needs a prescription.",
      detail: "Any pharmacy can fill a prescription, but each one may or may not have it in stock.",
    }
  }
  if (rxOtc?.startsWith("OTC or Rx")) {
    return {
      headline: "Some versions need a prescription and some do not.",
      detail: "Ask the pharmacist which one is right for you.",
    }
  }
  return { headline: "Ask the pharmacist about this medicine.", detail: "They can tell you if you need a prescription." }
}

export function directionsUrl(from: Spot, to: Pharmacy): string {
  const route = `${from.lat}%2C${from.lon}%3B${to.lat}%2C${to.lon}`
  return `https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${route}`
}

export function telHref(phone: string): string {
  return `tel:${phone.replace(/[^\d+]/g, "")}`
}

export function milesLabel(miles: number): string {
  return miles === 1 ? "1 mile" : `${miles} miles`
}
