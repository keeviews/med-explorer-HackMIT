from contextlib import asynccontextmanager
from pathlib import Path
import json
import secrets

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.compare import (
    load_drugs_by_ids,
    load_drugs_by_names,
    load_interaction_facts,
    parse_id_list,
    parse_name_list,
    serialize_drug,
)
from app.config import (
    COMPARE_LIMIT,
    CORS_ORIGINS,
    DB_PATH,
    EPIC_FHIR_BASE,
    EPIC_REDIRECT_URI,
    REVIEW_LIMIT,
)
from app.db import Base, engine, get_session
from app.disclaimer import (
    COMPARE_DATA_NOTICE,
    COMPARE_NOTE,
    DATA_LABEL,
    DATA_NOTICE,
    DISCLAIMER,
    OVERLAP_NOTE,
    TALK_WITH_CLINICIAN,
)
from app.fhir_import import (
    authorize_url,
    demo_bundle,
    extract_medications_from_bundle,
    map_medications,
    mychart_is_configured,
    setup_message,
)
from app.insights import build_insights
from app.medicine_match import resolve_text
from app.models import Condition, Drug
from app.schemas import (
    CombinationAlert,
    CompareResponse,
    ConditionSummary,
    DrugDetail,
    DrugDetailResponse,
    FhirImportResponse,
    HealthResponse,
    MappedMedication,
    MyChartStatusResponse,
    MedicineScanResponse,
    MedicineResolveRequest,
    SeededConditionsResponse,
    Similarity,
    SuggestResponse,
    Suggestion,
    UnmappedMedication,
)
from app.seed import database_is_seeded, seed_database
from app.suggest import suggest_drugs


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    from app.db import SessionLocal

    session = SessionLocal()
    try:
        if not database_is_seeded(session):
            seed_database(session)
    finally:
        session.close()
    yield


app = FastAPI(
    title="DiscussMeds",
    description=(
        "Patient/consumer decision-support API: search a condition and see "
        "associated medicines from open indication data. Compare selected "
        "medicines as discussion starters, with seed overlap highlights. "
        "Not a prescribing tool."
    ),
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health(session: Session = Depends(get_session)) -> HealthResponse:
    return HealthResponse(
        database=str(Path(DB_PATH).name),
        seeded=database_is_seeded(session),
    )


@app.get("/conditions", response_model=SeededConditionsResponse)
def list_conditions(session: Session = Depends(get_session)) -> SeededConditionsResponse:
    rows = session.query(Condition).order_by(Condition.name.asc()).all()
    return SeededConditionsResponse(
        conditions=[
            ConditionSummary(name=row.name, aliases=json.loads(row.aliases_json or "[]"))
            for row in rows
        ]
    )


@app.get("/suggest", response_model=SuggestResponse)
def suggest(
    q: str = Query(..., min_length=2, max_length=200, description="Condition or indication text"),
    limit: int = Query(20, ge=1, le=50),
    session: Session = Depends(get_session),
) -> SuggestResponse:
    hits = suggest_drugs(session, q, limit=limit)
    return SuggestResponse(
        query=q.strip(),
        disclaimer=DISCLAIMER,
        data_notice=DATA_NOTICE,
        result_count=len(hits),
        results=[
            Suggestion(
                id=hit.id,
                drug_name=hit.drug_name,
                rxnorm_id=hit.rxnorm_id,
                indication_snippet=hit.indication_snippet,
                matched_condition=hit.matched_condition,
                source=hit.source,
                data_label=DATA_LABEL,
                score=hit.score,
            )
            for hit in hits
        ],
    )


@app.get("/drugs/{drug_id}", response_model=DrugDetailResponse)
def get_drug(drug_id: int, session: Session = Depends(get_session)) -> DrugDetailResponse:
    found, _missing = load_drugs_by_ids(session, [drug_id])
    if not found:
        raise HTTPException(status_code=404, detail="That medicine is not in this dataset.")
    return DrugDetailResponse(
        disclaimer=DISCLAIMER,
        data_notice=COMPARE_DATA_NOTICE,
        compare_note=COMPARE_NOTE,
        drug=DrugDetail.model_validate(serialize_drug(found[0])),
    )


def _payload_for_drugs(session: Session, found: list, limit: int) -> CompareResponse:
    details = [serialize_drug(row) for row in found]
    insights = build_insights(details, load_interaction_facts(session, [row.id for row in found]))
    return CompareResponse(
        disclaimer=DISCLAIMER,
        data_notice=COMPARE_DATA_NOTICE,
        compare_note=COMPARE_NOTE,
        overlap_note=OVERLAP_NOTE,
        talk_with_clinician=TALK_WITH_CLINICIAN,
        compare_limit=limit,
        result_count=len(found),
        drugs=[DrugDetail.model_validate(row) for row in details],
        similarities=[Similarity.model_validate(row) for row in insights["similarities"]],
        alerts=[CombinationAlert.model_validate(row) for row in insights["alerts"]],
        overlap_summary=insights["overlap_summary"],
    )


def _load_requested_drugs(
    session: Session,
    ids: str | None,
    names: str | None,
    limit: int,
) -> list:
    if ids:
        try:
            requested_ids = parse_id_list(ids)
        except ValueError as exc:
            raise HTTPException(
                status_code=422, detail="ids must be comma-separated integers"
            ) from exc
        if not requested_ids:
            raise HTTPException(status_code=422, detail="Provide at least one drug id")
        if len(requested_ids) > limit:
            raise HTTPException(
                status_code=422,
                detail=f"This list is capped at {limit} medicines",
            )
        found, missing = load_drugs_by_ids(session, requested_ids)
        if missing:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown drug id(s): {', '.join(str(i) for i in missing)}",
            )
        return found
    if names:
        requested_names = parse_name_list(names)
        if not requested_names:
            raise HTTPException(status_code=422, detail="Provide at least one drug name")
        if len(requested_names) > limit:
            raise HTTPException(
                status_code=422,
                detail=f"This list is capped at {limit} medicines",
            )
        found, missing_names = load_drugs_by_names(session, requested_names)
        if missing_names:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown drug name(s): {', '.join(missing_names)}",
            )
        return found
    raise HTTPException(status_code=422, detail="Provide ids or names")


