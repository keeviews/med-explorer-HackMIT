"""Map FHIR / MyChart medication lists onto seed drugs.

Live MyChart access uses SMART on FHIR (patient login at Epic). This module
does not collect MyChart passwords. Without an Epic client id, the demo bundle
lets local development fill a current-meds list the same way a successful
SMART read would.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from app.config import (
    EPIC_AUTHORIZE_URL,
    EPIC_CLIENT_ID,
    EPIC_FHIR_BASE,
    EPIC_REDIRECT_URI,
)
from app.models import Drug
from app.suggest import normalize_text

RXNORM_SYSTEMS = {
    "http://www.nlm.nih.gov/research/umls/rxnorm",
    "http://www.nlm.nih.gov/research/umls/rxnorm/",
}

# Synthetic FHIR-style rows. Not a real patient chart.
DEMO_MEDICATIONS = [
    {"name": "Lisinopril 10 MG Oral Tablet", "rxnorm_id": "29046"},
    {"name": "Metformin hydrochloride 500 MG Oral Tablet", "rxnorm_id": "6809"},
    {"name": "Omeprazole 20 MG Delayed Release Oral Capsule", "rxnorm_id": "7646"},
    {"name": "Loratadine 10 MG Oral Tablet", "rxnorm_id": None},
    {"name": "Atorvastatin 40 MG Oral Tablet", "rxnorm_id": "83367"},
]

SMART_SCOPES = (
    "openid fhirUser launch/patient patient/Patient.read "
    "patient/MedicationRequest.read patient/MedicationStatement.read"
)

_STRENGTH = re.compile(r"\b\d+(\.\d+)?\s*(mg|mcg|g|ml|%|units?)\b", re.I)


def mychart_is_configured() -> bool:
    return bool(EPIC_CLIENT_ID)


def authorize_url(state: str, code_challenge: str) -> str | None:
    if not mychart_is_configured():
        return None
    query = urlencode(
        {
            "response_type": "code",
            "client_id": EPIC_CLIENT_ID,
            "redirect_uri": EPIC_REDIRECT_URI,
            "scope": SMART_SCOPES,
            "state": state,
            "aud": EPIC_FHIR_BASE,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{EPIC_AUTHORIZE_URL}?{query}"


def extract_medications_from_bundle(bundle: dict[str, Any]) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []
    for entry in bundle.get("entry") or []:
        resource = entry.get("resource") or {}
        if resource.get("resourceType") not in ("MedicationRequest", "MedicationStatement"):
            continue
        concept = (
            resource.get("medicationCodeableConcept")
            or (resource.get("medication") or {}).get("concept")
            or {}
        )
        name = concept.get("text") or resource.get("medicationReference", {}).get("display")
        rxnorm_id = None
        for coding in concept.get("coding") or []:
            system = str(coding.get("system") or "").rstrip("/")
            if system in {item.rstrip("/") for item in RXNORM_SYSTEMS} and coding.get("code"):
                rxnorm_id = str(coding["code"])
                name = name or coding.get("display")
                break
        if not name:
            continue
        rows.append({"name": str(name), "rxnorm_id": rxnorm_id})
    return rows


def match_seed_drug(session: Session, name: str, rxnorm_id: str | None) -> Drug | None:
    if rxnorm_id:
        row = session.query(Drug).filter(Drug.rxnorm_id == str(rxnorm_id)).one_or_none()
        if row is not None:
            return row
    needle = _core_name(name)
    if len(needle) < 4:
        return None
    best: Drug | None = None
    best_len = 0
    for drug in session.query(Drug).all():
        seed = _core_name(drug.name)
        if not seed:
            continue
        if needle == seed or seed in needle or needle in seed:
            if len(seed) > best_len:
                best = drug
                best_len = len(seed)
    return best if best_len >= 5 else None


def map_medications(
    session: Session,
    medications: list[dict[str, str | None]],
    source: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    mapped: list[dict[str, Any]] = []
    unmapped: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    seen_unmapped: set[str] = set()
    for item in medications:
        fhir_name = str(item.get("name") or "").strip()
        rxnorm_id = item.get("rxnorm_id")
        if not fhir_name:
            continue
        drug = match_seed_drug(session, fhir_name, rxnorm_id if isinstance(rxnorm_id, str) else None)
        if drug is None:
            key = fhir_name.casefold()
            if key in seen_unmapped:
                continue
            seen_unmapped.add(key)
            unmapped.append(
                {
                    "name": fhir_name,
                    "rxnorm_id": rxnorm_id,
                    "source": source,
                }
            )
            continue
        if drug.id in seen_ids:
            continue
        seen_ids.add(drug.id)
        mapped.append(
            {
                "id": drug.id,
                "name": drug.name,
                "rxnorm_id": drug.rxnorm_id,
                "fhir_name": fhir_name,
                "source": source,
            }
        )
    return mapped, unmapped


def _core_name(value: str) -> str:
    text = normalize_text(value)
    text = text.split("(")[0]
    text = _STRENGTH.sub(" ", text)
    for noise in (
        "oral tablet",
        "oral capsule",
        "delayed release",
        "hydrochloride",
        "nasal spray",
        "tablet",
        "capsule",
    ):
        text = text.replace(noise, " ")
    return normalize_text(text)


def demo_bundle() -> dict[str, Any]:
    entries = []
    for item in DEMO_MEDICATIONS:
        coding = []
        if item["rxnorm_id"]:
            coding.append(
                {
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": item["rxnorm_id"],
                    "display": item["name"],
                }
            )
        entries.append(
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "status": "active",
                    "intent": "order",
                    "medicationCodeableConcept": {
                        "text": item["name"],
                        "coding": coding,
                    },
                }
            }
        )
    return {"resourceType": "Bundle", "type": "collection", "entry": entries}


def setup_message() -> str:
    return (
        "Live MyChart import uses SMART on FHIR: the patient signs in at Epic, "
        "not by typing a MyChart password into DiscussMeds. Register a "
        "patient-facing app at https://fhir.epic.com/ then set EPIC_CLIENT_ID "
        f"and EPIC_REDIRECT_URI (callback {EPIC_REDIRECT_URI}). A health system "
        "must also enable the app. Until then, use the demo FHIR import."
    )
