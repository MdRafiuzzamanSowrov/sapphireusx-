r"""Send one real Task 3 analysis alert to the development backend and verify deduplication.

PowerShell:
    $env:SAPPHIRE_API_URL = "http://127.0.0.1:8000"
    $env:ALERT_API_KEY = "<development-key>"  # keep this out of source control and chat
    .venv\Scripts\python.exe manual_backend_integration.py

Run this only against a development backend. The script uses the planted DEMO-03 SpO2
sample at 2026-11-04T10:20:00Z. Its external_id is deterministic, so repeated runs remain
idempotent. The script never prints or stores the API key.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

from ai.analysis import analyze_vitals
from ai.backend_adapter import build_backend_alert_requests


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "task1" / "simulated_vitals_long.zip"
API_URL = os.environ.get("SAPPHIRE_API_URL", "http://127.0.0.1:8000").rstrip("/")
API_KEY = os.environ.get("ALERT_API_KEY")


def call_api(method: str, path: str, body: dict | None = None) -> tuple[int, dict | list]:
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        headers["X-API-Key"] = API_KEY or ""
        data = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
    request = Request(f"{API_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"Backend returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(
            f"Cannot reach {API_URL}. Run this script on a machine that can access the "
            "development backend, or set SAPPHIRE_API_URL to its reachable address."
        ) from exc


def main() -> int:
    if not API_KEY:
        print("Set ALERT_API_KEY in your terminal first; the key is never printed by this script.", file=sys.stderr)
        return 2

    print("Running Task 3 analysis on SIMULATED DATA...")
    result = analyze_vitals(DATA)
    rows = result["measurements"]
    target_time = pd.Timestamp("2026-11-04T10:20:00Z")
    selected = rows[
        (rows["astronaut_code"] == "DEMO-03")
        & (rows["metric_code"] == "BLOOD_OXYGEN_SPO2")
        & (rows["measured_at"] == target_time)
        & rows["alert_priority"].notna()
    ]
    if selected.empty:
        print("The expected demo alert was not produced; no request was sent.", file=sys.stderr)
        return 3

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = build_backend_alert_requests(selected, generated_at=generated_at)[0]
    print(
        "Generated alert:",
        f"astronaut_id={body['astronaut_id']}, indicator={body.get('indicator_code')}, "
        f"severity={body['severity']}, external_id={body['external_id']}",
    )

    try:
        status1, first = call_api("POST", "/api/alerts", body)
        status2, second = call_api("POST", "/api/alerts", body)
        if status1 != 201 or status2 != 201:
            raise RuntimeError(f"Expected HTTP 201 for both POSTs; received {status1} and {status2}.")
        if first.get("id") != second.get("id") or second.get("created") is not False:
            raise RuntimeError(f"Duplicate check failed: first={first}, second={second}")

        _, alerts = call_api("GET", f"/api/astronauts/{body['astronaut_id']}/alerts")
        matches = [alert for alert in alerts if alert.get("external_id") == body["external_id"]]
        if len(matches) != 1:
            raise RuntimeError(f"Expected one stored alert with this external_id; found {len(matches)}.")
    except RuntimeError as exc:
        print(f"INTEGRATION TEST FAILED: {exc}", file=sys.stderr)
        return 4

    print(f"First POST:  HTTP {status1}, {first}")
    print(f"Second POST: HTTP {status2}, {second}")
    print(f"GET verification: found exactly one alert (id={matches[0]['id']}).")
    print("PASS: Task 3 generated alert was accepted and duplicate delivery was idempotent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
