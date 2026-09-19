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
    payload = json.loads((Path(__file__).resolve().parents[2] / "data" / "seed.json").read_text())
    drug_names = {d["name"] for d in payload["drugs"]}
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
        assert row["source"] == "seed:illustrative"
