# DiscussMeds

A local-first patient/consumer MVP: search a **medical condition**, see **associated medicines** from indication data, and take that list to a clinician.

This is **decision support only**. It is not a prescribing tool, not a diagnosis, and not advice to start or stop a medicine.

## What this first pass includes

- FastAPI backend with `GET /health`, `GET /suggest`, `GET /compare?ids=`, `GET /review?ids=` (longer personal list), and `GET /drugs/{id}`
- SQLite schema: `conditions`, `drugs` (name, optional RxNorm ID, class/route/Rx-OTC, seed side effects and notes), `indications` (raw text + source)
- Illustrative **seed data** so search, compare, and overlap flags work without downloading external dumps
- React + TypeScript + Vite UI with search, a capped compare list (up to 4), sage/red cell highlighting, a private currently-taking list, MyChart/SMART on FHIR wiring plus a demo FHIR import, empty/error states, and a prominent disclaimer
- A **Simple / More detail** language toggle (defaults to Simple, saved in this browser) so the same screens stay readable for anyone, with extra technical notes only when you want them
- An ingest **stub** documenting the later DrugCentral + RxNorm pipeline

Not included: accounts, insurance, pharmacy pricing, allergy filtering, or a complete interaction/DDI database. Seed overlap flags are discussion starters only.

## Architecture

```
frontend (Vite :41789)  --CORS GET-->  backend (FastAPI :18765)  -->  SQLite
                                                              ^
                                                              |
                         data/seed.json  --scripts/seed_db.py-+
                         (also auto-loaded on API startup if DB is empty)
```

Ranking is simple text match on condition names, aliases, and raw indication strings. It is **not** a clinical ranking and does not claim guideline authority.

Every `/suggest` and `/compare` response includes the same disclaimer string. Compare is a side-by-side table of seed fields so a patient can prepare questions — it is **not** a ranking or a “best option.”

## Compare list

Search results include **Add to compare**. The sticky tray holds up to four medicines. With two or more selected, **Compare differences** loads `GET /compare?ids=` and shows class, route, Rx/OTC, typical-use notes, a short common-side-effect list, and clinician discussion topics.

Matching seed fields (same route, shared condition, overlapping listed side effects, and so on) are highlighted in **sage**. **Red** marks illustrative seed flags such as two medicines in the same class, or an ACE inhibitor plus an ARB. That is **not** a complete interaction checker and **not** an instruction to stop or cut a medicine — the copy tells you to ask your clinician whether every item is still needed.

**Currently taking** is stored in this browser (`localStorage`), with a past-notes history. You can fill it from search, or from a SMART on FHIR / demo FHIR import. **Review current list for overlap** calls `GET /review?ids=` (up to 12). Moving a medicine to past notes only updates your local list.

Side-effect, property, and overlap fields are **illustrative seed data**, not SIDER, OpenFDA, or complete labeling.

## Prerequisites

- Python 3.12+
- Node.js 22+ and npm

## Run locally (two terminals)

From the repo root:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/python scripts/seed_db.py
```

Terminal 1 — API:

```bash
cd backend
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 18765
```

If the database file is missing or empty, the API seeds it on startup from `data/seed.json`.

Terminal 2 — UI:

```bash
cd frontend
npm install
npm run dev
```

Open [http://127.0.0.1:41789](http://127.0.0.1:41789). Try **high blood pressure**, **type 2 diabetes**, **hay fever**, **GERD**, or **migraine**. Use **Simple** or **More detail** in the header to switch language.

Or with Make (after the venv exists):

```bash
make setup
make backend    # terminal 1
make frontend   # terminal 2
```

### Check the API without the UI

```bash
curl -s http://127.0.0.1:18765/health
curl -s "http://127.0.0.1:18765/suggest?q=hypertension&limit=20"
curl -s "http://127.0.0.1:18765/compare?names=Lisinopril,Losartan"
curl -s "http://127.0.0.1:18765/review?names=Lisinopril,Amlodipine,Losartan,Omeprazole"
```

Each suggest payload includes `disclaimer` and labels results as **illustrative seed data**.

Backend tests:

```bash
cd backend && .venv/bin/pytest
```

## Seed data (important)

`data/seed.json` is a **development fixture**. It is not a clinical guideline, not a complete open-data extract, and not an endorsement of any medicine.

RxNorm IDs in the seed file are public identifiers included so the schema is realistic. When the real ingest lands, those IDs should come from RxNorm/RxNav, not from this hand list.

## Next step: real open-data ingest

`scripts/ingest_stub.py` is a documented placeholder. It does **not** download the DrugCentral dump in this pass (size, Postgres load, and licensing/QA should be deliberate).

Intended path:

1. Download the DrugCentral PostgreSQL dump from [drugcentral.org/download](https://drugcentral.org/download)
2. Load it into local Postgres (`structures` + `omop_relationship`)
3. Extract `relationship_name = 'indication'` (not contraindications / off-label unless product scope expands)
4. Normalize drug names to RxNorm RXCUI via RxNav or the RxNorm RRF files
5. Keep raw indication text; map consumer synonyms onto `conditions`
6. Write into this SQLite schema with `source=drugcentral:<release-date>`
7. Later: attach labeled-effect sources (SIDER / OpenFDA) onto the same `drugs` compare fields — still as discussion data, not rankings

```bash
python scripts/ingest_stub.py --dry-run
```

## Ports and CORS

| Service  | URL |
|----------|-----|
| Frontend | http://127.0.0.1:41789 |
| Backend  | http://127.0.0.1:18765 |

The UI calls the API directly (`VITE_API_URL` in `frontend/.env`). FastAPI allows those localhost origins.

## MyChart / Epic (SMART on FHIR)

DiscussMeds does **not** collect a MyChart password. The supported live path is Epic’s patient standalone SMART on FHIR launch: the patient signs in at MyChart, grants medication read access, and this app maps `MedicationRequest` rows onto seed drugs (RxNorm id, then name).

Until an Epic client id is registered, use **Load demo medications** on the My medicines card (`GET /integrations/mychart/demo`). That fills the current list from a synthetic FHIR bundle so you can try overlap review without a clinic connection.

To enable live sign-in later:

1. Register a **patient-facing** app at [fhir.epic.com](https://fhir.epic.com/)
2. Set `EPIC_CLIENT_ID` and `EPIC_REDIRECT_URI` (see `backend/.env.example`)
3. Ask the health system to enable the app for their MyChart
4. Finish the OAuth code→token exchange (callback is stubbed as HTTP 501 in this pass)

`GET /integrations/mychart` reports whether a client id is configured. Medicines that do not match this seed dataset stay visible as notes and cannot enter compare.

## Disclaimer

This tool is decision support only — not medical advice, a diagnosis, or a prescription. Do not start, stop, or change any medicine based on these results. Discuss them with a licensed clinician who knows your history.
