"""Rank drugs associated with a searched condition.

Scoring is intentionally simple: exact/alias/substring matches on condition
names, then indication text. This is not a clinical ranking.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session, selectinload

from app.models import Indication

TOKEN_RE = re.compile(r"[a-z0-9]+")


def normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())


def tokenize(value: str) -> set[str]:
    return set(TOKEN_RE.findall(value.casefold()))


@dataclass
class RankedHit:
    id: int
    drug_name: str
    rxnorm_id: str | None
    indication_snippet: str
    matched_condition: str | None
    source: str
    score: float


def score_indication(
    query: str,
    condition_name: str | None,
    aliases: list[str],
    raw_text: str,
) -> float:
    q = normalize_text(query)
    if not q:
        return 0.0

    cond = normalize_text(condition_name or "")
    alias_norms = [normalize_text(a) for a in aliases]
    raw = normalize_text(raw_text)
    q_tokens = tokenize(q)

    score = 0.0
    if cond and q == cond:
        score = 100.0
    elif q in alias_norms:
        score = 92.0
    elif cond and (cond.startswith(q) or q.startswith(cond)):
        score = 82.0
    elif any(a.startswith(q) or q.startswith(a) for a in alias_norms if a):
        score = 78.0
    elif cond and q in cond:
        score = 72.0
    elif any(q in a for a in alias_norms if a):
        score = 68.0
    elif q in raw:
        score = 54.0
    else:
        haystack = tokenize(" ".join([cond, *alias_norms, raw]))
        overlap = q_tokens & haystack
        if not overlap:
            return 0.0
        # Require most query tokens so "type 2" does not flood unrelated rows.
        if len(overlap) < max(1, len(q_tokens) - 1):
            return 0.0
        score = 24.0 + (10.0 * len(overlap))

    if q in raw:
        score += 4.0
    return score


def suggest_drugs(session: Session, query: str, limit: int = 20) -> list[RankedHit]:
    rows = session.query(Indication).options(
        selectinload(Indication.drug),
        selectinload(Indication.condition),
    ).all()

    best: dict[str, RankedHit] = {}
    for row in rows:
        aliases: list[str] = []
        condition_name = None
        if row.condition is not None:
            condition_name = row.condition.name
            aliases = json.loads(row.condition.aliases_json or "[]")
        score = score_indication(query, condition_name, aliases, row.raw_text)
        if score <= 0:
            continue
        hit = RankedHit(
            id=row.drug.id,
            drug_name=row.drug.name,
            rxnorm_id=row.drug.rxnorm_id,
            indication_snippet=row.raw_text,
            matched_condition=condition_name,
            source=row.source,
            score=round(score, 2),
        )
        prior = best.get(hit.drug_name)
        if prior is None or hit.score > prior.score:
            best[hit.drug_name] = hit

    ranked = sorted(best.values(), key=lambda h: (-h.score, h.drug_name.casefold()))
    return ranked[:limit]
