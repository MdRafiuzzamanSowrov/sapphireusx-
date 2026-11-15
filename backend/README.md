# SapphireUSX Backend

FastAPI + SQLite backend for the SapphireUSX astronaut wellness check-in demo.
It stores health measurements, daily check-ins, and AI-generated alerts, and keeps
NASA research data in separate tables.

> Demo project. Sample/simulated data only. Not a medical device.

## Quick start

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # prompt should now show (venv)
pip install -r requirements.txt
python seed.py                    # creates sapphire.db with indicators + 14 days of simulated data
uvicorn main:app --reload --port 8000
```

- API docs and a "Try it out" panel: <http://localhost:8000/docs>
- Integrated React frontend (run in a second terminal): from `frontend/`, run `npm ci` then `npm run dev`, and open the Vite URL (usually <http://localhost:5173>). The root static HTML is a legacy demo.

Use the React frontend served by Vite; the static root HTML page is a legacy demo.

### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `ALERT_API_KEY` | `dev-alert-key` | Shared secret Member 3's service sends in the `X-API-Key` header |
| `SAPPHIRE_DB` | `backend/sapphire.db` | Path to the SQLite file |

```bash
ALERT_API_KEY="a-long-random-string" uvicorn main:app --reload --port 8000
```

Do not commit real keys. `sapphire.db` and `venv/` are git-ignored; each teammate seeds their own copy.

### Reset the database

Stop uvicorn first (`Ctrl+C`), then:

```bash
rm sapphire.db
python seed.py
uvicorn main:app --reload --port 8000
```

## Data model (`schema.sql`)

| Table | Purpose |
|---|---|
| `astronauts` | Pseudonymous crew members (seeded IDs listed below) |
| `indicators` | Catalog of health indicators: code, canonical unit, valid range, normal range, status |
| `data_sources` | Where data comes from. `kind` is `self_report`, `simulated` or `sensor` |
| `measurements` | Append-only time series (indicator, value, unit, `measured_at`, source, quality) |
| `checkins` | Daily check-in form entries, including free-text symptoms |
| `alerts` | AI-generated alerts (severity, message, model info, confidence, evidence, status) |
| `nasa_datasets`, `nasa_reference_values` | NASA research/reference data, kept completely separate |

### Seeded astronauts (stable IDs)

| id | code | Simulated profile |
|---|---|---|
| 1 | `CDR-01` | baseline |
| 2 | `DEMO-01` | well rested, active |
| 3 | `DEMO-02` | short sleep |
| 4 | `DEMO-03` | low hydration |
| 5 | `DEMO-04` | low activity |

All history for these astronauts is `simulated` (source `sim_generator_v1`), 14 days each. `python seed.py` is safe to re-run on an existing database: it adds any missing astronauts and their history and leaves existing data alone.

### Measurement format

Every measurement has:

| Field | Example | Notes |
|---|---|---|
| `indicator_code` | `heart_rate` | Must exist in `indicators` |
| `value` | `72` | Number. Must be inside the indicator's valid range |
| `unit` | `bpm` | Must equal the indicator's canonical unit, otherwise 422 |
| `measured_at` | `2026-11-15T08:00:00Z` | ISO-8601, UTC, with `Z` |
| source | `wearable_demo` | A name from `data_sources`; its `kind` tells you if it is self-reported, simulated or sensor data |

Sending the same (astronaut, indicator, `measured_at`, source) twice is ignored, so retries are safe.

### NASA data separation

NASA research data never goes into `measurements`. Measurements can only reference a
crew data source (`self_report`, `simulated`, `sensor`). NASA values live in
`nasa_reference_values` (linked to `nasa_datasets` for title, URL, citation, license) and are
only exposed through `GET /api/reference/{indicator}`.

## API reference

Base URL: `http://localhost:8000`. All bodies and responses are JSON.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness check |
| GET | `/api/indicators` | Indicator catalog |
| GET | `/api/astronauts/{id}/summary` | Latest value per indicator (dashboard cards) |
| GET | `/api/astronauts/{id}/measurements` | Raw measurements. Query: `indicator`, `start`, `end`, `source_kind`, `limit` |
| GET | `/api/astronauts/{id}/history/{indicator}` | History for charts. Query: `bucket` = `day` (default), `hour`, `raw`; `start`, `end` |
| POST | `/api/checkins` | Daily check-in from the frontend form |
| POST | `/api/measurements` | Batch of sensor/simulated measurements |
| POST | `/api/alerts` | Create an AI alert (requires `X-API-Key`) |
| GET | `/api/astronauts/{id}/alerts` | List alerts. Query: `status`, `limit` |
| PATCH | `/api/alerts/{alert_id}` | Set status: `acknowledged`, `dismissed`, `resolved`, `new` |
| GET | `/api/reference/{indicator}` | NASA reference values for an indicator |

