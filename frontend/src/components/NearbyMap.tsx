import { useEffect, useRef } from "react"
import L from "leaflet"
import "leaflet/dist/leaflet.css"

import type { Pharmacy } from "@/lib/nearby"

const METERS_PER_MILE = 1609.344

type NearbyMapProps = {
  center: { lat: number; lon: number }
  miles: number
  pharmacies: Pharmacy[]
  selectedId: string | null
  onSelect: (id: string) => void
}

type MapState = { map: L.Map; layer: L.LayerGroup; markers: Map<string, L.Marker>; pharmacies: Pharmacy[] }

// Plain circles instead of Leaflet's image markers (those break under bundlers). Numbers match the list.
function pinIcon(number: number, selected: boolean): L.DivIcon {
  const size = selected ? 32 : 26
  const colors = selected ? "background:#1c2b24" : "background:#2f6f5e"
  return L.divIcon({
    className: "",
    html: `<span style="display:flex;align-items:center;justify-content:center;width:${size}px;height:${size}px;border-radius:50%;${colors};color:#fff;font:600 12px sans-serif;border:2px solid #fff;box-shadow:0 1px 5px rgba(0,0,0,.45)">${number}</span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })
}

const youIcon = L.divIcon({
  className: "",
  html: '<span style="display:block;width:18px;height:18px;border-radius:50%;background:#2563eb;border:3px solid #fff;box-shadow:0 0 0 2px #2563eb,0 1px 5px rgba(0,0,0,.45)"></span>',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
})

// Tooltips are built from text nodes: pharmacy names come from a public map database and must
// never be inserted as HTML.
function textNode(text: string): HTMLElement {
  const node = document.createElement("span")
  node.textContent = text
  return node
}

export function NearbyMap({ center, miles, pharmacies, selectedId, onSelect }: NearbyMapProps) {
  const container = useRef<HTMLDivElement>(null)
  const state = useRef<MapState | null>(null)
  const onSelectRef = useRef(onSelect)
  onSelectRef.current = onSelect

  useEffect(() => {
    if (!container.current) return
    const map = L.map(container.current, { scrollWheelZoom: false }).setView([center.lat, center.lon], 12)
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors',
    }).addTo(map)
    state.current = { map, layer: L.layerGroup().addTo(map), markers: new Map(), pharmacies: [] }
    // The map starts inside a popup that is still animating in, so measure again once it settles.
    const settle = window.setTimeout(() => map.invalidateSize(), 200)
    return () => {
      window.clearTimeout(settle)
      map.remove()
      state.current = null
    }
    // The map is created once; later changes are drawn by the effect below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const current = state.current
    if (!current) return
    current.layer.clearLayers()
    current.markers.clear()
    current.pharmacies = pharmacies
    const circle = L.circle([center.lat, center.lon], {
      radius: miles * METERS_PER_MILE,
      color: "#2f6f5e",
      weight: 2,
      fillOpacity: 0.06,
    }).addTo(current.layer)
    L.marker([center.lat, center.lon], { icon: youIcon, keyboard: false, zIndexOffset: 1000 })
      .bindTooltip(textNode("You are here"))
      .addTo(current.layer)
    pharmacies.forEach((pharmacy, index) => {
      const marker = L.marker([pharmacy.lat, pharmacy.lon], {
        icon: pinIcon(index + 1, false),
        title: pharmacy.name,
        keyboard: false, // the list beside the map is the keyboard-friendly way in
      })
        .bindTooltip(textNode(`${index + 1}. ${pharmacy.name}`))
        .on("click", () => onSelectRef.current(pharmacy.id))
        .addTo(current.layer)
      current.markers.set(pharmacy.id, marker)
    })
    current.map.fitBounds(circle.getBounds(), { padding: [12, 12] })
  }, [center.lat, center.lon, miles, pharmacies])

  useEffect(() => {
    const current = state.current
    if (!current) return
    current.pharmacies.forEach((pharmacy, index) => {
      const marker = current.markers.get(pharmacy.id)
      if (!marker) return
      const selected = pharmacy.id === selectedId
      marker.setIcon(pinIcon(index + 1, selected))
      marker.setZIndexOffset(selected ? 900 : 0)
      if (selected) current.map.panTo(marker.getLatLng(), { animate: true })
    })
  }, [selectedId, pharmacies])

  return <div ref={container} className="h-72 w-full sm:h-96" role="region" aria-label="Map of nearby pharmacies" />
}
