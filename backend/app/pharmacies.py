"""Find pharmacies near a point, using OpenStreetMap data.

- Pharmacy locations come from the Overpass API (OpenStreetMap contributors).
- A ZIP code or address is turned into a point with Nominatim (also OpenStreetMap).

Nothing here knows what a pharmacy has IN STOCK. No open dataset does. The app tells
people to call ahead. Locations are used to answer one request and are not stored or logged;
results are kept in memory for a few minutes so the public map servers are not hit twice.
"""

from __future__ import annotations

import math
import re
import threading
import time

import httpx
from pydantic import BaseModel, Field

# Both services ask for an identifying User-Agent; requests without one are rejected.
USER_AGENT = "DiscussMeds-hackathon/0.1 (github.com/keeviews/med-explorer-HackMIT)"
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

METERS_PER_MILE = 1609.344
MAX_MILES = 25.0
MAX_RESULTS = 60
CACHE_SECONDS = 600
NOMINATIM_MIN_GAP_SECONDS = 1.1  # Nominatim's usage policy: at most one request per second

SOURCE_NOTICE = (
    "Pharmacy locations come from OpenStreetMap contributors and can be incomplete or out of date. "
    "We cannot see what any pharmacy has in stock, so call before you go."
)


class PharmacyLookupError(Exception):
    """The public map service could not be reached or gave an unusable answer."""


