import json, os, sqlite3
from datetime import datetime, timezone

DB_PATH = os.environ.get("SAPPHIRE_DB", os.path.join(os.path.dirname(__file__), "sapphire.db"))
SCHEMA = os.path.join(os.path.dirname(__file__), "schema.sql")

def now_iso(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def connect(path=None):
    c = sqlite3.connect(path or DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c

def init(c):
    with open(SCHEMA) as f: c.executescript(f.read())
    c.commit()

class ValidationError(ValueError): pass

def _source_id(c, name):
    r = c.execute("SELECT id FROM data_sources WHERE name=?", (name,)).fetchone()
    if not r: raise ValidationError(f"unknown data source '{name}'")
    return r["id"]

def add_measurements(c, astronaut_id, source, items):
    """items: dicts with indicator_code, value, unit, measured_at. Returns (inserted, duplicates)."""
    sid = _source_id(c, source)
    if not c.execute("SELECT 1 FROM astronauts WHERE id=?", (astronaut_id,)).fetchone():
        raise ValidationError("unknown astronaut")
    ind = {r["code"]: r for r in c.execute("SELECT * FROM indicators WHERE status<>'retired'")}
    inserted = dup = 0
    for it in items:                                  # validate everything first
        i = ind.get(it["indicator_code"])
        if not i: raise ValidationError(f"unknown indicator '{it['indicator_code']}'")
        if it["unit"] != i["unit"]: raise ValidationError(f"{i['code']}: unit must be '{i['unit']}'")
        v = it["value"]
        if (i["min_valid"] is not None and v < i["min_valid"]) or (i["max_valid"] is not None and v > i["max_valid"]):
            raise ValidationError(f"{i['code']}: value {v} outside valid range")
    for it in items:
        cur = c.execute("""INSERT OR IGNORE INTO measurements
            (astronaut_id,indicator_code,value,unit,measured_at,source_id) VALUES (?,?,?,?,?,?)""",
            (astronaut_id, it["indicator_code"], it["value"], it["unit"], it["measured_at"], sid))
        inserted += cur.rowcount; dup += 1 - cur.rowcount
    c.commit()
    return inserted, dup

def query_measurements(c, astronaut_id, indicator=None, start=None, end=None, source_kind=None, limit=500):
    sql = """SELECT m.id, m.indicator_code, m.value, m.unit, m.measured_at, s.name AS source, s.kind AS source_kind, m.quality
             FROM measurements m JOIN data_sources s ON s.id=m.source_id
             WHERE m.astronaut_id=? AND m.quality<>'invalid'"""
    a = [astronaut_id]
    for cond, val in (("m.indicator_code=?", indicator), ("m.measured_at>=?", start),
                      ("m.measured_at<=?", end), ("s.kind=?", source_kind)):
        if val: sql += " AND " + cond; a.append(val)
    sql += " ORDER BY m.measured_at DESC LIMIT ?"; a.append(min(limit, 5000))
    return [dict(r) for r in c.execute(sql, a)]

def latest(c, astronaut_id):
    """Most recent value per indicator + its normal range -> powers the dashboard cards."""
    sql = """SELECT i.code AS indicator_code, i.name, i.unit, i.ref_low, i.ref_high,
                    m.value, m.measured_at, s.kind AS source_kind
             FROM indicators i
             JOIN measurements m ON m.id = (SELECT id FROM measurements
                    WHERE astronaut_id=? AND indicator_code=i.code AND quality='ok'
                    ORDER BY measured_at DESC LIMIT 1)
             JOIN data_sources s ON s.id=m.source_id
             WHERE i.status<>'retired'"""
    return [dict(r) for r in c.execute(sql, (astronaut_id,))]

def history(c, astronaut_id, indicator, start=None, end=None, bucket="day"):
    fmt = {"day": "%Y-%m-%d", "hour": "%Y-%m-%dT%H:00:00Z", "raw": None}[bucket]
    if fmt is None:
        return query_measurements(c, astronaut_id, indicator, start, end, limit=5000)[::-1]
    sql = f"""SELECT strftime('{fmt}', measured_at) AS bucket, ROUND(AVG(value),2) AS avg,
                     MIN(value) AS min, MAX(value) AS max, COUNT(*) AS n
              FROM measurements WHERE astronaut_id=? AND indicator_code=? AND quality='ok'"""
    a = [astronaut_id, indicator]
    if start: sql += " AND measured_at>=?"; a.append(start)
    if end:   sql += " AND measured_at<=?"; a.append(end)
    sql += " GROUP BY bucket ORDER BY bucket"
    return [dict(r) for r in c.execute(sql, a)]

MOOD = {"Low": 1, "Okay": 2, "Great": 3}
def add_checkin(c, astronaut_id, sleep_hours, mood, symptoms, submitted_at=None):
    t = submitted_at or now_iso()
    c.execute("INSERT INTO checkins (astronaut_id,submitted_at,mood,sleep_hours,symptoms) VALUES (?,?,?,?,?)",
              (astronaut_id, t, mood, sleep_hours, (symptoms or "").strip() or None))
    c.commit()
    add_measurements(c, astronaut_id, "frontend_checkin", [
        dict(indicator_code="sleep_hours", value=sleep_hours, unit="hours", measured_at=t),
        dict(indicator_code="mood_score",  value=MOOD[mood],  unit="score", measured_at=t)])
    return t

def add_alert(c, a):
    """Idempotent on external_id. Returns (alert_id, created)."""
    if a.get("external_id"):
        r = c.execute("SELECT id FROM alerts WHERE external_id=?", (a["external_id"],)).fetchone()
        if r: return r["id"], False
    if not c.execute("SELECT 1 FROM astronauts WHERE id=?", (a["astronaut_id"],)).fetchone():
        raise ValidationError("unknown astronaut")
    if a.get("indicator_code") and not c.execute("SELECT 1 FROM indicators WHERE code=?", (a["indicator_code"],)).fetchone():
        raise ValidationError(f"unknown indicator '{a['indicator_code']}'")
    cur = c.execute("""INSERT INTO alerts (external_id,astronaut_id,indicator_code,severity,title,message,
                       model_name,model_version,confidence,evidence,generated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (a.get("external_id"), a["astronaut_id"], a.get("indicator_code"), a["severity"], a["title"], a["message"],
         a.get("model_name"), a.get("model_version"), a.get("confidence"),
         json.dumps(a["evidence"]) if a.get("evidence") is not None else None, a["generated_at"]))
    c.commit()
    return cur.lastrowid, True

def list_alerts(c, astronaut_id, status=None, limit=50):
    sql, a = "SELECT * FROM alerts WHERE astronaut_id=?", [astronaut_id]
    if status: sql += " AND status=?"; a.append(status)
    sql += " ORDER BY generated_at DESC LIMIT ?"; a.append(limit)
    out = [dict(r) for r in c.execute(sql, a)]
    for r in out:
        if r["evidence"]: r["evidence"] = json.loads(r["evidence"])
    return out

def set_alert_status(c, alert_id, status):
    cur = c.execute("UPDATE alerts SET status=?, acknowledged_at=? WHERE id=?",
                    (status, now_iso() if status != "new" else None, alert_id))
    c.commit(); return cur.rowcount > 0

def nasa_reference(c, indicator):
    return [dict(r) for r in c.execute("""SELECT v.context, v.statistic, v.value, v.unit, v.note,
              d.title AS dataset, d.url, d.citation FROM nasa_reference_values v
              JOIN nasa_datasets d ON d.id=v.dataset_id WHERE v.indicator_code=?""", (indicator,))]
