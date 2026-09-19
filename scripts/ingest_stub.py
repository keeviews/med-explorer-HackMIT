#!/usr/bin/env python3
"""Placeholder ingest for DrugCentral indications + RxNorm normalization.

This script does **not** download the full DrugCentral PostgreSQL dump in
this pass. The dump is large, requires Postgres to load, and we are not
shipping a live network ingest until licensing, size, and mapping QA are
handled on purpose.

Intended pipeline (next pass)
-----------------------------
1. Download
   - DrugCentral Postgres dump from https://drugcentral.org/download
     (full database dump; also review their SQL query examples).
   - Optional TSV extracts if a smaller indication-only file is published
     for the release you pin.

2. Load (Postgres, not SQLite)
   - createdb drugcentral
   - psql drugcentral < drugcentral.dump.<date>.sql
   - Confirm tables: `structures` (drugs) and `omop_relationship`
     (indication / contraindication / off-label use).

3. Extract labeled indications only
   Example shape used by public DrugCentral SQL examples::

       SELECT s.id AS drugcentral_id,
              s.name AS drug_name,
              r.relationship_name,
              r.concept_name AS indication_text
       FROM structures s
       JOIN omop_relationship r ON r.struct_id = s.id
       WHERE r.relationship_name = 'indication';

   Skip `contraindication` and `off-label use` for the consumer MVP unless
   product explicitly adds those later. This app does **not** currently
   filter allergies, interactions, or deprescribing.

4. Normalize drug names to RxNorm
   - Prefer RxNorm ingredient RXCUI (not brand or clinical-drug NDC packs).
   - Lookup via NIH RxNav REST (`rxnav.nlm.nih.gov`) in small batches, or
     offline via the RxNorm RRF release if you need reproducible air-gapped
     builds.
   - Store `rxnorm_id` on `drugs`; keep the original DrugCentral name as
     `name` (or add `drugcentral_id` when the schema grows).

5. Map indication text to searchable conditions
   - Keep `indications.raw_text` as the source string.
   - Optionally cluster/map to `conditions` using UMLS / SNOMED (DrugCentral
     already maps many concepts) plus a small synonym list for consumer
     queries ("high blood pressure" → hypertension).
   - Label `source` as `drugcentral:<release-date>` and set `source_url`.

6. Load into this app's SQLite schema
   - Truncate or version the local DB.
   - Insert drugs, conditions, indications.
   - Re-run ranking as-is (simple text match). Later: SQLite FTS5.

Usage when implemented
----------------------
    python scripts/ingest_stub.py --help
    python scripts/ingest_stub.py --dry-run
    python scripts/ingest_stub.py --dump /path/to/drugcentral.dump.sql

Do not treat this placeholder as a working downloader.
"""

from __future__ import annotations

import argparse
import sys


PIPELINE_STEPS = [
    "Download DrugCentral Postgres dump (https://drugcentral.org/download)",
    "Load dump into local Postgres (structures + omop_relationship)",
    "SELECT indication rows only (exclude contraindication / off-label unless scoped)",
    "Normalize drug names to RxNorm RXCUI (RxNav or RxNorm RRF)",
    "Keep raw indication text; map consumer synonyms onto conditions",
    "Write into SQLite: drugs, conditions, indications with source=drugcentral:<date>",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="DrugCentral + RxNorm ingest stub (not a live downloader)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the intended pipeline and exit 0.",
    )
    parser.add_argument(
        "--dump",
        metavar="PATH",
        help="Future: path to a DrugCentral Postgres dump. Not loaded yet.",
    )
    args = parser.parse_args()

    print("DiscussMeds ingest stub — no dump is downloaded or imported.")
    print()
    print("Intended pipeline:")
    for i, step in enumerate(PIPELINE_STEPS, start=1):
        print(f"  {i}. {step}")
    print()
    if args.dump:
        print(f"Received --dump {args.dump!r} but ingest is not implemented.")
        print("Keep using data/seed.json until this script writes real rows.")
        return 2 if not args.dry_run else 0
    print("Seed path for now: python scripts/seed_db.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
