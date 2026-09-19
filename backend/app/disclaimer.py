"""Fixed consumer-facing medical disclaimer. Do not vary this per request."""

DISCLAIMER = (
    "This tool is decision support only — not medical advice, a diagnosis, "
    "or a prescription. Do not start, stop, or change any medicine based on "
    "these results. Discuss them with a licensed clinician who knows your history."
)

DATA_LABEL = "FDA label data"

DATA_NOTICE = (
    "Medicine names, what they are used for, and whether they are sold over the "
    "counter come from U.S. FDA drug labels (openFDA). Our team wrote the plain-language "
    "descriptions from those labels. This is not a complete list of medicines and "
    "not clinical guidelines."
)

COMPARE_DATA_NOTICE = (
    DATA_NOTICE
    + " The side effects shown are common ones that appear in the FDA label — not a "
    "full list. Read the label or ask a pharmacist about the rest."
)

COMPARE_NOTE = (
    "This table shows how the medicines differ so you can prepare questions for a "
    "clinician. It is not a ranking, not a “best option,” and not a "
    "recommendation to start, stop, or choose any medicine."
)

OVERLAP_NOTE = (
    "Sage highlighting marks matching fields. Red highlighting marks flags for "
    "possible class overlap or combinations that clinicians often review closely. "
    "These flags are not a complete interaction checker and are not instructions "
    "to stop, cut, or combine medicines. Talk with your clinician before changing "
    "anything."
)

TALK_WITH_CLINICIAN = (
    "Ask your clinician whether every medicine on this list is still needed. "
    "DiscussMeds cannot tell you to stop, cut, or keep any medicine."
)
