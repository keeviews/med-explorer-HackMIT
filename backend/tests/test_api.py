from fastapi.testclient import TestClient

from app.disclaimer import DATA_LABEL, DISCLAIMER
from app.main import app

client = TestClient(app)


def test_health_ok():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["seeded"] is True


def test_suggest_requires_query():
    response = client.get("/suggest")
    assert response.status_code == 422


def test_resolve_browser_ocr_text_returns_a_confirmable_match():
    response = client.post(
        "/medicines/resolve",
        json={"raw_text": "Lisinopril 10 mg tablet\nTake one tablet daily"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "ocr"
    assert body["candidates"] == [
        {
            "id": 1,
            "name": "Lisinopril",
            "strength": "10 mg",
            "form": "tablet",
            "confidence": 0.99,
        }
    ]


def test_suggest_hypertension_returns_ranked_drugs_and_disclaimer():
    response = client.get("/suggest", params={"q": "hypertension", "limit": 20})
    assert response.status_code == 200
    body = response.json()
    assert body["disclaimer"] == DISCLAIMER
    assert "not medical advice" in body["disclaimer"].casefold()
    assert body["result_count"] >= 5
    names = [row["drug_name"] for row in body["results"]]
    assert "Lisinopril" in names
    assert "Amlodipine" in names
    assert all(isinstance(row["id"], int) and row["id"] > 0 for row in body["results"])
    assert all(row["source"].startswith("openfda:label:") for row in body["results"])
    assert all(row["data_label"] == DATA_LABEL for row in body["results"])


def test_suggest_alias_hay_fever():
    response = client.get("/suggest", params={"q": "hay fever"})
    assert response.status_code == 200
    names = [row["drug_name"] for row in response.json()["results"]]
    assert "Cetirizine" in names
    assert "Loratadine" in names


def test_suggest_empty_unknown_condition():
    response = client.get("/suggest", params={"q": "xyzzy-unknown-condition"})
    assert response.status_code == 200
    body = response.json()
    assert body["disclaimer"] == DISCLAIMER
    assert body["result_count"] == 0
    assert body["results"] == []


def test_conditions_list_includes_seeded_names():
    response = client.get("/conditions")
    assert response.status_code == 200
    names = [row["name"] for row in response.json()["conditions"]]
    assert "Hypertension" in names
    assert "Migraine" in names


def test_compare_two_drugs_by_id_includes_disclaimer_and_seed_fields():
    suggest = client.get("/suggest", params={"q": "hypertension"}).json()
    by_name = {row["drug_name"]: row["id"] for row in suggest["results"]}
    lisinopril = by_name["Lisinopril"]
    amlodipine = by_name["Amlodipine"]
    response = client.get("/compare", params={"ids": f"{lisinopril},{amlodipine}"})
    assert response.status_code == 200
    body = response.json()
    assert body["disclaimer"] == DISCLAIMER
    assert "not a ranking" in body["compare_note"].casefold()
    assert "not a “best option" in body["compare_note"].casefold() or "not a \"best option" in body["compare_note"].casefold()
    assert body["result_count"] == 2
    assert body["compare_limit"] == 4
    names = [row["drug_name"] for row in body["drugs"]]
    assert names == ["Lisinopril", "Amlodipine"]
    lisinopril_row = body["drugs"][0]
    assert lisinopril_row["drug_class"]
    assert lisinopril_row["route"] == "oral"
    assert lisinopril_row["rx_otc"] == "Rx"
    assert "dry cough" in lisinopril_row["common_side_effects"]
    assert lisinopril_row["typical_use_note"]
    assert lisinopril_row["monitoring_note"]
    assert "Hypertension" in lisinopril_row["linked_conditions"]
    assert lisinopril_row["data_label"] == DATA_LABEL
    assert "FDA" in body["data_notice"]


def test_compare_by_name_and_unknown_id():
    ok = client.get("/compare", params={"names": "Omeprazole,Famotidine"})
    assert ok.status_code == 200
    assert [row["drug_name"] for row in ok.json()["drugs"]] == ["Omeprazole", "Famotidine"]
    missing = client.get("/compare", params={"ids": "999999"})
    assert missing.status_code == 404


def test_compare_rejects_more_than_four():
    suggest = client.get("/suggest", params={"q": "hypertension"}).json()
    ids = [str(row["id"]) for row in suggest["results"][:5]]
    response = client.get("/compare", params={"ids": ",".join(ids)})
    assert response.status_code == 422


def test_drug_detail_endpoint():
    suggest = client.get("/suggest", params={"q": "migraine"}).json()
    drug_id = next(row["id"] for row in suggest["results"] if row["drug_name"] == "Sumatriptan")
    response = client.get(f"/drugs/{drug_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["disclaimer"] == DISCLAIMER
    assert body["drug"]["drug_name"] == "Sumatriptan"
    assert body["drug"]["common_side_effects"]


def test_compare_highlights_similar_fields_without_urgent_flag():
    body = client.get("/compare", params={"names": "Lisinopril,Amlodipine"}).json()
    similar_fields = {row["field"] for row in body["similarities"]}
    assert "route" in similar_fields
    assert "linked_conditions" in similar_fields
    assert all(row["code"] != "duplicate_class" for row in body["alerts"])
    assert not any(row["severity"] == "urgent_seed" for row in body["alerts"])


def test_compare_flags_ace_inhibitor_with_arb_in_red_category():
    body = client.get("/compare", params={"names": "Lisinopril,Losartan"}).json()
    assert body["disclaimer"] == DISCLAIMER
    urgent = [row for row in body["alerts"] if row["severity"] == "urgent_seed"]
    assert urgent
    assert any("ACE" in row["title"] or "ARB" in row["title"] for row in urgent)
    assert "cannot tell you to stop" in body["talk_with_clinician"].casefold()
    assert body["overlap_summary"]


def test_compare_flags_two_ppis_as_same_class_overlap():
    body = client.get("/compare", params={"names": "Omeprazole,Esomeprazole"}).json()
    assert any(row["code"] == "duplicate_class" for row in body["alerts"])
    assert any(row["severity"] == "urgent_seed" for row in body["alerts"])


def test_review_allows_more_than_compare_cap():
    names = "Lisinopril,Amlodipine,Losartan,Metformin,Omeprazole"
    compare = client.get("/compare", params={"names": names})
    assert compare.status_code == 422
    review = client.get("/review", params={"names": names})
    assert review.status_code == 200
    assert review.json()["result_count"] == 5


def test_mychart_status_is_unconfigured_by_default():
    response = client.get("/integrations/mychart")
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is False
    assert body["authorize_url"] is None
    assert "SMART on FHIR" in body["setup_note"]
    assert body["demo_available"] is True
    assert body["disclaimer"] == DISCLAIMER


def test_mychart_demo_import_maps_seed_drugs_and_keeps_unmapped():
    response = client.get("/integrations/mychart/demo")
    assert response.status_code == 200
    body = response.json()
    names = {row["name"] for row in body["mapped"]}
    assert "Lisinopril" in names
    assert "Metformin" in names
    assert "Omeprazole" in names
    assert "Loratadine" in names
    unmapped_names = {row["name"] for row in body["unmapped"]}
    assert "Atorvastatin" in names  # now in the dataset, so it maps
    assert any("Fish Oil" in name for name in unmapped_names)
    assert body["source"] == "fhir_demo"
    assert body["mapped_count"] >= 4
    assert body["unmapped_count"] >= 1


def test_search_finds_real_drugs_for_new_conditions():
    for query, expected in (
        ("high cholesterol", "Atorvastatin"),
        ("depression", "Sertraline"),
        ("infection", "Amoxicillin"),
        ("asthma", "Albuterol"),
        ("blood thinner", "Warfarin"),
        ("hypothyroidism", "Levothyroxine"),
    ):
        body = client.get("/suggest", params={"q": query, "limit": 50}).json()
        names = [row["drug_name"] for row in body["results"]]
        assert expected in names, f"{expected} missing for {query!r}: {names}"


def test_rx_otc_comes_from_fda_labels():
    body = client.get("/compare", params={"names": "Ibuprofen,Lisinopril,Acetaminophen"}).json()
    by_name = {row["drug_name"]: row["rx_otc"] for row in body["drugs"]}
    assert by_name["Lisinopril"] == "Rx"
    assert by_name["Acetaminophen"] == "OTC"
    assert by_name["Ibuprofen"].startswith("OTC or Rx")


def test_new_classes_trigger_duplicate_class_flags():
    for pair in ("Atorvastatin,Rosuvastatin", "Ibuprofen,Naproxen", "Sertraline,Escitalopram", "Warfarin,Apixaban"):
        body = client.get("/compare", params={"names": pair}).json()
        assert any(row["code"] == "duplicate_class" for row in body["alerts"]), pair


def test_side_effect_overlap_is_still_highlighted():
    body = client.get("/compare", params={"names": "Cetirizine,Loratadine"}).json()
    overlaps = [row for row in body["similarities"] if row["field"] == "side_effects"]
    assert any(row["value"] == "drowsiness" for row in overlaps)


# ---------------------------------------------------------------------------
# Interaction flags: every flag is backed by a real FDA label sentence
# ---------------------------------------------------------------------------
def _label_alerts(names):
    body = client.get("/review", params={"names": names}).json()
    return [row for row in body["alerts"] if row["code"] == "label_interaction"]


def test_warfarin_and_ibuprofen_are_flagged_red_with_label_proof():
    alerts = _label_alerts("Warfarin,Ibuprofen")
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["severity"] == "urgent_seed"
    assert "bleeding" in alert["detail"].lower()
    assert alert["evidence"]
    quotes = " ".join(item["quote"] for item in alert["evidence"]).lower()
    assert "warfarin" in quotes or "anticoagulant" in quotes
    assert all(item["source_url"].startswith("https://dailymed.nlm.nih.gov/") for item in alert["evidence"])


def test_opioid_with_benzodiazepine_is_flagged_red():
    alerts = _label_alerts("Tramadol,Alprazolam")
    assert alerts and alerts[0]["severity"] == "urgent_seed"
    assert "breathing" in alerts[0]["detail"].lower()


def test_clopidogrel_with_omeprazole_quotes_the_avoid_warning():
    alerts = _label_alerts("Clopidogrel,Omeprazole")
    assert alerts and alerts[0]["severity"] == "urgent_seed"
    assert any("avoid" in item["quote"].lower() for item in alerts[0]["evidence"])


def test_other_known_pairs_are_flagged():
    for names in ("Sertraline,Sumatriptan", "Lisinopril,Spironolactone", "Levothyroxine,Omeprazole", "Simvastatin,Amlodipine"):
        assert _label_alerts(names), names


def test_unrelated_medicines_and_no_effect_sentences_are_not_flagged():
    # Metformin and cetirizine never mention each other. The tadalafil label says it had NO effect on
    # warfarin, which is reassurance, not a warning, so it must not become a flag.
    assert not _label_alerts("Metformin,Cetirizine")
    assert not _label_alerts("Tadalafil,Warfarin")


def test_every_flag_is_readable_and_has_proof():
    names = "Warfarin,Ibuprofen,Sertraline,Lisinopril,Metformin,Amlodipine,Simvastatin,Aspirin,Omeprazole,Tramadol,Alprazolam"
    for alert in _label_alerts(names):
        assert alert["title"].strip() and alert["detail"].strip()
        assert "seed" not in alert["detail"].lower()
        assert 1 <= len(alert["evidence"]) <= 3
        for item in alert["evidence"]:
            assert item["quote"].strip()
            assert item["section"]
            assert item["source_url"].startswith("https://dailymed.nlm.nih.gov/")


def test_compare_endpoint_also_returns_label_flags():
    body = client.get("/compare", params={"names": "Warfarin,Ibuprofen"}).json()
    assert any(row["code"] == "label_interaction" for row in body["alerts"])
    assert body["overlap_summary"]