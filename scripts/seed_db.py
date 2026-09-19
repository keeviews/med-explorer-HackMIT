#!/usr/bin/env python3
"""Load data/seed.json into the local SQLite database.

Safe to re-run. The API also seeds automatically on startup if the
indications table is empty.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.config import DB_PATH, SEED_PATH  # noqa: E402
from app.seed import seed_database  # noqa: E402


def main() -> None:
    counts = seed_database()
    print(f"Seeded {DB_PATH} from {SEED_PATH}")
    print(
        "  conditions={conditions} drugs={drugs} indications={indications}".format(
            **counts
        )
    )


if __name__ == "__main__":
    main()
