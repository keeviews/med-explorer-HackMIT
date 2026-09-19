#!/usr/bin/env python3
"""Build data/seed.json from real FDA drug labels (openFDA) plus plain-language wording.

What comes from the FDA (looked up live, cached in data/openfda_cache/):
  - whether the drug is sold over the counter, by prescription, or both
  - the RxNorm ingredient id (from NLM RxNav)
  - the label's DailyMed page and effective date (stored as the source of each row)

What is written by hand (scripts/curated_drugs.py):
  - every sentence a person reads: what it is used for, how it works, common side
    effects and what to ask a clinician about

This script then CHECKS the hand-written claims against the FDA label text
(is the condition mentioned in the label's "indications"? does the label mention
each listed side effect?) and prints anything it cannot confirm, so a person can
fix the wording instead of trusting it blindly.

Usage:
    python scripts/build_seed_from_openfda.py            # fetch (cached) and rewrite data/seed.json
    python scripts/build_seed_from_openfda.py --offline  # use the cache only
    python scripts/build_seed_from_openfda.py --check    # verify only, do not write seed.json

Optional: set OPENFDA_API_KEY (free at open.fda.gov) for higher rate limits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from curated_drugs import (  # noqa: E402
    CLASS_LABEL_TERMS,
    CLASSES,
    COMBINATION_RULES,
    CONDITIONS,
    DRUGS,
    INTERACTION_NOTES,
    LEGACY_DRUG_ORDER,
)

DATA_DIR = ROOT / "data"
SEED_PATH = DATA_DIR / "seed.json"
CACHE_DIR = DATA_DIR / "openfda_cache"

OPENFDA_URL = "https://api.fda.gov/drug/label.json"
RXNAV_URL = "https://rxnav.nlm.nih.gov/REST/rxcui.json"
RXNAV_PROPS_URL = "https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/properties.json"
DAILYMED_URL = "https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid="
RX_TYPE = "HUMAN PRESCRIPTION DRUG"
OTC_TYPE = "HUMAN OTC DRUG"
PAUSE_SECONDS = 0.35  # stays well under openFDA's 240 requests/minute limit

TEXT_SECTIONS = [
    "indications_and_usage",
    "purpose",
    "adverse_reactions",
    "adverse_reactions_table",
    "drug_interactions",
    "contraindications",
    "ask_doctor_or_pharmacist",
    "precautions",
    "warnings",
    "warnings_and_cautions",
    "boxed_warning",
    "stop_use",
    "when_using",
    "ask_doctor",
    "do_not_use",
]
MAX_SECTION_CHARS = 40_000

# Words that mean the wording slipped back into label jargon.
JARGON = ["indicated", "contraindicat", "concomitant", "prophylaxis", "adjunct", "seed", "illustrative"]

# Everyday side-effect phrases -> words a label might use instead.
SIDE_EFFECT_SYNONYMS = {
    "dry cough": ["cough"],
    "high potassium": ["hyperkalemia", "potassium"],
    "low potassium": ["hypokalemia", "potassium"],
    "more urination": ["urinat", "diuresis", "polyuria"],
    "sun sensitivity": ["photosensitiv", "sunlight", "sun "],
    "fatigue": ["fatigue", "tired", "asthenia"],
    "tiredness": ["fatigue", "tired", "asthenia"],
    "slow heart rate": ["bradycardia", "heart rate"],
    "cold hands or feet": ["extremit", "raynaud", "cold"],
    "ankle swelling": ["edema", "swelling"],
    "swelling": ["edema", "swelling"],
    "swelling in the legs": ["edema", "peripheral"],
    "flushing": ["flush"],
    "stomach upset": ["dyspepsia", "nausea", "abdominal", "stomach", "gastro"],
    "upset stomach": ["dyspepsia", "nausea", "abdominal", "stomach", "gastro"],
    "stomach pain": ["abdominal pain", "stomach", "epigastric"],
    "abdominal cramps": ["cramp", "abdominal"],
    "metallic taste": ["taste"],
    "dehydration": ["dehydrat", "volume depletion"],
    "genital yeast infections": ["mycotic", "yeast", "candid", "genital"],
    "decreased appetite": ["appetite", "anorexia"],
    "appetite change": ["appetite", "anorexia", "weight"],
    "low blood sugar": ["hypoglyc"],
    "weight gain": ["weight"],
    "stuffy nose": ["nasopharyngitis", "nasal", "upper respiratory"],
    "drowsiness": ["somnolence", "drows", "sleepiness", "sedat"],
    "occasional drowsiness": ["somnolence", "drows", "sleepiness", "sedat"],
    "sleepiness": ["somnolence", "drows", "sleepiness", "sedat"],
    "dry mouth": ["dry mouth", "xerostomia"],
    "nosebleeds": ["epistaxis", "nosebleed"],
    "nasal irritation": ["nasal", "irritation"],
    "mood or behavior changes": ["neuropsychiatric", "behavior", "mood", "agitation"],
    "chest tightness": ["chest", "tightness", "pressure"],
    "tingling": ["paresthesia", "tingling"],
    "word-finding difficulty": ["word", "language", "speech", "cognit", "aphasia"],
    "bleeding or easy bruising": ["bleed", "bruis", "hemorrhage", "ecchymosis"],
    "bleeding gums": ["gum", "bleed"],
    "easy bruising": ["bruis", "bleed"],
    "sexual side effects": ["sexual", "libido", "ejaculat", "anorgasm"],
    "trouble sleeping": ["insomnia", "sleep"],
    "unsteadiness": ["ataxia", "unsteadi", "balance"],
    "muscle aches": ["myalgia", "muscle"],
    "joint pain": ["arthralgia", "joint"],
    "fast heartbeat": ["tachycardia", "palpitation", "heart rate"],
    "shakiness": ["tremor", "shak"],
    "shaky hands": ["tremor", "shak"],
    "nervousness": ["nervous", "anxiety", "tremor"],
    "liver damage if too much is taken": ["liver", "hepat"],
    "rare skin rash": ["rash", "skin"],
    "gout flare-ups when first starting": ["gout", "flare"],
    "back or muscle aches": ["back pain", "myalgia", "muscle"],
    "bloating": ["bloat", "distension", "abdominal"],
    "gas": ["flatulence", "gas"],
    "heartburn": ["heartburn", "dyspepsia"],
    "breast tenderness": ["gynecomastia", "breast"],
    "vivid dreams": ["dream", "nightmare", "sleep"],
    "joint or muscle pain": ["arthralgia", "myalgia", "muscle", "joint"],
    "cold-like symptoms": ["nasopharyngitis", "cold"],
    "allergic reaction (rare)": ["allergic reaction"],
    "poor coordination": ["coordination", "ataxia"],
    "dizziness": ["dizz", "vertigo", "lightheaded"],
    "loose stools": ["loose", "diarrhea"],
}
STOP_WORDS = {"more", "when", "from", "with", "much", "taken", "that", "your", "have", "high", "first", "starting"}


def fetch_json(url: str, offline: bool) -> dict | None:
    """GET a JSON URL with an on-disk cache. openFDA answers 404 when nothing matches."""
    cache_url = re.sub(r"&api_key=[^&]+", "", url)
    cache_file = CACHE_DIR / f"{hashlib.sha1(cache_url.encode()).hexdigest()}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))
    if offline:
        raise SystemExit(f"--offline: nothing cached for {cache_url}")
    data: dict | None = None
    for attempt in range(6):
        try:
            with urlopen(Request(url, headers={"User-Agent": "discussmeds-seed-build"}), timeout=90) as response:
                data = json.load(response)
            break
        except HTTPError as exc:
            if exc.code == 404:
                data = None
                break
            if exc.code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            raise
        except (URLError, TimeoutError):
            time.sleep(2 * (attempt + 1))
    else:
        raise SystemExit(f"Could not fetch {cache_url}")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(data), encoding="utf-8")
    time.sleep(PAUSE_SECONDS)
    return data


def trim_label(label: dict) -> dict:
    """Keep only what the build needs so the cache stays small."""
    fda = label.get("openfda", {})
    sections = {}
    for key in TEXT_SECTIONS:
        value = label.get(key)
        if value:
            sections[key] = " ".join(value)[:MAX_SECTION_CHARS]
    return {
        "set_id": label.get("set_id"),
        "effective_time": label.get("effective_time"),
        "product_type": (fda.get("product_type") or [""])[0],
        "brand_name": fda.get("brand_name", []),
        "substance_name": fda.get("substance_name", []),
        "sections": sections,
    }


def search_labels(
    term: str,
    product_type: str | None,
    route: str | None,
    offline: bool,
    field: str = "openfda.substance_name",
    limit: int = 40,
    extra: str | None = None,
) -> list[dict]:
    """Newest single-ingredient labels for one ingredient and one product type."""
    parts = [f'{field}:"{term}"']
    if product_type:
        parts.append(f'openfda.product_type:"{product_type}"')
    if route:
        parts.append(f'openfda.route:"{route}"')
    if extra:
        parts.append(extra)
    query = "+AND+".join(part.replace('"', "%22").replace(" ", "+") for part in parts)
    url = f"{OPENFDA_URL}?search={query}&sort=effective_time:desc&limit={limit}"
    if os.environ.get("OPENFDA_API_KEY"):
        url += f"&api_key={os.environ['OPENFDA_API_KEY']}"
    payload = fetch_json(url, offline)
    if not payload:
        return []
    token = term.lower().split()[0]
    labels = []
    for raw in payload.get("results", []):
        if field != "openfda.substance_name":
            labels.append(trim_label(raw))  # searched by product data; caller vouches for it
            continue
        substances = [s.lower() for s in raw.get("openfda", {}).get("substance_name", [])]
        # Single-ingredient only: every listed ingredient must be this drug (salts are fine).
        if not (substances and all(token in s for s in substances)):
            continue
        # Real over-the-counter medicines carry an FDA application or monograph number.
        # Homeopathic products that merely list an ingredient (e.g. a "levothyroxine" remedy)
        # have none, and must not make a prescription-only drug look like it is sold over the counter.
        if product_type == OTC_TYPE and not raw.get("openfda", {}).get("application_number"):
            continue
        trimmed = trim_label(raw)
        # Some repackagers file an over-the-counter "Drug Facts" label under the prescription type
        # (loratadine has two). Real prescription labels never say "temporarily relieves".
        if product_type == RX_TYPE:
            use_text = (trimmed["sections"].get("indications_and_usage", "") + trimmed["sections"].get("purpose", "")).lower()
            if "temporarily relieve" in use_text:
                continue
        labels.append(trimmed)
    return labels


def rxnorm_ingredient_id(term: str, offline: bool) -> str | None:
    """Exact-name RxNorm lookup, accepted only if the result is a plain ingredient (tty IN).

    RxNav's approximate search can return a different drug entirely (it mapped
    "omeprazole" to esomeprazole), so we never use it.
    """
    payload = fetch_json(f"{RXNAV_URL}?name={quote(term)}", offline)
    ids = (payload or {}).get("idGroup", {}).get("rxnormId") or []
    if not ids:
        return None
    props = fetch_json(f"{RXNAV_PROPS_URL.format(rxcui=ids[0])}", offline)
    tty = ((props or {}).get("properties") or {}).get("tty")
    return str(ids[0]) if tty == "IN" else None


def iso_date(effective_time: str | None) -> str:
    text = effective_time or ""
    return f"{text[:4]}-{text[4:6]}-{text[6:8]}" if len(text) == 8 else "unknown-date"


def keywords_for(phrase: str) -> list[str]:
    words = re.findall(r"[a-z]+", phrase.lower())
    return [w[:5] for w in words if len(w) >= 4 and w not in STOP_WORDS]


def appears_in(phrase: str, haystack: str) -> bool:
    for synonym in SIDE_EFFECT_SYNONYMS.get(phrase.lower(), []):
        if synonym in haystack:
            return True
    return any(word in haystack for word in keywords_for(phrase))


def lint_wording(name: str, texts: list[str], problems: list[str]) -> None:
    for text in texts:
        lowered = text.lower()
        for word in JARGON:
            if word in lowered:
                problems.append(f"{name}: wording contains jargon/dev word '{word}': {text!r}")


# ---------------------------------------------------------------------------
# Drug-interaction facts: real sentences from each FDA label
# ---------------------------------------------------------------------------
# Only these label sections talk about combining medicines.
INTERACTION_SECTIONS = {
    "boxed_warning": "Boxed warning",
    "contraindications": "Contraindications",
    "drug_interactions": "Drug interactions",
    "ask_doctor_or_pharmacist": "Ask a doctor or pharmacist",
    "do_not_use": "Do not use",
    "precautions": "Precautions",  # older-format labels keep their interaction details here
}
# "( 7.1 )" and "[see Warnings and Precautions (5.1)]" are cross-reference markers; they are removed
# so the quote reads cleanly. Everything else in a quote is the label's own wording.
REFERENCE_MARKERS = re.compile(r"\(\s*\d+(?:\.\d+)?(?:\s*,\s*\d+(?:\.\d+)?)*\s*\)|\[\s*see [^\]]*\]", re.I)
STRONG_WORDS = re.compile(
    r"\b(contraindicated|should not|must not|do not|avoid|not recommended|life-threatening|fatal)\b", re.I
)
MAX_QUOTE_CHARS = 360


def clean_label_text(text: str) -> str:
    text = REFERENCE_MARKERS.sub("", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([.,;:])", r"\1", text)
    return text.strip()


SECTION_HEADING = re.compile(r"^\d+(?:\.\d+)*\s+(?:DRUG INTERACTIONS|CONTRAINDICATIONS)\s+", re.I)
SUBSECTION_NUMBER = re.compile(r"^\d+(?:\.\d+)+\s+")
# A sentence is only worth showing if it says what happens (raises a risk, lowers absorption, ...).
# Bare lists of drug names ("Examples: morphine, ..., tramadol.") carry no information.
EFFECT_WORDS = re.compile(
    r"\b(increas\w*|decreas\w*|reduc\w*|rais\w*|elevat\w*|risk|avoid\w*|concomitant|co-?administ\w*|monitor\w*|"
    r"may|can|could|result\w*|caus\w*|absorption|effect\w*|contraindicated|interact\w*|toxicity|reaction\w*|"
    r"not recommended|adjust\w*|caution|coma|death|bleeding|syndrome|limit|exceed|should|hyperkalemia)\b",
    re.I,
)


# Labels also say when a combination was tested and found harmless. That is not a warning, so it is skipped.
NO_INTERACTION = re.compile(
    r"\b(no significant|no clinically|no (?:apparent |notable )?(?:effect|change|interaction)|did not|does not|"
    r"had no|not affect|not alter|not expected|no dose adjustment|not (?:be )?clinically)\b",
    re.I,
)


def split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(\"\u201c])", text)
    cleaned = []
    for piece in pieces:
        piece = SUBSECTION_NUMBER.sub("", SECTION_HEADING.sub("", piece.strip())).strip()
        if piece:
            cleaned.append(piece)
    return cleaned


def term_regex(terms: list[str]) -> re.Pattern | None:
    terms = [t for t in terms if t]
    if not terms:
        return None
    alternatives = "|".join(re.escape(t) for t in sorted(set(terms), key=len, reverse=True))
    # Whole words only ("omeprazole" must not match inside "esomeprazole"); plural "NSAIDs" is fine.
    return re.compile(rf"(?<![A-Za-z0-9])(?:{alternatives})(?:s|es)?(?![A-Za-z0-9])", re.I)


def excerpt(sentence: str, match: re.Match) -> str:
    """A long label sentence is cut down to a window around the match (still a contiguous quote)."""
    if len(sentence) <= MAX_QUOTE_CHARS:
        return sentence
    start = max(0, match.start() - 140)
    end = min(len(sentence), match.end() + 200)
    if start > 0:
        start = sentence.rfind(" ", 0, start) + 1
    if end < len(sentence):
        space = sentence.find(" ", end)
        end = space if space != -1 else len(sentence)
    return sentence[start:end].strip()


def collect_interaction_sections(rx_labels: list[dict], otc_labels: list[dict]) -> list[tuple]:
    """(section name, cleaned text, label set id, label date) from the best Rx and OTC label."""
    collected = []
    # Labels are written in different formats, so read up to a few of the newest of each kind.
    for labels, how_many in ((rx_labels[:8], 3), (otc_labels[:8], 2)):
        taken = 0
        for label in labels:
            keys = [k for k in INTERACTION_SECTIONS if label["sections"].get(k)]
            if not keys:
                continue
            taken += 1
            for key in keys:
                collected.append(
                    (INTERACTION_SECTIONS[key], clean_label_text(label["sections"][key]), label["set_id"], label["effective_time"])
                )
            if taken >= how_many:
                break
    return collected


def _in_rule(names: list[str], drug_name: str, drug_class: str) -> bool:
    return drug_name in names or drug_class in names


def plain_note(a: dict, b: dict, severity: str) -> tuple[str, str, str]:
    """Plain-language title and explanation, and the severity (a rule may raise it, never lower it)."""
    for rule in INTERACTION_NOTES:
        forward = _in_rule(rule["a"], a["name"], a["class"]) and _in_rule(rule["b"], b["name"], b["class"])
        backward = _in_rule(rule["a"], b["name"], b["class"]) and _in_rule(rule["b"], a["name"], a["class"])
        if forward or backward:
            return rule["title"], rule["plain"], rule.get("severity") or severity
    if severity == "urgent_seed":
        return (
            f"{a['name']} and {b['name']}: strong warning on the FDA label",
            f"The FDA label for {a['name']} has a strong warning that involves {b['name']}. "
            "Ask a pharmacist or clinician before taking both.",
            severity,
        )
    return (
        f"{a['name']} and {b['name']}: mentioned together on the FDA label",
        f"The FDA label for {a['name']} mentions {b['name']} in its interaction information. "
        "Ask a pharmacist or clinician whether they are safe together.",
        severity,
    )


def build_interactions(docs: dict[str, dict], order: list[str]) -> list[dict]:
    """For every ordered pair (A, B): label sentences in A's label that mention B or B's class."""
    matchers = {}
    for name, doc in docs.items():
        generic = re.sub(r"\s*\(.*?\)", "", name).lower()
        brands = [b for b in doc["brands"] if re.fullmatch(r"[A-Za-z0-9-]{5,14}", b) and b.lower() != generic]
        matchers[name] = (term_regex([generic, *brands]), term_regex(CLASS_LABEL_TERMS.get(doc["class"], [])))

    facts: list[dict] = []
    for a in order:
        for b in order:
            if a == b:
                continue
            name_re, class_re = matchers[b]
            same_class = docs[a]["class"] == docs[b]["class"]  # the duplicate-class flag already covers this
            found = []
            for section, text, set_id, effective in docs[a]["sections"]:
                for sentence in split_sentences(text):
                    match = name_re.search(sentence) if name_re else None
                    kind = "name"
                    if not match and class_re and not same_class:
                        match, kind = class_re.search(sentence), "class"
                    if not match:
                        continue
                    quote = excerpt(sentence, match)
                    assert quote in text, f"quote is not a contiguous piece of the label: {quote!r}"
                    strong_section = section in ("Boxed warning", "Contraindications")
                    # Judge the text actually shown: it must say what happens, and must not be a bare list.
                    if not (strong_section or EFFECT_WORDS.search(quote)) or quote.count(",") > 8:
                        continue
                    if NO_INTERACTION.search(quote):
                        continue
                    strong = strong_section or STRONG_WORDS.search(sentence)
                    severity = "urgent_seed" if strong else "discuss"
                    title, plain, severity = plain_note(
                        {"name": a, "class": docs[a]["class"]}, {"name": b, "class": docs[b]["class"]}, severity
                    )
                    found.append((severity != "urgent_seed", kind != "name", len(quote), quote, kind,
                                  match.group(0), section, severity, set_id, effective, title, plain))
            found.sort()
            seen = set()
            for _s, _c, _l, quote, kind, term, section, severity, set_id, effective, title, plain in found:
                if quote in seen or len(seen) >= 2:
                    continue
                seen.add(quote)
                facts.append(
                    {
                        "drug": a,
                        "other": b,
                        "matched_on": kind,
                        "matched_term": term,
                        "section": section,
                        "severity": severity,
                        "title": title,
                        "plain": plain,
                        "quote": quote,
                        "source": f"openfda:label:{set_id}:{iso_date(effective)}",
                        "source_url": f"{DAILYMED_URL}{set_id}",
                    }
                )
    return facts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true", help="use only the local cache")
    parser.add_argument("--check", action="store_true", help="verify only; do not write data/seed.json")
    args = parser.parse_args()

    condition_defaults = {name: text for name, _aliases, text, _kw in CONDITIONS}
    condition_keywords = {name: kw for name, _aliases, _text, kw in CONDITIONS}

    previous_ids: dict[str, str | None] = {}
    if SEED_PATH.exists():
        try:
            previous = json.loads(SEED_PATH.read_text(encoding="utf-8"))
            previous_ids = {d["name"]: d.get("rxnorm_id") for d in previous.get("drugs", [])}
        except (json.JSONDecodeError, KeyError):
            previous_ids = {}

    drugs_out: list[dict] = []
    docs: dict[str, dict] = {}
    indications_out: list[dict] = []
    problems: list[str] = []
    notes: list[str] = []
    seen_names: set[str] = set()

    for index, drug in enumerate(DRUGS, start=1):
        name = drug["name"]
        if name in seen_names:
            problems.append(f"{name}: listed twice in curated_drugs.py")
            continue
        seen_names.add(name)
        term = drug.get("fda") or name.lower()
        # A drug taken by mouth is judged on its oral labels: an IV or injection version can be
        # prescription-only even when the tablets are sold over the counter (e.g. acetaminophen).
        route = drug.get("fda_route") or ("ORAL" if drug["route"] == "oral" else None)
        if drug.get("fda_field"):
            route = None  # that label has no route field to filter on
        print(f"[{index}/{len(DRUGS)}] {name} ...", flush=True)

        if drug.get("fda_field"):
            # Label openFDA cannot find by ingredient: the curated file states Rx/OTC.
            rx_labels = search_labels(term, None, route, args.offline, field=drug["fda_field"])
            otc_labels = []
            rx_otc = drug["rx_otc"]
        else:
            limit = drug.get("fda_limit", 40)
            rx_labels = search_labels(term, RX_TYPE, route, args.offline, limit=limit)
            otc_labels = search_labels(term, OTC_TYPE, route, args.offline, limit=limit)
            if rx_labels and otc_labels:
                rx_otc = "OTC or Rx (depends on the product)"
            elif rx_labels:
                rx_otc = "Rx"
            else:
                rx_otc = "OTC"
        if not rx_labels and not otc_labels:
            problems.append(f"{name}: no single-ingredient FDA label found for '{term}'")
            continue

        # Some uses appear only on a few labels among thousands (e.g. low-dose aspirin), so a drug can
        # name one extra search to find a label that states that use.
        use_labels = rx_labels + otc_labels
        if drug.get("fda_use_check"):
            use_labels = use_labels + search_labels(
                term, None, route, args.offline, limit=5, extra=drug["fda_use_check"]
            )

        primary = (rx_labels or otc_labels)[0]
        # Look at the five newest labels of each kind: one unusual label should not hide a fact.
        sample = rx_labels[:5] + otc_labels[:5]
        haystack = " ".join(text for label in sample for text in label["sections"].values()).lower()
        # "Is this use stated on any FDA label for this drug?" - so look at every label, not just the newest.
        indications_text = " ".join(
            label["sections"].get(key, "")
            for label in use_labels
            for key in ("indications_and_usage", "purpose")
        ).lower()

        klass = CLASSES[drug["cls"]] if drug.get("cls") else {}
        drug_class = drug.get("klass") or klass["name"]
        what = drug.get("what") or klass["what"]
        effects = drug.get("effects") or klass["effects"]
        watch = drug.get("watch") or klass["watch"]
        use_note = f"{drug['how']} {what}"

        lint_wording(name, [use_note, watch, *effects], problems)

        missing_effects = [e for e in effects if not appears_in(e, haystack)]
        if missing_effects:
            notes.append(f"{name}: side effect(s) not found in the FDA label text: {', '.join(missing_effects)}")

        rxnorm = rxnorm_ingredient_id(drug.get("rxnav") or term, args.offline)
        old = previous_ids.get(name)
        if rxnorm is None:
            rxnorm = old
            notes.append(f"{name}: RxNav gave no id; kept previous id {old}")
        elif old and old != rxnorm:
            notes.append(f"{name}: RxNorm id changed {old} -> {rxnorm}")

        drugs_out.append(
            {
                "name": name,
                "rxnorm_id": rxnorm,
                "drug_class": drug_class,
                "route": drug["route"],
                "rx_otc": rx_otc,
                "common_side_effects": effects,
                "typical_use_note": use_note,
                "monitoring_note": watch,
            }
        )

        source = f"openfda:label:{primary['set_id']}:{iso_date(primary['effective_time'])}"
        source_url = f"{DAILYMED_URL}{primary['set_id']}"
        docs[name] = {
            "class": drug_class,
            "brands": sorted({brand for label in sample for brand in label["brand_name"]}),
            "sections": collect_interaction_sections(rx_labels, otc_labels),
        }
        for cond in drug["conds"]:
            cond_name, cond_text = cond if isinstance(cond, tuple) else (cond, condition_defaults.get(cond))
            if cond_name not in condition_defaults:
                problems.append(f"{name}: unknown condition '{cond_name}'")
                continue
            lint_wording(name, [cond_text], problems)
            if not any(word in indications_text for word in condition_keywords[cond_name]):
                notes.append(f"{name}: '{cond_name}' not found in the FDA label's use section")
            indications_out.append(
                {
                    "drug": name,
                    "condition": cond_name,
                    "raw_text": cond_text,
                    "source": source,
                    "source_url": source_url,
                }
            )

    # Original drugs first, in their original order, so their database ids never change.
    legacy_rank = {name: position for position, name in enumerate(LEGACY_DRUG_ORDER)}
    drugs_out.sort(key=lambda row: legacy_rank.get(row["name"], len(legacy_rank)))

    interactions_out = build_interactions(docs, [row["name"] for row in drugs_out])
    print(f"Interaction facts found in FDA labels: {len(interactions_out)}")

    print()
    print(f"Drugs built: {len(drugs_out)} of {len(DRUGS)}")
    if notes:
        print(f"\nNeeds a human look ({len(notes)}):")
        for line in notes:
            print(f"  - {line}")
    if problems:
        print(f"\nProblems ({len(problems)}):")
        for line in problems:
            print(f"  ! {line}")
        return 1
    if args.check:
        return 0

    payload = {
        "meta": {
            "label": "FDA drug label data (openFDA), with plain-language wording written by the team",
            "retrieved": date.today().isoformat(),
            "sources": {
                "labels": "openFDA drug label API — https://open.fda.gov/apis/drug/label/",
                "ingredient_ids": "NLM RxNav RxNorm lookup",
                "label_pages": "DailyMed (linked from each indication's source_url)",
            },
            "not": "clinical guidelines, a complete list of side effects or interactions, or prescribing advice",
            "how_it_is_built": "python scripts/build_seed_from_openfda.py",
        },
        "combination_rules": COMBINATION_RULES,
        "conditions": [
            {"name": name, "aliases": aliases} for name, aliases, _text, _kw in CONDITIONS
        ],
        "drugs": drugs_out,
        "indications": indications_out,
        "interactions": interactions_out,
    }
    SEED_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote {SEED_PATH} ({len(drugs_out)} drugs, {len(indications_out)} indications)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
