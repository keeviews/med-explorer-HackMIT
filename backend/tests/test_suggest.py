import json
from pathlib import Path

from app.suggest import score_indication


def test_exact_condition_outranks_unrelated_text():
    exact = score_indication("hypertension", "Hypertension", ["high blood pressure"], "Hypertension")
    miss = score_indication("hypertension", "Migraine", ["migraines"], "Migraine")
    assert exact > 90
    assert miss == 0


def test_alias_match():
    score = score_indication("t2dm", "Type 2 diabetes mellitus", ["t2dm", "type 2 diabetes"], "Type 2 diabetes mellitus")
    assert score >= 90


def test_seed_json_is_internally_consistent():
    payload = json.loads(
        (Path(__file__).resolve().parents[2] / "data" / "seed.json").read_text(encoding="utf-8")
    )
    drug_names = {d["name"] for d in payload["drugs"]}
    assert len(drug_names) == len(payload["drugs"]), "drug names must be unique"
    condition_names = {c["name"] for c in payload["conditions"]}
    rules = payload["combination_rules"]
    assert rules["duplicate_class_urgent"]
    assert rules["pairs"]
    for row in payload["drugs"]:
        assert row["name"].strip()
        assert row.get("drug_class")
        assert row.get("route")
        assert row.get("rx_otc")
        assert isinstance(row.get("common_side_effects"), list)
        assert len(row["common_side_effects"]) >= 2
        assert row.get("typical_use_note")
        assert row.get("monitoring_note")
    for row in payload["indications"]:
        assert row["drug"] in drug_names
        assert row["condition"] in condition_names
        assert row["raw_text"].strip()
        assert row["source"].startswith("openfda:label:")
        assert row["source_url"].startswith("https://dailymed.nlm.nih.gov/")


def test_every_condition_is_used_and_every_drug_has_a_use():
    payload = json.loads(
        (Path(__file__).resolve().parents[2] / "data" / "seed.json").read_text(encoding="utf-8")
    )
    used_conditions = {row["condition"] for row in payload["indications"]}
    used_drugs = {row["drug"] for row in payload["indications"]}
    assert {c["name"] for c in payload["conditions"]} == used_conditions
    assert {d["name"] for d in payload["drugs"]} == used_drugs


def test_wording_shown_to_people_is_plain_language():
    payload = json.loads(
        (Path(__file__).resolve().parents[2] / "data" / "seed.json").read_text(encoding="utf-8")
    )
    shown = []
    for drug in payload["drugs"]:
        shown += [drug["typical_use_note"], drug["monitoring_note"], *drug["common_side_effects"]]
    shown += [row["raw_text"] for row in payload["indications"]]
    banned = ("seed", "illustrative", "indicated for", "contraindicat", "concomitant")
    for text in shown:
        assert not any(word in text.lower() for word in banned), text
        assert len(text) < 320, f"too long to read comfortably: {text!r}"


def test_original_drugs_keep_their_ids():
    """Saved medicine lists in people's browsers store drug ids, so the first 23 must never move."""
    payload = json.loads(
        (Path(__file__).resolve().parents[2] / "data" / "seed.json").read_text(encoding="utf-8")
    )
    original = [
        "Lisinopril", "Amlodipine", "Hydrochlorothiazide", "Losartan", "Metoprolol", "Propranolol",
        "Metformin", "Empagliflozin", "Semaglutide", "Glipizide", "Sitagliptin", "Cetirizine",
        "Loratadine", "Fluticasone (nasal)", "Montelukast", "Omeprazole", "Pantoprazole",
        "Famotidine", "Esomeprazole", "Sumatriptan", "Rizatriptan", "Topiramate", "Ubrogepant",
    ]
    assert [d["name"] for d in payload["drugs"][:23]] == original