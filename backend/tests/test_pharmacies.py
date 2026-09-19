"""Pharmacy lookup tests. The map services are replaced with fake data, so no network is used."""

import pytest
from fastapi.testclient import TestClient

from app import pharmacies
from app.main import app

client = TestClient(app)

HERE = (42.3601, -71.0942)  # a point in Cambridge, MA


def element(kind, element_id, name, lat, lon, **tags):
    item = {"type": kind, "id": element_id, "tags": {"name": name, **tags}}
    if kind == "way":
        item["center"] = {"lat": lat, "lon": lon}
    else:
        item["lat"], item["lon"] = lat, lon
    return item


@pytest.fixture(autouse=True)
def clean_cache():
    pharmacies._cache.clear()
    yield
    pharmacies._cache.clear()


@pytest.fixture
def fake_overpass(monkeypatch):
    calls = []

    def fake(query):
        calls.append(query)
        return [
            element("node", 1, "Corner Pharmacy", 42.3610, -71.0950, **{
                "addr:housenumber": "12", "addr:street": "Main Street", "addr:city": "Cambridge",
                "addr:state": "MA", "addr:postcode": "02139", "phone": "+1 617 555 0100",
                "opening_hours": "Mo-Fr 09:00-21:00; Sa 09:00-17:00; Su off", "dispensing": "yes"}),
            element("way", 2, "Far Away Drugs", 42.4500, -71.0942),  # about 6 miles north
            element("node", 3, "Late Night Pharmacy", 42.3650, -71.1000, opening_hours="24/7"),
            element("node", 4, "No Coordinates", 0, 0),
        ]

    monkeypatch.setattr(pharmacies, "_run_overpass", fake)
    fake.calls = calls
    return fake


def test_distance_is_in_miles():
    assert pharmacies.haversine_miles(0, 0, 0, 1) == pytest.approx(69.1, abs=0.3)
    assert pharmacies.haversine_miles(*HERE, *HERE) == 0


def test_hours_are_turned_into_plain_english():
    assert pharmacies.format_hours("24/7") == "Open 24 hours, every day"
    assert pharmacies.format_hours("Mo-Su 08:00-21:00") == "Mon–Sun: 8 am to 9 pm"
    assert (
        pharmacies.format_hours("Mo-Fr 09:00-21:00; Sa 09:00-17:00; Su off")
        == "Mon–Fri: 9 am to 9 pm; Sat: 9 am to 5 pm; Sun: closed"
    )
    assert pharmacies.format_hours("Mo-Fr 09:00-13:00,14:00-18:30") == "Mon–Fri: 9 am to 1 pm and 2 pm to 6:30 pm"
    assert pharmacies.format_hours("Mo-Su 00:00-24:00") == "Mon–Sun: open 24 hours"


def test_unusual_or_missing_hours_are_left_out_not_guessed():
    assert pharmacies.format_hours(None) is None
    assert pharmacies.format_hours("") is None
    assert pharmacies.format_hours("sunrise-sunset") is None
    assert pharmacies.format_hours("Mo-Fr 25:00-99:00") is None


def test_parse_orders_by_distance_and_drops_anything_outside_the_radius():
    elements = [
        element("node", 1, "Near", 42.3610, -71.0950),
        element("node", 2, "Mid", 42.3800, -71.0942),
        element("way", 3, "Far", 42.4500, -71.0942),
    ]
    within_1, total_1 = pharmacies.parse_pharmacies(elements, *HERE, miles=1)
    within_10, _ = pharmacies.parse_pharmacies(elements, *HERE, miles=10)
    assert [p.name for p in within_1] == ["Near"] and total_1 == 1
    assert [p.name for p in within_10] == ["Near", "Mid", "Far"]
    assert within_10[0].distance_miles < within_10[1].distance_miles < within_10[2].distance_miles


def test_parse_reads_address_phone_hours_and_whether_it_fills_prescriptions(fake_overpass):
    results, _ = pharmacies.parse_pharmacies(fake_overpass("q"), *HERE, miles=10)
    corner = next(p for p in results if p.name == "Corner Pharmacy")
    assert corner.address == "12 Main Street, Cambridge, MA 02139"
    assert corner.phone == "+1 617 555 0100"
    assert corner.hours.startswith("Mon–Fri: 9 am to 9 pm")
    assert corner.fills_prescriptions is True
    late = next(p for p in results if p.name == "Late Night Pharmacy")
    assert late.fills_prescriptions is None  # the map does not say, so we do not guess


def test_one_store_mapped_twice_is_shown_once_with_the_richer_entry():
    elements = [
        element("node", 1, "Twin Pharmacy", 42.3610, -71.0950),
        element("way", 2, "Twin Pharmacy", 42.36102, -71.09502, phone="+1 617 555 0199",
                opening_hours="Mo-Su 08:00-21:00"),
    ]
    results, total = pharmacies.parse_pharmacies(elements, *HERE, miles=1)
    assert total == 1 and results[0].phone == "+1 617 555 0199"