Errors: `401` bad API key, `404` not found, `422` validation failure (unknown indicator, wrong unit, value out of range, malformed body).

### Examples

Check-in (frontend):
```bash
curl -X POST http://localhost:8000/api/checkins -H "Content-Type: application/json" \
  -d '{"astronaut_id":1,"sleep_hours":7.5,"mood":"Okay","symptoms":"none"}'
```
`mood` is `Great`, `Okay` or `Low` (stored as scores 3, 2, 1 under `mood_score`). A check-in creates `sleep_hours` and `mood_score` measurements with source `frontend_checkin`.

Sensor or simulator data:
```bash
curl -X POST http://localhost:8000/api/measurements -H "Content-Type: application/json" \
  -d '{"astronaut_id":1,"source":"wearable_demo","measurements":[
        {"indicator_code":"heart_rate","value":72,"unit":"bpm","measured_at":"2026-11-15T08:00:00Z"}]}'
```
Response: `{"inserted":1,"duplicates_ignored":0}`

Dashboard summary and chart data:
```bash
curl http://localhost:8000/api/astronauts/1/summary
curl "http://localhost:8000/api/astronauts/1/history/sleep_hours?bucket=day"
```
Summary only lists indicators that have at least one measurement. Handle a missing indicator in the UI.

## For Member 3: sending AI alerts

`POST /api/alerts` with header `X-API-Key: <ALERT_API_KEY>`.

```json
{
  "external_id": "ai-2026-11-15-001",
  "astronaut_id": 1,
  "indicator_code": "sleep_hours",
  "severity": "watch",
  "title": "Low sleep trend",
  "message": "Sleep has been below 7 hours for 3 days.",
  "model_name": "sleep-trend-model",
  "model_version": "0.1",
  "confidence": 0.82,
  "evidence": {"window_days": 3, "measurement_ids": [101, 108, 115]},
  "generated_at": "2026-11-15T08:00:00Z"
}
```

| Field | Required | Notes |
|---|---|---|
| `astronaut_id`, `severity`, `title`, `message`, `generated_at` | yes | `severity` is `info`, `watch`, `warning` or `critical` |
| `external_id` | recommended | Your own unique id. Re-sending the same one returns `{"created": false}` instead of a duplicate |
| `indicator_code` | no | Leave out for alerts spanning several indicators |
| `model_name`, `model_version`, `confidence`, `evidence` | no | `confidence` is 0 to 1. `evidence` is any JSON object |

Response: `{"id": 1, "created": true}`. Wrong key returns `401`.

## For Member 2: using the API from the frontend

- The React check-in form sends `POST /api/checkins`; submitted sleep and mood measurements are stored for demo astronaut 1.
- The Overview and Trends views read `/api/astronauts/1/summary` and `/api/astronauts/1/history/{indicator}`.
- The Alerts view reads alerts from all five seeded astronaut profiles and saves status changes with `PATCH /api/alerts/{id}`.
- Run `task3-ai/manual_backend_integration.py` to generate and send a simulated Task 3 alert; it will appear in Alerts.
- CORS is open for the demo, so a frontend on another port works.

## For Member 1: updating the health indicators

Indicators live in the `indicators` table, seeded from the `INDICATORS` list in `seed.py`
(code, name, category, unit, min_valid, max_valid, ref_low, ref_high). The current list is a
**temporary draft**. When the final list is agreed, edit that list and re-seed
(see "Reset the database"). Changing an indicator's unit later means existing data in the old unit must be converted or cleared.

## Project layout

```
backend/
  schema.sql        database tables
  db.py             all database logic
  main.py           FastAPI routes
  seed.py           indicators, sources, and sample simulated data
  requirements.txt
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `uvicorn: command not found` | Activate the venv: `source venv/bin/activate` |
| `Address already in use` | uvicorn is already running in another terminal; stop it with `Ctrl+C` |
| Browser shows `{"detail":"Not Found"}` at `:8000` | Expected. Use `/docs` for the API, `:5500` for the website |
| Deleted `sapphire.db` but data looks old | Restart uvicorn after deleting and re-seeding |
| Form says "Could not save check-in" | Is uvicorn running? Check the browser console (F12) and the uvicorn log |
