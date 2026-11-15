# SapphireUSX

SapphireUSX is a crew-wellness interface prototype. The React and TypeScript
application in `frontend/` is the integrated version. A legacy static HTML demo
remains at the repository root; use `frontend/` for backend-connected screens.

## Run the React app

Requires Node.js and npm. To submit check-ins, start the backend first in a
separate terminal (see `backend/README.md`), then run the frontend:

```sh
cd frontend
npm ci
npm run dev
```

The check-in form sends `POST /api/checkins` to `http://127.0.0.1:8000` by
default. Set `VITE_API_BASE_URL` before starting Vite to use another backend URL.
Overview, Trends, Sources, and Alerts read stored backend data. Alerts covers all
five demo profiles and saves acknowledge/dismiss actions. The Task 3 integration
script sends simulated AI alerts, which appear in the Alerts view. Seeded records
are simulated; submitted check-ins are self-reported.

## Run and verify the local integration on Windows

Start the backend in the first PowerShell terminal:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe seed.py
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

Start the frontend in a second terminal using the commands above. Open the Vite
URL, choose **Check-in**, enter sleep, mood, and symptoms, then submit. The page
should confirm that the check-in was saved. Verify it through
`http://127.0.0.1:8000/api/astronauts/1/measurements?source_kind=self_report&limit=10`.

To verify AI-to-backend alert delivery, use a third terminal while the backend is
running:

```powershell
cd task3-ai
$env:SAPPHIRE_API_URL = "http://127.0.0.1:8000"
$env:ALERT_API_KEY = "dev-alert-key"
.\.venv\Scripts\python.exe manual_backend_integration.py
```

The expected final line is `PASS: Task 3 generated alert was accepted and duplicate delivery was idempotent.`

For a production build and lint check:

```sh
npm run build
npm run lint
```

## Data and prototype notice

Seeded readings and AI integration examples use simulated data; check-ins are self-reported entries in a local demo database. These are not live spacecraft measurements and are not for health monitoring, diagnosis, or treatment decisions. NASA OSDR study OSD-575 remains a separate research reference.
SapphireUSX is not an official NASA product.