def test_nearby_endpoint_returns_pharmacies_nearest_first(fake_overpass):
    body = client.get("/pharmacies/nearby", params={"lat": HERE[0], "lon": HERE[1], "miles": 10}).json()
    names = [p["name"] for p in body["results"]]
    assert names == ["Corner Pharmacy", "Late Night Pharmacy", "Far Away Drugs"]
    assert body["radius_miles"] == 10 and body["total_found"] == 3
    assert "cannot see what any pharmacy has in stock" in body["notice"]
    assert all(p["distance_miles"] <= 10.02 for p in body["results"])


def test_smaller_radius_returns_fewer_pharmacies(fake_overpass):
    one = client.get("/pharmacies/nearby", params={"lat": HERE[0], "lon": HERE[1], "miles": 1}).json()
    assert [p["name"] for p in one["results"]] == ["Corner Pharmacy", "Late Night Pharmacy"]


def test_map_data_is_cached_but_each_person_gets_distances_from_their_own_spot(fake_overpass):
    first = client.get("/pharmacies/nearby", params={"lat": 42.3601, "lon": -71.0942, "miles": 10}).json()
    second = client.get("/pharmacies/nearby", params={"lat": 42.3604, "lon": -71.0944, "miles": 10}).json()
    assert len(fake_overpass.calls) == 1  # one lookup shared
    assert second["lat"] == 42.3604 and second["lon"] == -71.0944  # never the other person's location
    assert first["results"][0]["distance_miles"] != 0 or second["results"][0]["distance_miles"] != 0


def test_bad_locations_and_radii_are_rejected():
    for params in (
        {"lat": 200, "lon": -71, "miles": 5},
        {"lat": 42, "lon": -300, "miles": 5},
        {"lat": 42, "lon": -71, "miles": 100},
        {"lat": 42, "lon": -71, "miles": 0},
        {"lat": 42},
    ):
        assert client.get("/pharmacies/nearby", params=params).status_code == 422, params


def test_map_service_trouble_gives_a_friendly_error(monkeypatch):
    def broken(_query):
        raise pharmacies.PharmacyLookupError("The map service is busy right now.")

    monkeypatch.setattr(pharmacies, "_run_overpass", broken)
    response = client.get("/pharmacies/nearby", params={"lat": HERE[0], "lon": HERE[1], "miles": 5})
    assert response.status_code == 502
    assert "try again" in response.json()["detail"].lower()


def test_geocode_turns_a_zip_code_into_points(monkeypatch):
    monkeypatch.setattr(
        pharmacies, "_run_nominatim",
        lambda text: [{"display_name": "02139, Cambridge, Massachusetts, United States", "lat": "42.36", "lon": "-71.10"}],
    )
    body = client.get("/geocode", params={"q": "02139"}).json()
    assert body["matches"] == [{"label": "02139, Cambridge, Massachusetts, United States", "lat": 42.36, "lon": -71.10}]
    assert client.get("/geocode", params={"q": "ab"}).status_code == 422


def test_a_missing_zip_code_is_never_printed_as_none():
    results, _ = pharmacies.parse_pharmacies(
        [element("node", 1, "No Zip", 42.3610, -71.0950, **{"addr:street": "Medford Street", "addr:city": "Somerville"})],
        *HERE, miles=1,
    )
    assert results[0].address == "Medford Street, Somerville"
    assert "None" not in results[0].address
    only_zip = pharmacies.parse_pharmacies(
        [element("node", 2, "Zip Only", 42.3610, -71.0950, **{"addr:postcode": "02139"})], *HERE, miles=1
    )[0][0]
    assert only_zip.address == "02139"


def test_the_map_service_is_retried_once_before_giving_up(monkeypatch):
    attempts = []

    class Ok:
        def raise_for_status(self):
            return None

        def json(self):
            return {"elements": [{"type": "node", "id": 1, "lat": 42.36, "lon": -71.09, "tags": {"name": "Retry Pharmacy"}}]}

    def flaky(url, **_kwargs):
        attempts.append(url)
        if len(attempts) <= len(pharmacies.OVERPASS_ENDPOINTS):
            raise pharmacies.httpx.ConnectError("busy")  # every server fails on the first pass
        return Ok()

    monkeypatch.setattr(pharmacies.httpx, "post", flaky)
    monkeypatch.setattr(pharmacies.time, "sleep", lambda _s: None)
    elements = pharmacies._run_overpass("query")
    assert elements[0]["tags"]["name"] == "Retry Pharmacy"
    assert len(attempts) == len(pharmacies.OVERPASS_ENDPOINTS) + 1
