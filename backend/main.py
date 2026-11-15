"""SapphireUSX backend. Run:  uvicorn main:app --reload --port 8000"""
import os, secrets
from typing import Literal, Optional
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import db

app = FastAPI(title="SapphireUSX API", version="0.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])  
conn = db.connect(); db.init(conn)

ALERT_KEY = os.environ.get("ALERT_API_KEY", "dev-alert-key")   

def require_key(x_api_key: str = Header(default="")):
    """Runs BEFORE body validation, so a wrong key always gets 401."""
    if not secrets.compare_digest(x_api_key, ALERT_KEY):
        raise HTTPException(401, "bad API key")

def check(fn, *a, **k):
    try: return fn(conn, *a, **k)
    except db.ValidationError as e: raise HTTPException(422, str(e))

class MeasurementIn(BaseModel):
    indicator_code: str
    value: float
    unit: str
    measured_at: str                       

class MeasurementBatch(BaseModel):
    astronaut_id: int
    source: str                            
    measurements: list[MeasurementIn] = Field(min_length=1, max_length=1000)

class CheckinIn(BaseModel):
    astronaut_id: int = 1
    sleep_hours: float = Field(ge=0, le=24)
    mood: Literal["Great", "Okay", "Low"]
    symptoms: Optional[str] = Field(default=None, max_length=1000)

class AlertIn(BaseModel):
    external_id: Optional[str] = None
    astronaut_id: int
    indicator_code: Optional[str] = None
    severity: Literal["info", "watch", "warning", "critical"]
    title: str
    message: str
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    evidence: Optional[dict] = None
    generated_at: str

class AlertStatus(BaseModel):
    status: Literal["acknowledged", "dismissed", "resolved", "new"]

@app.get("/api/health")
def health(): return {"ok": True}

@app.get("/api/indicators")
def indicators():
    return [dict(r) for r in conn.execute("SELECT * FROM indicators WHERE status<>'retired'")]

@app.post("/api/measurements", status_code=201)
def post_measurements(b: MeasurementBatch):
    ins, dup = check(db.add_measurements, b.astronaut_id, b.source, [m.model_dump() for m in b.measurements])
    return {"inserted": ins, "duplicates_ignored": dup}

@app.get("/api/astronauts/{aid}/summary")
def summary(aid: int): return {"astronaut_id": aid, "latest": db.latest(conn, aid)}

@app.get("/api/astronauts/{aid}/measurements")
def measurements(aid: int, indicator: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None,
                 source_kind: Optional[Literal["self_report", "simulated", "sensor"]] = None, limit: int = 500):
    return db.query_measurements(conn, aid, indicator, start, end, source_kind, limit)

@app.get("/api/astronauts/{aid}/history/{indicator}")
def history(aid: int, indicator: str, start: Optional[str] = None, end: Optional[str] = None,
            bucket: Literal["raw", "hour", "day"] = "day"):
    return db.history(conn, aid, indicator, start, end, bucket)

@app.post("/api/checkins", status_code=201)
def post_checkin(c: CheckinIn):
    return {"submitted_at": check(db.add_checkin, c.astronaut_id, c.sleep_hours, c.mood, c.symptoms)}

@app.post("/api/alerts", status_code=201, dependencies=[Depends(require_key)])   
def post_alert(a: AlertIn):
    aid, created = check(db.add_alert, a.model_dump())
    return {"id": aid, "created": created}

@app.get("/api/astronauts/{aid}/alerts")
def alerts(aid: int, status: Optional[str] = None, limit: int = 50):
    return db.list_alerts(conn, aid, status, limit)

@app.patch("/api/alerts/{alert_id}")
def patch_alert(alert_id: int, s: AlertStatus):
    if not db.set_alert_status(conn, alert_id, s.status): raise HTTPException(404, "alert not found")
    return {"id": alert_id, "status": s.status}

@app.get("/api/reference/{indicator}")             
def reference(indicator: str): return db.nasa_reference(conn, indicator)