class Pharmacy(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    distance_miles: float
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    hours: str | None = Field(None, description="Opening hours in plain English, when they can be understood")
    fills_prescriptions: bool | None = Field(None, description="None means the map data does not say")


class NearbyPharmaciesResponse(BaseModel):
    notice: str = SOURCE_NOTICE
    source: str = "OpenStreetMap contributors (Overpass API)"
    lat: float
    lon: float
    radius_miles: float
    total_found: int
    results: list[Pharmacy]


class GeocodeMatch(BaseModel):
    label: str
    lat: float
    lon: float


class GeocodeResponse(BaseModel):
    source: str = "OpenStreetMap contributors (Nominatim)"
    matches: list[GeocodeMatch]


# ---------------------------------------------------------------------------
# Distance
# ---------------------------------------------------------------------------
def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_miles = 3958.7613
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius_miles * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# Opening hours: OpenStreetMap writes "Mo-Fr 09:00-21:00; Sa 09:00-17:00". Say it in plain English.
# ---------------------------------------------------------------------------
_DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
_DAY_NAMES = {"Mo": "Mon", "Tu": "Tue", "We": "Wed", "Th": "Thu", "Fr": "Fri", "Sa": "Sat", "Su": "Sun"}
_RANGE = re.compile(r"^(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$")


def _clock(hour: int, minute: int) -> str:
    if (hour, minute) in ((0, 0), (24, 0)):
        return "midnight"
    if (hour, minute) == (12, 0):
        return "noon"
    suffix = "am" if hour % 24 < 12 else "pm"
    hour12 = hour % 12 or 12
    return f"{hour12} {suffix}" if minute == 0 else f"{hour12}:{minute:02d} {suffix}"


def _day_list(spec: str) -> str | None:
    names = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start, _, end = part.partition("-")
            if start not in _DAYS or end not in _DAYS:
                return None
            names.append(f"{_DAY_NAMES[start]}–{_DAY_NAMES[end]}")
        elif part in _DAYS:
            names.append(_DAY_NAMES[part])
        else:
            return None
    return ", ".join(names)


def format_hours(raw: str | None) -> str | None:
    """Turn simple OpenStreetMap opening hours into plain English; None if they are too unusual."""
    if not raw:
        return None
    text = raw.strip()
    if text == "24/7":
        return "Open 24 hours, every day"
    pieces = []
    for segment in (s.strip() for s in text.split(";") if s.strip()):
        match = re.match(r"^([A-Za-z,\-]+)?\s*(.*)$", segment)
        days_spec, rest = (match.group(1) or ""), match.group(2).strip()
        days = _day_list(days_spec) if days_spec else "Every day"
        if days is None:
            return None
        if rest == "off":
            pieces.append(f"{days}: closed")
            continue
        if rest in ("24/7", "00:00-24:00"):
            pieces.append(f"{days}: open 24 hours")
            continue
        ranges = []
        for chunk in (c.strip() for c in rest.split(",") if c.strip()):
            parsed = _RANGE.match(chunk)
            if not parsed:
                return None
            h1, m1, h2, m2 = (int(g) for g in parsed.groups())
            if h1 > 24 or h2 > 24 or m1 > 59 or m2 > 59:
                return None
            ranges.append(f"{_clock(h1, m1)} to {_clock(h2, m2)}")
        if not ranges:
            return None
        pieces.append(f"{days}: {' and '.join(ranges)}")
    return "; ".join(pieces) or None


# ---------------------------------------------------------------------------
# Turning Overpass results into pharmacies
# ---------------------------------------------------------------------------
def _address(tags: dict) -> str | None:
    street = " ".join(p for p in (tags.get("addr:housenumber"), tags.get("addr:street")) if p)
    place = ", ".join(p for p in (tags.get("addr:city"), tags.get("addr:state")) if p)
    locality = " ".join(p for p in (place, tags.get("addr:postcode")) if p)
    return ", ".join(p for p in (street, locality) if p) or None


def _phone(tags: dict) -> str | None:
    return tags.get("phone") or tags.get("contact:phone")


def parse_pharmacies(elements: list[dict], lat: float, lon: float, miles: float) -> tuple[list[Pharmacy], int]:
    """Nearest-first pharmacies within `miles`, with duplicates merged. Also returns how many were found."""
    found: list[Pharmacy] = []
    for element in elements:
        tags = element.get("tags") or {}
        point = element if "lat" in element else element.get("center") or {}
        if "lat" not in point or "lon" not in point:
            continue
        distance = haversine_miles(lat, lon, point["lat"], point["lon"])
        if distance > miles + 0.02:
            continue
        name = tags.get("name") or tags.get("brand") or tags.get("operator") or "Pharmacy"
        dispensing = tags.get("dispensing")
        found.append(
            Pharmacy(
                id=f"{element.get('type', 'node')}/{element.get('id')}",
                name=name,
                lat=point["lat"],
                lon=point["lon"],
                distance_miles=round(distance, 2),
                address=_address(tags),
                phone=_phone(tags),
                website=tags.get("website") or tags.get("contact:website"),
                hours=format_hours(tags.get("opening_hours")),
                fills_prescriptions=True if dispensing == "yes" else False if dispensing == "no" else None,
            )
        )
    found.sort(key=lambda p: (p.distance_miles, p.name))
    # OpenStreetMap often maps one store twice (a point and a building outline). Keep the one with more detail.
    unique: list[Pharmacy] = []
    for item in found:
        twin = next(
            (u for u in unique if u.name.lower() == item.name.lower()
             and haversine_miles(u.lat, u.lon, item.lat, item.lon) < 0.06),
            None,
        )
        if twin is None:
            unique.append(item)
        elif sum(v is not None for v in (item.phone, item.hours, item.address)) > sum(
            v is not None for v in (twin.phone, twin.hours, twin.address)
        ):
            unique[unique.index(twin)] = item
    return unique[:MAX_RESULTS], len(unique)


# ---------------------------------------------------------------------------
# Network calls (kept small so tests can replace them)
# ---------------------------------------------------------------------------
def _overpass_query(lat: float, lon: float, miles: float) -> str:
    meters = int(miles * METERS_PER_MILE)
    around = f"(around:{meters},{lat:.5f},{lon:.5f})"
    return f'[out:json][timeout:50];(node["amenity"="pharmacy"]{around};way["amenity"="pharmacy"]{around};);out center tags;'


OVERPASS_TOTAL_SECONDS = 75  # a 25-mile search can take ~25 s on the public servers; never wait longer than this


def _run_overpass(query: str) -> list[dict]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    deadline = time.monotonic() + OVERPASS_TOTAL_SECONDS
    last_error: Exception | None = None
    for attempt in range(2):
        if attempt:
            time.sleep(2)  # give a briefly overloaded server a moment before trying the list again
        for endpoint in OVERPASS_ENDPOINTS:
            remaining = deadline - time.monotonic()
            if remaining < 8:
                break
            try:
                response = httpx.post(endpoint, data={"data": query}, headers=headers, timeout=min(50, remaining))
                response.raise_for_status()
                return response.json().get("elements", [])
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
    raise PharmacyLookupError("The map service is busy right now. A smaller distance can help.") from last_error


_nominatim_lock = threading.Lock()
_last_nominatim_call = 0.0


def _run_nominatim(text: str) -> list[dict]:
    global _last_nominatim_call
    params = {"format": "jsonv2", "limit": 5, "countrycodes": "us", "q": text}
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    with _nominatim_lock:
        wait = NOMINATIM_MIN_GAP_SECONDS - (time.monotonic() - _last_nominatim_call)
        if wait > 0:
            time.sleep(wait)
        try:
            response = httpx.get(NOMINATIM_URL, params=params, headers=headers, timeout=20)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise PharmacyLookupError("The address search is busy right now.") from exc
        finally:
            _last_nominatim_call = time.monotonic()


# ---------------------------------------------------------------------------
# Public functions, with a small in-memory cache
# ---------------------------------------------------------------------------
_cache: dict[tuple, tuple[float, object]] = {}
_cache_lock = threading.Lock()


def _cached(key: tuple, compute):
    now = time.monotonic()
    with _cache_lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < CACHE_SECONDS:
            return hit[1]
        for stale in [k for k, (stamp, _v) in _cache.items() if now - stamp >= CACHE_SECONDS]:
            del _cache[stale]
    value = compute()
    with _cache_lock:
        _cache[key] = (now, value)
    return value


QUERY_PADDING_MILES = 0.15  # covers the rounding of the cached search point (about 0.08 miles)


def find_pharmacies(lat: float, lon: float, miles: float) -> NearbyPharmaciesResponse:
    miles = min(max(miles, 0.1), MAX_MILES)
    # Only the raw map data is cached, keyed by a location rounded to ~100 m and searched a little wider.
    # Distances are then worked out from each person's own position, so an exact location is never shared
    # with, or stored for, anyone else.
    search_lat, search_lon = round(lat, 3), round(lon, 3)
    key = ("pharmacies", search_lat, search_lon, round(miles, 1))
    elements = _cached(
        key, lambda: _run_overpass(_overpass_query(search_lat, search_lon, min(miles + QUERY_PADDING_MILES, MAX_MILES + QUERY_PADDING_MILES)))
    )
    results, total = parse_pharmacies(elements, lat, lon, miles)
    return NearbyPharmaciesResponse(lat=lat, lon=lon, radius_miles=miles, total_found=total, results=results)


def geocode(text: str) -> GeocodeResponse:
    query = " ".join(text.split())
    key = ("geocode", query.lower())

    def compute() -> GeocodeResponse:
        rows = _run_nominatim(query)
        matches = [
            GeocodeMatch(label=row["display_name"], lat=float(row["lat"]), lon=float(row["lon"]))
            for row in rows
            if "lat" in row and "lon" in row
        ]
        return GeocodeResponse(matches=matches)

    return _cached(key, compute)
