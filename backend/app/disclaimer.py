"""Fixed consumer-facing medical disclaimer. Do not vary this per request."""

DISCLAIMER = (
    "This tool is decision support only — not medical advice, a diagnosis, "
    "or a prescription. Do not start, stop, or change any medicine based on "
    "these results. Discuss them with a licensed clinician who knows your history."
)

DATA_NOTICE = (
    "Results below come from illustrative seed data for development, not from "
    "a complete open-data ingest and not from clinical guidelines. When the "
    "DrugCentral + RxNorm pipeline is connected, this notice will name the "
    "actual sources."
)

COMPARE_DATA_NOTICE = (
    DATA_NOTICE
    + " Side-effect and property fields are a short illustrative list for "
    "development — not SIDER, OpenFDA, complete product labeling, or a ranking."
)

COMPARE_NOTE = (
    "This table shows differences in illustrative seed data so you can prepare "
    "questions for a clinician. It is not a ranking, not a “best option,” and "
    "not a recommendation to start, stop, or choose any medicine."
)

OVERLAP_NOTE = (
    "Sage highlighting marks matching seed fields. Red highlighting marks "
    "illustrative seed flags for possible class overlap or combinations that "
    "clinicians often review closely. These flags are not a complete interaction "
    "checker and are not instructions to stop, cut, or combine medicines. Talk "
    "with your clinician before changing anything."
)

TALK_WITH_CLINICIAN = (
    "Ask your clinician whether every medicine on this list is still needed. "
    "DiscussMeds cannot tell you to stop, cut, or keep any medicine."
)
