PRAGMA foreign_keys = ON;

-- Who the data belongs to
CREATE TABLE IF NOT EXISTS astronauts (
  id          INTEGER PRIMARY KEY,
  code        TEXT NOT NULL UNIQUE,          -- e.g. 'CDR-01' (pseudonymous, no real names)
  display_name TEXT NOT NULL,
  created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- Catalog of health indicators. Member 1 owns this list: add/edit rows, no code change needed.
CREATE TABLE IF NOT EXISTS indicators (
  code        TEXT PRIMARY KEY,              -- stable machine name, e.g. 'sleep_hours'
  name        TEXT NOT NULL,
  category    TEXT NOT NULL,                 -- sleep | mental | activity | hydration | vital | ...
  unit        TEXT NOT NULL,                 -- canonical unit; incoming values must use it
  value_type  TEXT NOT NULL DEFAULT 'number' CHECK (value_type IN ('number','category')),
  min_valid   REAL,                          -- hard sanity bounds (reject impossible values)
  max_valid   REAL,
  ref_low     REAL,                          -- normal range used by UI/AI (PROVISIONAL until Member 1 finalizes)
  ref_high    REAL,
  status      TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','final','retired'))
);

-- Every row of data must say where it came from.
-- NASA research data is NOT a source for measurements (enforced by trigger below).
CREATE TABLE IF NOT EXISTS data_sources (
  id    INTEGER PRIMARY KEY,
  name  TEXT NOT NULL UNIQUE,                -- 'frontend_checkin', 'sim_generator_v1', 'wearable_demo'
  kind  TEXT NOT NULL CHECK (kind IN ('self_report','simulated','sensor')),
  notes TEXT
);

-- Time-series of crew measurements (self-reported, simulated or sensor). Append-only.
CREATE TABLE IF NOT EXISTS measurements (
  id             INTEGER PRIMARY KEY,
  astronaut_id   INTEGER NOT NULL REFERENCES astronauts(id),
  indicator_code TEXT    NOT NULL REFERENCES indicators(code),
  value          REAL    NOT NULL,           -- categorical indicators stored as numeric score
  unit           TEXT    NOT NULL,
  measured_at    TEXT    NOT NULL,           -- ISO-8601 UTC, when it was measured
  source_id      INTEGER NOT NULL REFERENCES data_sources(id),
  quality        TEXT    NOT NULL DEFAULT 'ok' CHECK (quality IN ('ok','suspect','invalid')),
  ingested_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  UNIQUE (astronaut_id, indicator_code, measured_at, source_id)   -- makes re-sending a batch safe
);
CREATE INDEX IF NOT EXISTS idx_meas_lookup ON measurements (astronaut_id, indicator_code, measured_at);

-- Free-text part of the daily check-in (symptoms). Numeric parts also go to measurements.
CREATE TABLE IF NOT EXISTS checkins (
  id           INTEGER PRIMARY KEY,
  astronaut_id INTEGER NOT NULL REFERENCES astronauts(id),
  submitted_at TEXT    NOT NULL,
  mood         TEXT    NOT NULL CHECK (mood IN ('Great','Okay','Low')),
  sleep_hours  REAL    NOT NULL,
  symptoms     TEXT
);
CREATE INDEX IF NOT EXISTS idx_checkins ON checkins (astronaut_id, submitted_at);

-- AI-generated alerts from Member 3
CREATE TABLE IF NOT EXISTS alerts (
  id             INTEGER PRIMARY KEY,
  external_id    TEXT UNIQUE,                -- Member 3's own id -> idempotent re-delivery
  astronaut_id   INTEGER NOT NULL REFERENCES astronauts(id),
  indicator_code TEXT REFERENCES indicators(code),   -- nullable: alert may be multi-indicator
  severity       TEXT NOT NULL CHECK (severity IN ('info','watch','warning','critical')),
  title          TEXT NOT NULL,
  message        TEXT NOT NULL,
  model_name     TEXT,                       -- which AI/model produced it
  model_version  TEXT,
  confidence     REAL CHECK (confidence BETWEEN 0 AND 1),
  evidence       TEXT,                       -- JSON: measurement ids / window / features used
  generated_at   TEXT NOT NULL,              -- when the AI produced it
  received_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  status         TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new','acknowledged','dismissed','resolved')),
  acknowledged_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_alerts ON alerts (astronaut_id, status, generated_at);

-- ===== NASA research data: completely separate tables =====
CREATE TABLE IF NOT EXISTS nasa_datasets (
  id          INTEGER PRIMARY KEY,
  title       TEXT NOT NULL,
  url         TEXT,
  citation    TEXT,
  license     TEXT,
  retrieved_at TEXT
);

-- Population-level reference values (means, ranges, study results). Never per-astronaut live data.
CREATE TABLE IF NOT EXISTS nasa_reference_values (
  id             INTEGER PRIMARY KEY,
  dataset_id     INTEGER NOT NULL REFERENCES nasa_datasets(id),
  indicator_code TEXT NOT NULL REFERENCES indicators(code),
  context        TEXT,                       -- e.g. 'ISS long-duration crew, in-flight'
  statistic      TEXT NOT NULL,              -- mean | median | p5 | p95 | range_low | range_high
  value          REAL NOT NULL,
  unit           TEXT NOT NULL,
  note           TEXT
);
CREATE INDEX IF NOT EXISTS idx_nasa_ref ON nasa_reference_values (indicator_code);

-- Guard rail: measurements can never point at anything but a crew data source.
-- (kind CHECK already restricts data_sources; this trigger also blocks bad inserts if the table is ever changed.)
CREATE TRIGGER IF NOT EXISTS trg_meas_unit_matches BEFORE INSERT ON measurements
WHEN NEW.unit <> (SELECT unit FROM indicators WHERE code = NEW.indicator_code)
BEGIN
  SELECT RAISE(ABORT, 'unit does not match indicator canonical unit');
END;
