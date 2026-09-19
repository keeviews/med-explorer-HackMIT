"""Match browser-extracted medicine-label text against the local dataset."""

from __future__ import annotations

from collections.abc import Iterable
from difflib import SequenceMatcher
import re
from typing import Any

from app.schemas import ScanCandidate

_STRENGTH = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mcg|mg|g|mL|ml|units?)\b", re.IGNORECASE)
_FORMS = re.compile(r"\b(tablet|tab|capsule|cap|solution|suspension|cream|ointment|inhaler|spray)\b", re.IGNORECASE)


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _candidate_score(drug_name: str, lines: list[str]) -> float:
    target = _normalise(drug_name)
    best = 0.0
    for line in lines:
        source = _normalise(line)
        if target and target in source:
            best = max(best, 0.99)
        else:
            best = max(best, SequenceMatcher(None, target, source).ratio())
    return best


def resolve_text(raw_text: str, drugs: Iterable[Any]) -> list[ScanCandidate]:
    """Return only credible local-dataset matches for OCR text from a browser."""
    lines = [line for line in raw_text.splitlines() if line.strip()]
    strength_match = _STRENGTH.search(raw_text)
    form_match = _FORMS.search(raw_text)
    candidates = []
    for drug in drugs:
        confidence = _candidate_score(drug.name, lines)
        if confidence >= 0.55:
            candidates.append(
                ScanCandidate(
                    id=drug.id,
                    name=drug.name,
                    strength=strength_match.group(0) if strength_match else None,
                    form=form_match.group(0).lower() if form_match else None,
                    confidence=round(confidence, 2),
                )
            )
    candidates.sort(key=lambda candidate: candidate.confidence, reverse=True)
    return candidates[:3]
