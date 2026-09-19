from app.db import SessionLocal
from app.fhir_import import match_seed_drug


def _match(name, rxnorm_id=None):
    with SessionLocal() as session:
        drug = match_seed_drug(session, name, rxnorm_id)
        return drug.name if drug else None


def test_rxnorm_id_matches_first():
    assert _match("some odd product name", "29046") == "Lisinopril"


def test_exact_name_beats_a_longer_lookalike():
    # "omeprazole" is a substring of "esomeprazole"; each must map to itself.
    assert _match("Omeprazole 20 MG Delayed Release Oral Capsule") == "Omeprazole"
    assert _match("Esomeprazole 40 MG Delayed Release Oral Capsule") == "Esomeprazole"


def test_combination_products_are_not_guessed():
    assert _match("Lisinopril and Hydrochlorothiazide 20-12.5 MG Oral Tablet") is None
    assert _match("Hydrocodone/Acetaminophen 5-325 MG Oral Tablet") is None


def test_unknown_supplement_stays_unmapped():
    assert _match("Fish Oil 1000 MG Oral Capsule") is None
