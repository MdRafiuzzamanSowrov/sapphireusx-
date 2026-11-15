"""Regression coverage for screening, orchestration, OSD-575, experiment and plots."""
import pandas as pd
from functools import lru_cache

from ai.analysis import analysis_to_payload, analyze_vitals
from ai.backend_adapter import (BACKEND_SEED_ASTRONAUT_IDS, BACKEND_SEED_INDICATORS,
                                build_backend_alert_requests)
from ai.detectors import detect
from ai.experimental import isolation_forest_experiment
from ai.evaluation import evaluate_planted_alerts
from ai.loader import load_metric_table, load_reference_ranges
from ai.osd575 import DATA_LABEL, load_osd575, summarize_osd575
from ai.plots import plot_osd575
from ai.loader import load_planted_events

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def full_simulated_evaluation():
    result = analyze_vitals(ROOT / "data/task1/simulated_vitals_long.zip")
    return evaluate_planted_alerts(result["measurements"],
                                   load_planted_events(ROOT / "data/task1/planted_events.csv"))


def rows(items):
    result = []
    for i, (metric, value, context, status) in enumerate(items):
        unit = {"HEART_RATE": "bpm", "BLOOD_OXYGEN_SPO2": "%", "SYMPTOM_HEADACHE": "yes_no",
                "RESPIRATORY_RATE": "breaths/min", "BODY_TEMPERATURE": "degC",
                "EXERCISE_TIME": "min/day"}[metric]
        result.append({
            "row_id": i, "astronaut_code": "DEMO-01", "metric_code": metric, "value": value,
            "unit": unit, "measured_at": pd.Timestamp("2026-11-01T10:00:00Z") + pd.Timedelta(minutes=i),
            "context": context, "device_quality_status": status, "source_type": "synthetic",
            "collection_method": "sensor", "source_note": "fixture",
        })
    return pd.DataFrame(result)


def test_detector_context_and_device_quality_gates():
    frame = rows([("HEART_RATE", 142, "exercise", "valid"),
                  ("RESPIRATORY_RATE", 32, "exercise", "valid"),
                  ("BODY_TEMPERATURE", 37.7, "recovery", "valid"),
                  ("HEART_RATE", 135, "awake", "valid"),
                  ("BLOOD_OXYGEN_SPO2", 85, "awake", "invalid")])
    screened = detect(frame.assign(quality_status=["valid", "valid", "valid", "valid", "invalid"]),
                      load_reference_ranges(ROOT / "data/task1/reference_ranges.csv"))
    assert screened.loc[:2, "alert_priority"].isna().all()
    assert screened.loc[3, "alert_priority"] == "HIGH"
    assert pd.isna(screened.loc[4, "alert_priority"])
    assert screened.loc[4, "detector_findings"] == []


def test_symptom_is_explained_and_labeled():
    frame = rows([("SYMPTOM_HEADACHE", 1, "awake", "valid")]).assign(quality_status="valid")
    out = detect(frame, load_reference_ranges(ROOT / "data/task1/reference_ranges.csv"))
    assert out.loc[0, "alert_priority"] == "MEDIUM"
    assert out.loc[0, "data_label"] == "SIMULATED DATA"
    assert out.loc[0, "detector_findings"][0]["detector"] == "reported_symptom"


def test_personal_baseline_deviation_is_directional_and_low_priority():
    frame = rows([("EXERCISE_TIME", 10, "not_applicable", "valid")]).assign(
        quality_status="valid", baseline_status="ok", baseline_median=60.0,
        baseline_scale=10.0, baseline_n=8)
    frame["unit"] = "min/day"
    out = detect(frame, load_reference_ranges(ROOT / "data/task1/reference_ranges.csv"),
                 metric_rules=load_metric_table(ROOT / "data/task1/metric_table.csv"))
    assert out.loc[0, "alert_priority"] == "LOW"
    finding = next(f for f in out.loc[0, "detector_findings"]
                   if f["detector"] == "personal_baseline_deviation")
    assert finding["robust_z"] == -5.0


def test_personal_heart_rate_baseline_never_alerts_in_sleep_or_exercise():
    frame = rows([("HEART_RATE", 140, "exercise", "valid"),
                  ("HEART_RATE", 42, "asleep", "valid"),
                  ("HEART_RATE", 140, "awake", "valid")]).assign(
        quality_status="valid", baseline_status="ok", baseline_median=70.0,
        baseline_scale=5.0, baseline_n=100)
    out = detect(frame, load_reference_ranges(ROOT / "data/task1/reference_ranges.csv"),
                 metric_rules=load_metric_table(ROOT / "data/task1/metric_table.csv"))
    assert out.loc[:1, "alert_priority"].isna().all()
    assert out.loc[2, "alert_priority"] == "HIGH"


def test_analysis_payload_is_json_safe_and_separates_exclusions():
    frame = rows([("HEART_RATE", 135, "awake", "valid"),
                  ("HEART_RATE", 0, "awake", "valid")])
    result = analyze_vitals(frame, reference_ranges=load_reference_ranges(ROOT / "data/task1/reference_ranges.csv"))
    payload = analysis_to_payload(result)
    assert payload["schema_version"] == "1.0"
    assert len(payload["measurements"]) == 2
    assert payload["measurements"][1]["quality_status"] == "invalid"
    assert payload["measurements"][1]["dq_reasons"] == "impossible_value"
    assert "baseline_status" in payload["measurements"][0]
    assert len(payload["alerts"]) == 1
    assert payload["alerts"][0]["priority"] == "HIGH"
    assert len(result["excluded"]) == 1


