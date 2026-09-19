from pydantic import BaseModel, Field

from app.disclaimer import (
    COMPARE_DATA_NOTICE,
    COMPARE_NOTE,
    DATA_NOTICE,
    DISCLAIMER,
    OVERLAP_NOTE,
    TALK_WITH_CLINICIAN,
)


class Suggestion(BaseModel):
    id: int
    drug_name: str
    rxnorm_id: str | None
    indication_snippet: str
    matched_condition: str | None
    source: str
    data_label: str = "Illustrative seed data"
    score: float


class SuggestResponse(BaseModel):
    query: str
    disclaimer: str = DISCLAIMER
    data_notice: str = DATA_NOTICE
    result_count: int
    results: list[Suggestion]


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "discussmeds"
    database: str
    seeded: bool


class ConditionSummary(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)


class SeededConditionsResponse(BaseModel):
    disclaimer: str = DISCLAIMER
    data_notice: str = DATA_NOTICE
    conditions: list[ConditionSummary]


class DrugDetail(BaseModel):
    id: int
    drug_name: str
    rxnorm_id: str | None
    drug_class: str | None
    route: str | None
    rx_otc: str | None
    common_side_effects: list[str] = Field(default_factory=list)
    typical_use_note: str | None
    monitoring_note: str | None
    linked_conditions: list[str] = Field(default_factory=list)
    data_label: str = "Illustrative seed data"


class Similarity(BaseModel):
    field: str
    value: str
    drug_ids: list[int]
    drug_names: list[str]


class CombinationAlert(BaseModel):
    severity: str
    code: str
    title: str
    detail: str
    talk_with_clinician: str = TALK_WITH_CLINICIAN
    drug_ids: list[int]
    drug_names: list[str]
    fields: list[str] = Field(default_factory=list)
    data_label: str = "Illustrative seed data"


class DrugDetailResponse(BaseModel):
    disclaimer: str = DISCLAIMER
    data_notice: str = COMPARE_DATA_NOTICE
    compare_note: str = COMPARE_NOTE
    drug: DrugDetail


class CompareResponse(BaseModel):
    disclaimer: str = DISCLAIMER
    data_notice: str = COMPARE_DATA_NOTICE
    compare_note: str = COMPARE_NOTE
    overlap_note: str = OVERLAP_NOTE
    talk_with_clinician: str = TALK_WITH_CLINICIAN
    compare_limit: int
    result_count: int
    drugs: list[DrugDetail]
    similarities: list[Similarity] = Field(default_factory=list)
    alerts: list[CombinationAlert] = Field(default_factory=list)
    overlap_summary: str | None = None


class MappedMedication(BaseModel):
    id: int
    name: str
    rxnorm_id: str | None = None
    fhir_name: str | None = None
    source: str


class UnmappedMedication(BaseModel):
    name: str
    rxnorm_id: str | None = None
    source: str


class MyChartStatusResponse(BaseModel):
    disclaimer: str = DISCLAIMER
    configured: bool
    authorize_url: str | None = None
    redirect_uri: str
    fhir_base: str
    setup_note: str
    demo_available: bool = True


class FhirImportResponse(BaseModel):
    disclaimer: str = DISCLAIMER
    data_notice: str = (
        "Imported names are matched to illustrative seed drugs by RxNorm id or "
        "name. This is not a live chart unless a SMART on FHIR session succeeded. "
        "Unmapped medicines stay visible as notes but cannot enter compare."
    )
    source: str
    mapped: list[MappedMedication] = Field(default_factory=list)
    unmapped: list[UnmappedMedication] = Field(default_factory=list)
    mapped_count: int
    unmapped_count: int
