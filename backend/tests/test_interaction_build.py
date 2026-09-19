"""Tests for the interaction-finding helpers in scripts/build_seed_from_openfda.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import build_seed_from_openfda as build  # noqa: E402


def test_whole_words_only_so_omeprazole_does_not_match_esomeprazole():
    pattern = build.term_regex(["omeprazole"])
    assert pattern.search("Do not combine with omeprazole.")
    assert not pattern.search("Esomeprazole may raise levels.")


def test_plural_class_names_match():
    assert build.term_regex(["NSAID"]).search("Avoid NSAIDs and aspirin.")


def test_reference_markers_are_removed_but_the_wording_is_kept():
    cleaned = build.clean_label_text("Monitor INR ( 7.1 , 12.3 ) closely [see Warnings and Precautions (5.1)] .")
    assert cleaned == "Monitor INR closely."


def test_section_headings_are_stripped_from_quotes():
    sentences = build.split_sentences("7 DRUG INTERACTIONS Do not exceed 20 mg daily of simvastatin.")
    assert sentences == ["Do not exceed 20 mg daily of simvastatin."]


def test_reassuring_no_effect_sentences_are_recognised():
    assert build.NO_INTERACTION.search("Tadalafil had no significant effect on exposure to warfarin.")
    assert not build.NO_INTERACTION.search("Concomitant use increases the risk of bleeding.")


def test_a_curated_rule_can_raise_severity_but_never_lower_it():
    nsaid = {"name": "Ibuprofen", "class": "NSAID (anti-inflammatory pain reliever)"}
    thinner = {"name": "Warfarin", "class": "Blood thinner (anticoagulant)"}
    assert build.plain_note(nsaid, thinner, "discuss")[2] == "urgent_seed"
    ppi = {"name": "Omeprazole", "class": "Proton pump inhibitor"}
    levo = {"name": "Levothyroxine", "class": "Thyroid hormone replacement"}
    assert build.plain_note(ppi, levo, "discuss")[2] == "discuss"
    assert build.plain_note(ppi, levo, "urgent_seed")[2] == "urgent_seed"


def test_every_quote_in_seed_json_is_readable_and_bounded():
    import json

    seed = json.loads((Path(__file__).resolve().parents[2] / "data" / "seed.json").read_text(encoding="utf-8"))
    names = {d["name"] for d in seed["drugs"]}
    assert seed["interactions"]
    for fact in seed["interactions"]:
        assert fact["drug"] in names and fact["other"] in names and fact["drug"] != fact["other"]
        assert 20 <= len(fact["quote"]) <= build.MAX_QUOTE_CHARS + 60
        assert fact["severity"] in ("urgent_seed", "discuss")
        assert fact["source"].startswith("openfda:label:")
        assert fact["source_url"].startswith("https://dailymed.nlm.nih.gov/")
        assert "( 7" not in fact["quote"]  # cross-reference markers are cleaned out