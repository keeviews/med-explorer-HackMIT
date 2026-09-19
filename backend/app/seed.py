"""Load illustrative seed JSON into SQLite. Safe to re-run (replaces seed rows)."""

from __future__ import annotations

import json

from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from app.config import SEED_PATH
from app.db import Base, SessionLocal, engine
from app.models import Condition, Drug, Indication
from app.suggest import normalize_text


def schema_is_current() -> bool:
    inspector = inspect(engine)
    if "drugs" not in inspector.get_table_names():
        return False
    columns = {column["name"] for column in inspector.get_columns("drugs")}
    required = {
        "drug_class",
        "route",
        "rx_otc",
        "side_effects_json",
        "typical_use_note",
        "monitoring_note",
    }
    return required.issubset(columns)


def seed_database(session: Session | None = None) -> dict[str, int]:
    owns_session = session is None
    session = session or SessionLocal()
    try:
        session.expire_all()
        session.execute(text("PRAGMA foreign_keys = OFF"))
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        session.execute(text("PRAGMA foreign_keys = ON"))
        payload = json.loads(SEED_PATH.read_text(encoding="utf-8"))

        conditions_by_key: dict[str, Condition] = {}
        for item in payload["conditions"]:
            name = item["name"].strip()
            condition = Condition(
                name=name,
                normalized_name=normalize_text(name),
                aliases_json=json.dumps(item.get("aliases", []), ensure_ascii=False),
            )
            session.add(condition)
            session.flush()
            conditions_by_key[normalize_text(name)] = condition

        drugs_by_name: dict[str, Drug] = {}
        for item in payload["drugs"]:
            drug = Drug(
                name=item["name"].strip(),
                rxnorm_id=item.get("rxnorm_id"),
                drug_class=item.get("drug_class"),
                route=item.get("route"),
                rx_otc=item.get("rx_otc"),
                side_effects_json=json.dumps(
                    item.get("common_side_effects", []), ensure_ascii=False
                ),
                typical_use_note=item.get("typical_use_note"),
                monitoring_note=item.get("monitoring_note"),
            )
            session.add(drug)
            session.flush()
            drugs_by_name[normalize_text(drug.name)] = drug

        for item in payload["indications"]:
            drug = drugs_by_name[normalize_text(item["drug"])]
            condition_name = item.get("condition")
            condition = (
                conditions_by_key.get(normalize_text(condition_name))
                if condition_name
                else None
            )
            session.add(
                Indication(
                    drug_id=drug.id,
                    condition_id=condition.id if condition else None,
                    raw_text=item["raw_text"].strip(),
                    source=item.get("source", "seed:illustrative"),
                    source_url=item.get("source_url"),
                )
            )

        session.commit()
        return {
            "conditions": session.scalar(select(func.count()).select_from(Condition)) or 0,
            "drugs": session.scalar(select(func.count()).select_from(Drug)) or 0,
            "indications": session.scalar(select(func.count()).select_from(Indication)) or 0,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()


def database_is_seeded(session: Session) -> bool:
    if not schema_is_current():
        return False
    count = session.scalar(select(func.count()).select_from(Indication))
    if not count:
        return False
    # Older DBs may have the new columns but empty compare fields.
    sample = session.scalar(
        select(Drug.drug_class).where(Drug.drug_class.isnot(None)).limit(1)
    )
    if not sample:
        return False
    # A database built from an older data/seed.json has a different drug count.
    # Rebuilding is safe: the database only ever holds data derived from seed.json.
    expected = len(json.loads(SEED_PATH.read_text(encoding="utf-8"))["drugs"])
    return session.scalar(select(func.count()).select_from(Drug)) == expected
