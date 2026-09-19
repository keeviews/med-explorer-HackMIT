from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Drug(Base):
    __tablename__ = "drugs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rxnorm_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    drug_class: Mapped[str | None] = mapped_column(String(128), nullable=True)
    route: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rx_otc: Mapped[str | None] = mapped_column(String(32), nullable=True)
    side_effects_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    typical_use_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    monitoring_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    indications: Mapped[list["Indication"]] = relationship(back_populates="drug")

    __table_args__ = (UniqueConstraint("name", name="uq_drugs_name"),)


class Condition(Base):
    __tablename__ = "conditions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    aliases_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    indications: Mapped[list["Indication"]] = relationship(back_populates="condition")

    __table_args__ = (UniqueConstraint("normalized_name", name="uq_conditions_normalized"),)


class Indication(Base):
    __tablename__ = "indications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    drug_id: Mapped[int] = mapped_column(ForeignKey("drugs.id"), nullable=False, index=True)
    condition_id: Mapped[int | None] = mapped_column(
        ForeignKey("conditions.id"), nullable=True, index=True
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    drug: Mapped[Drug] = relationship(back_populates="indications")
    condition: Mapped[Condition | None] = relationship(back_populates="indications")