@app.get("/compare", response_model=CompareResponse)
def compare(
    ids: str | None = Query(None, description="Comma-separated drug ids"),
    names: str | None = Query(None, description="Comma-separated drug names"),
    session: Session = Depends(get_session),
) -> CompareResponse:
    found = _load_requested_drugs(session, ids, names, COMPARE_LIMIT)
    return _payload_for_drugs(session, found, COMPARE_LIMIT)


@app.get("/review", response_model=CompareResponse)
def review(
    ids: str | None = Query(None, description="Comma-separated drug ids from a personal list"),
    names: str | None = Query(None, description="Comma-separated drug names"),
    session: Session = Depends(get_session),
) -> CompareResponse:
    found = _load_requested_drugs(session, ids, names, REVIEW_LIMIT)
    return _payload_for_drugs(session, found, REVIEW_LIMIT)


def _import_payload(session: Session, medications: list, source: str) -> FhirImportResponse:
    mapped, unmapped = map_medications(session, medications, source)
    return FhirImportResponse(
        disclaimer=DISCLAIMER,
        source=source,
        mapped=[MappedMedication.model_validate(row) for row in mapped],
        unmapped=[UnmappedMedication.model_validate(row) for row in unmapped],
        mapped_count=len(mapped),
        unmapped_count=len(unmapped),
    )


@app.get("/integrations/mychart", response_model=MyChartStatusResponse)
def mychart_status() -> MyChartStatusResponse:
    state = secrets.token_urlsafe(16)
    challenge = secrets.token_urlsafe(32)
    return MyChartStatusResponse(
        disclaimer=DISCLAIMER,
        configured=mychart_is_configured(),
        authorize_url=authorize_url(state, challenge),
        redirect_uri=EPIC_REDIRECT_URI,
        fhir_base=EPIC_FHIR_BASE,
        setup_note=setup_message(),
    )


@app.get("/integrations/mychart/demo", response_model=FhirImportResponse)
def mychart_demo_import(session: Session = Depends(get_session)) -> FhirImportResponse:
    medications = extract_medications_from_bundle(demo_bundle())
    return _import_payload(session, medications, "fhir_demo")


@app.post("/medicines/resolve", response_model=MedicineScanResponse)
def resolve_medicine_text(
    payload: MedicineResolveRequest,
    session: Session = Depends(get_session),
) -> MedicineScanResponse:
    """Match text produced in the browser without uploading the label photo."""
    raw_text = payload.raw_text.strip()
    return MedicineScanResponse(
        mode="ocr",
        notice=(
            "Your browser read this text with PaddleOCR. Check the printed label and select a match "
            "before adding it; no medicine is added automatically."
        ),
        raw_text=raw_text,
        candidates=resolve_text(raw_text, session.query(Drug).all()),
    )


@app.get("/integrations/mychart/callback")
def mychart_callback() -> dict[str, str]:
    raise HTTPException(
        status_code=501,
        detail=(
            "Live SMART token exchange is not completed in this local MVP. "
            "Register an Epic patient-facing app, then finish the code→token "
            "exchange against EPIC_TOKEN_URL. Until then, use "
            "GET /integrations/mychart/demo."
        ),
    )
