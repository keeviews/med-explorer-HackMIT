"""Seed overlap insights for compare / my-list review.

This is not a DDI engine, not deprescribing, and not clinical ranking.
Flags come from data/seed.json combination_rules plus simple same-class checks.
"""

from __future__ import annotations

import json
from collections import defaultdict
from functools import lru_cache
from typing import Any

from app.config import SEED_PATH
from app.disclaimer import TALK_WITH_CLINICIAN

DATA_LABEL = "General overlap rule"


@lru_cache(maxsize=1)
def load_combination_rules() -> dict[str, Any]:
    payload = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    return payload.get("combination_rules") or {}


def _norm(value: str | None) -> str:
    return " ".join((value or "").split()).casefold()


def build_insights(
    details: list[dict[str, Any]], interactions: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    similarities = _similarities(details)
    alerts = _duplicate_class_alerts(details) + _pair_alerts(details) + _label_alerts(details, interactions or [])
    alerts.sort(key=lambda row: row["severity"] != "urgent_seed")  # red first (stable sort)
    overlap_summary = None
    if alerts:
        urgent = [row for row in alerts if row["severity"] == "urgent_seed"]
        if urgent:
            overlap_summary = (
                "Flags marked possible overlap in red. Bring this list to "
                "your clinician — do not stop or cut a medicine based on this screen."
            )
        else:
            overlap_summary = (
                "Notes marked class overlap to discuss. This is not advice "
                "to drop a medicine."
            )
    return {
        "similarities": similarities,
        "alerts": alerts,
        "overlap_summary": overlap_summary,
        "talk_with_clinician": TALK_WITH_CLINICIAN,
        "overlap_note": (
            "Sage = matching fields. Red = combination / duplicate-class "
            "flags, not a complete interaction checker."
        ),
    }


def _similarities(details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(details) < 2:
        return []
    rows: list[dict[str, Any]] = []
    for field, label in (
        ("drug_class", "drug_class"),
        ("route", "route"),
        ("rx_otc", "rx_otc"),
        ("typical_use_note", "typical_use_note"),
    ):
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for drug in details:
            raw = drug.get(field)
            if not isinstance(raw, str) or not raw.strip():
                continue
            buckets[_norm(raw)].append(drug)
        for _key, group in buckets.items():
            if len(group) < 2:
                continue
            value = str(group[0].get(field) or "").strip()
            rows.append(
                {
                    "field": label,
                    "value": value,
                    "drug_ids": [int(d["id"]) for d in group],
                    "drug_names": [str(d["drug_name"]) for d in group],
                }
            )

    condition_buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for drug in details:
        for cond in drug.get("linked_conditions") or []:
            if isinstance(cond, str) and cond.strip():
                condition_buckets[_norm(cond)].append(drug)
    for _key, group in condition_buckets.items():
        unique: list[dict[str, Any]] = []
        seen: set[int] = set()
        for drug in group:
            if drug["id"] in seen:
                continue
            seen.add(int(drug["id"]))
            unique.append(drug)
        if len(unique) < 2:
            continue
        sample = next(
            cond
            for cond in (unique[0].get("linked_conditions") or [])
            if _norm(str(cond)) == _key
        )
        rows.append(
            {
                "field": "linked_conditions",
                "value": str(sample),
                "drug_ids": [int(d["id"]) for d in unique],
                "drug_names": [str(d["drug_name"]) for d in unique],
            }
        )

    effect_buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for drug in details:
        for effect in drug.get("common_side_effects") or []:
            if isinstance(effect, str) and effect.strip():
                effect_buckets[_norm(effect)].append(drug)
    for _key, group in effect_buckets.items():
        unique = []
        seen = set()
        for drug in group:
            if drug["id"] in seen:
                continue
            seen.add(drug["id"])
            unique.append(drug)
        if len(unique) < 2:
            continue
        sample = next(
            effect
            for effect in (unique[0].get("common_side_effects") or [])
            if _norm(str(effect)) == _key
        )
        rows.append(
            {
                "field": "side_effects",
                "value": str(sample),
                "drug_ids": [int(d["id"]) for d in unique],
                "drug_names": [str(d["drug_name"]) for d in unique],
            }
        )
    return rows


def _duplicate_class_alerts(details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rules = load_combination_rules()
    urgent_classes = {
        _norm(name) for name in (rules.get("duplicate_class_urgent") or []) if name
    }
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for drug in details:
        klass = drug.get("drug_class")
        if isinstance(klass, str) and klass.strip():
            buckets[_norm(klass)].append(drug)
    alerts: list[dict[str, Any]] = []
    for key, group in buckets.items():
        if len(group) < 2 or key not in urgent_classes:
            continue
        klass = str(group[0].get("drug_class") or "")
        names = [str(d["drug_name"]) for d in group]
        alerts.append(
            {
                "severity": "urgent_seed",
                "code": "duplicate_class",
                "title": f"More than one {klass} on this list",
                "detail": (
                    f"{_join_names(names)} are in the same drug class. "
                    "That kind of overlap is something to ask a clinician about — "
                    "for example whether you still need each one — not an instruction "
                    "to drop a medicine yourself."
                ),
                "talk_with_clinician": TALK_WITH_CLINICIAN,
                "drug_ids": [int(d["id"]) for d in group],
                "drug_names": names,
                "fields": ["drug_class"],
                "data_label": DATA_LABEL,
            }
        )
    return alerts


def _pair_alerts(details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rules = load_combination_rules()
    alerts: list[dict[str, Any]] = []
    for pair in rules.get("pairs") or []:
        classes = [_norm(c) for c in (pair.get("classes") or []) if c]
        if len(classes) != 2:
            continue
        left = [d for d in details if _norm(str(d.get("drug_class") or "")) == classes[0]]
        right = [d for d in details if _norm(str(d.get("drug_class") or "")) == classes[1]]
        if not left or not right:
            continue
        group = left + right
        names = [str(d["drug_name"]) for d in group]
        severity = pair.get("severity") or "discuss"
        if severity not in ("urgent_seed", "discuss"):
            severity = "discuss"
        alerts.append(
            {
                "severity": severity,
                "code": "class_pair",
                "title": str(pair.get("title") or "Class combination to discuss"),
                "detail": str(pair.get("detail") or TALK_WITH_CLINICIAN),
                "talk_with_clinician": TALK_WITH_CLINICIAN,
                "drug_ids": [int(d["id"]) for d in group],
                "drug_names": names,
                "fields": ["drug_class"],
                "data_label": DATA_LABEL,
            }
        )
    return alerts


def _join_names(names: list[str]) -> str:
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def _label_alerts(details: list[dict[str, Any]], interactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One alert per pair of medicines whose FDA labels mention each other, with the label text as proof."""
    names = {int(d["id"]): str(d["drug_name"]) for d in details}
    grouped: dict[frozenset[int], list[dict[str, Any]]] = defaultdict(list)
    for fact in interactions:
        grouped[frozenset((fact["drug_id"], fact["other_drug_id"]))].append(fact)
    alerts: list[dict[str, Any]] = []
    for pair, rows in grouped.items():
        # Best evidence first: strong warnings, then a named medicine over a whole class, then the shortest.
        rows.sort(key=lambda r: (r["severity"] != "urgent_seed", r["matched_on"] != "name", len(r["quote"])))
        top = rows[0]
        ids = sorted(pair)
        alerts.append(
            {
                "severity": top["severity"],
                "code": "label_interaction",
                "title": top["title"],
                "detail": top["plain"],
                "talk_with_clinician": TALK_WITH_CLINICIAN,
                "drug_ids": ids,
                "drug_names": [names[i] for i in ids],
                "fields": ["drug_class"],
                "data_label": "FDA label",
                "evidence": [
                    {
                        "drug_name": names[row["drug_id"]],
                        "quote": row["quote"],
                        "section": row["section"],
                        "source_url": row["source_url"],
                        "matched_on": row["matched_on"],
                        "matched_term": row["matched_term"],
                    }
                    for row in rows[:3]
                ],
            }
        )
    return alerts