def test_backend_adapter_matches_readme_contract_and_uses_seed_id_mapping_by_default():
    result = analyze_vitals(
        rows([("HEART_RATE", 135, "awake", "valid")]),
        reference_ranges=load_reference_ranges(ROOT / "data/task1/reference_ranges.csv"),
    )
    with __import__("pytest").raises(ValueError, match="no backend astronaut_id mapping"):
        build_backend_alert_requests(result["measurements"], {}, {"HEART_RATE": "heart_rate"},
                                    generated_at="2026-11-15T10:00:00Z")
    bodies = build_backend_alert_requests(
        result["measurements"], generated_at="2026-11-15T10:00:00Z")
    assert len(bodies) == 1
    body = bodies[0]
    assert body["astronaut_id"] == 2
    assert body["severity"] == "critical"
    assert body["indicator_code"] == "heart_rate"
    assert body["model_name"] == "sapphireusx-task3-rules"
    assert body["evidence"]["data_label"] == "SIMULATED DATA"
    assert BACKEND_SEED_ASTRONAUT_IDS == {"CDR-01": 1, "DEMO-01": 2, "DEMO-02": 3,
                                         "DEMO-03": 4, "DEMO-04": 5}
    seeded_body = build_backend_alert_requests(
        result["measurements"], generated_at="2026-11-15T10:00:00Z")[0]
    assert seeded_body["astronaut_id"] == 2
    temp_result = analyze_vitals(
        rows([("BODY_TEMPERATURE", 42.0, "awake", "valid")]),
        reference_ranges=load_reference_ranges(ROOT / "data/task1/reference_ranges.csv"),
    )
    temp_body = build_backend_alert_requests(
        temp_result["measurements"], generated_at="2026-11-15T10:00:00Z")[0]
    assert temp_body["indicator_code"] == "body_temp"
    assert temp_body["evidence"]["unit"] == "°C"
    assert BACKEND_SEED_INDICATORS["BODY_TEMPERATURE"] == ("body_temp", "°C")


def test_backend_adapter_omits_unseeded_indicator_but_keeps_source_metric_in_evidence():
    result = analyze_vitals(
        rows([("EXERCISE_TIME", 0, "not_applicable", "valid")]),
        reference_ranges=load_reference_ranges(ROOT / "data/task1/reference_ranges.csv"),
    )
    frame = result["measurements"].copy()
    frame.loc[0, "alert_priority"] = "LOW"
    frame.loc[0, "detector_findings"] = [[{"detector": "personal_baseline_deviation",
                                            "source_label": "Outside personal baseline"}]]
    body = build_backend_alert_requests(frame, {"DEMO-01": 1}, generated_at="2026-11-15T10:00:00Z")[0]
    assert "indicator_code" not in body
    assert body["evidence"]["task3_metric_code"] == "EXERCISE_TIME"
    assert body["evidence"]["unit"] == "min/day"


def test_osd575_is_separate_descriptive_real_research_data():
    frame = load_osd575(ROOT / "data/osd575/LSDS-8_Multiplex_serum_cardiovascular_EvePanel_TRANSFORMED.csv")
    summary = summarize_osd575(ROOT / "data/osd575/LSDS-8_Multiplex_serum_cardiovascular_EvePanel_TRANSFORMED.csv")
    assert frame.shape == (252, 6)
    assert frame.analyte.nunique() == 9
    assert set(frame.data_label) == {DATA_LABEL}
    assert set(summary.samples) == {28}
    assert "alert_priority" not in summary.columns


def test_isolation_forest_is_experimental_and_drops_nonvalid_rows():
    frame = pd.DataFrame({
        "quality_status": ["valid"] * 40 + ["invalid"],
        "metric_code": ["HEART_RATE"] * 41,
        "value": list(range(40)) + [10000],
        "astronaut_code": ["DEMO-01"] * 41,
        "measured_at": list(pd.date_range("2026-11-01", periods=41, freq="min", tz="UTC")),
    })
    events = pd.DataFrame(columns=["category", "participant_id", "metric_codes", "start", "end"])
    scored, summary = isolation_forest_experiment(frame, planted_events=events, random_state=2)
    assert len(scored) == 40
    assert scored.experimental_label.eq("SIMULATED DATA").all()
    assert summary.loc[0, "severity_effect"] == "none"
    assert "alert_priority" not in scored.columns


def test_planted_event_evaluation_counts_coverage_and_unassociated_alerts():
    screened = pd.DataFrame({
        "astronaut_code": ["D1", "D1", "D1"],
        "metric_code": ["HEART_RATE"] * 3,
        "measured_at": pd.date_range("2026-11-01T00:00:00Z", periods=3, freq="h"),
        "alert_priority": ["HIGH", None, "LOW"],
    })
    events = pd.DataFrame([{
        "event_id": "E1", "category": "health_event", "participant_id": "D1",
        "metric_codes": ["HEART_RATE"], "start": pd.Timestamp("2026-11-01T00:00:00Z"),
        "end": pd.Timestamp("2026-11-01T01:00:00Z"),
    }])
    report = evaluate_planted_alerts(screened, events)
    assert report["summary"].loc[0, "detected_events"] == 1
    assert report["events"].loc[0, "event_detected"]
    assert len(report["unassociated_alerts"]) == 1


def test_full_simulated_rule_pipeline_covers_the_planted_alert_windows():
    report = full_simulated_evaluation()
    assert report["summary"].loc[0, "label"] == "SIMULATED DATA"
    assert report["summary"].loc[0, "expected_events"] == 10
    assert report["summary"].loc[0, "detected_events"] == 10
    e05 = report["events"].set_index("event_id").loc["E05"]
    assert e05["event_detected"]


def test_osd575_plot_writes_an_image(tmp_path):
    output = plot_osd575(summarize_osd575(), tmp_path / "panel.png")
    assert output.is_file() and output.stat().st_size > 0
