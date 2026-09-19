# DiscussMeds

A local-first patient/consumer MVP: search a **medical condition**, see **associated medicines** from indication data, and take that list to a clinician.

This is **decision support only**. It is not a prescribing tool, not a diagnosis, and not advice to start or stop a medicine.

## What this first pass includes

- FastAPI backend with `GET /health`, `GET /suggest`, `GET /compare?ids=`, `GET /review?ids=` (longer personal list), and `GET /drugs/{id}`
- SQLite schema: `conditions`, `drugs` (name, optional RxNorm ID, class/route/Rx-OTC, seed side effects and notes), `indications` (raw text + source)
- Real **FDA drug label data** ([openFDA](https://open.fda.gov/apis/drug/label/)) for 81 common medicines and 25 conditions, saved in `data/seed.json` so search, compare, and overlap flags work offline
- React + TypeScript + Vite UI with search, a capped compare list (up to 4), sage/red cell highlighting, a private currently-taking list, MyChart/SMART on FHIR wiring plus a demo FHIR import, empty/error states, and a prominent disclaimer
- A **Simple / More detail** language toggle (defaults to Simple, saved in this browser) so the same screens stay readable for anyone, with extra technical notes only when you want them
- A build script (`scripts/build_seed_from_openfda.py`) that regenerates the data from openFDA and checks the wording against the FDA labels

Not included: accounts, insurance, pharmacy pricing, allergy filtering, or a complete interaction/DDI database. Overlap flags are discussion starters only.

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

Side effects shown are common ones that appear in the FDA label — not a complete list. Overlap flags are general rules (same drug class, ACE inhibitor + ARB, and so on), not a full interaction checker.

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

If the database file is missing or empty, the API seeds it on startup from `data/seed.json`. It also re-seeds on startup when the number of drugs in `data/seed.json` changes, so pulling new data just works.

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

## Data

`data/seed.json` is built from **U.S. FDA drug labels** (through [openFDA](https://open.fda.gov/apis/drug/label/)):

| Comes from the FDA | Written by the team (`scripts/curated_drugs.py`) |
|---|---|
| Whether a drug is prescription (Rx), over the counter (OTC), or both, judged from its real labels | Plain-language "used for", "how it works", and "how it is taken" |
| The RxNorm ingredient id (NLM RxNav) | Common side effects, in everyday words |
| A link to the drug's DailyMed label page and the label date, saved as `source` / `source_url` on every "used for" entry | "Ask a clinician about" notes and the overlap rules |

Everything a person reads is written in plain language on purpose. When the data is built, each hand-written claim is **checked against the FDA label text** (is the use stated on a label? does the label mention each side effect?). Anything the labels do not confirm is reported and fixed instead of shipped.

Rx/OTC is judged per route (a drug taken by mouth uses its oral labels, so an IV-only prescription version does not change the answer for tablets) and ignores homeopathic products that only list an ingredient.

Rebuild after editing wording or adding a drug (first run needs internet; responses are cached in `data/openfda_cache/`, which is git-ignored):

```bash
python scripts/build_seed_from_openfda.py           # rewrites data/seed.json
python scripts/build_seed_from_openfda.py --check   # verify only
python scripts/seed_db.py                           # reload the local database
```

Set `OPENFDA_API_KEY` (free at open.fda.gov) if you hit rate limits.

Not included yet: over-the-counter cough and cold products such as dextromethorphan and guaifenesin, because their FDA labels list no side effects to confirm. `scripts/ingest_stub.py` (a DrugCentral placeholder) is no longer used.

## Ports and CORS

| Service  | URL |
|----------|-----|
| Frontend | http://127.0.0.1:41789 |
| Backend  | http://127.0.0.1:18765 |

The UI calls the API directly (`VITE_API_URL` in `frontend/.env`). FastAPI allows those localhost origins.

## Deploy as a web app

The label scanner does not require a Python OCR server. It uses the official
PaddleOCR.js browser SDK after a user captures a label: the photo remains in
the browser and the large OCR runtime downloads only when the scan begins.
The API receives the extracted text only to find matching medicines from this
app's dataset.

1. Deploy this repository's `Dockerfile` to any container host. Set `CORS_ORIGINS`
   to the comma-separated URL(s) where the web UI will be served, for example
   `https://medicines.example.com`.
2. Set `VITE_API_URL` to that API URL (see `frontend/.env.example`) and build
   the Vite app with `cd frontend && npm run build`.
3. Deploy `frontend/dist` to a static host such as Cloudflare Pages, Netlify,
   or Vercel. A camera requires HTTPS in production; `localhost` is the only
   normal development exception.

The browser still asks each visitor for camera permission. OCR is not an
identification or prescribing decision: the person must select a proposed
medicine before it can be added to their list.

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
