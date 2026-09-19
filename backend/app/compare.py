"""Load structured compare/detail payloads. This is not clinical ranking."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session, selectinload

from app.disclaimer import DATA_LABEL
from app.models import Drug, Indication


def parse_id_list(raw: str) -> list[int]:
    values: list[int] = []
    seen: set[int] = set()
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        drug_id = int(token)
        if drug_id in seen:
            continue
        seen.add(drug_id)
        values.append(drug_id)
    return values


def parse_name_list(raw: str) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        key = token.casefold()
        if key in seen:
            continue
        seen.add(key)
        values.append(token)
    return values


def serialize_drug(drug: Drug) -> dict:
    linked = sorted(
        {
            row.condition.name
            for row in drug.indications
            if row.condition is not None
        }
    )
    try:
        side_effects = json.loads(drug.side_effects_json or "[]")
    except json.JSONDecodeError:
        side_effects = []
    if not isinstance(side_effects, list):
        side_effects = []
    return {
        "id": drug.id,
        "drug_name": drug.name,
        "rxnorm_id": drug.rxnorm_id,
        "drug_class": drug.drug_class,
        "route": drug.route,
        "rx_otc": drug.rx_otc,
        "common_side_effects": [str(item) for item in side_effects],
        "typical_use_note": drug.typical_use_note,
        "monitoring_note": drug.monitoring_note,
        "linked_conditions": linked,
        "data_label": DATA_LABEL,
    }


def load_drugs_by_ids(session: Session, ids: list[int]) -> tuple[list[Drug], list[int]]:
    rows = (
        session.query(Drug)
        .options(selectinload(Drug.indications).selectinload(Indication.condition))
        .filter(Drug.id.in_(ids))
        .all()
    )
    by_id = {row.id: row for row in rows}
    found = [by_id[i] for i in ids if i in by_id]
    missing = [i for i in ids if i not in by_id]
    return found, missing


def load_drugs_by_names(session: Session, names: list[str]) -> tuple[list[Drug], list[str]]:
    rows = (
        session.query(Drug)
        .options(selectinload(Drug.indications).selectinload(Indication.condition))
        .all()
    )
    by_key = {row.name.casefold(): row for row in rows}
    found: list[Drug] = []
    missing: list[str] = []
    for name in names:
        row = by_key.get(name.casefold())
        if row is None:
            missing.append(name)
        else:
            found.append(row)
    return found, missing
