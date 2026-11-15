"""Descriptive-only analysis of the OSD-575 cardiovascular serum panel.

This periodic laboratory dataset is kept separate from continuous vital monitoring.
All output carries the REAL NASA RESEARCH DATA provenance label.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_LABEL = "REAL NASA RESEARCH DATA"
_PREFIX = "data/osd575/LSDS-8_Multiplex_serum_cardiovascular_EvePanel_TRANSFORMED.csv"


def load_osd575(path=None) -> pd.DataFrame:
    """Load the 9 concentration measures as a long descriptive table (28 samples)."""
    path = Path(path) if path else Path(__file__).resolve().parents[1] / _PREFIX
    wide = pd.read_csv(path)
    sample_col = "Sample Name"
    concentration_cols = [c for c in wide.columns if "_concentration_" in c]
    if sample_col not in wide or len(concentration_cols) != 9:
        raise ValueError("OSD-575 file must contain Sample Name and exactly 9 concentration columns")
    long = wide.melt(id_vars=[sample_col], value_vars=concentration_cols,
                     var_name="analyte_column", value_name="concentration")
    long["participant_id"] = long[sample_col].str.extract(r"^(C\d{3})_")
    long["collection_point"] = long[sample_col].str.extract(r"_serum_(.+)$")
    long["analyte"] = long["analyte_column"].str.replace(r"_concentration_.*$", "", regex=True)
    long["unit"] = long["analyte_column"].str.extract(r"_concentration_(.+)$")[0].str.replace("_", "/")
    long["data_label"] = DATA_LABEL
    return long[["participant_id", "collection_point", "analyte", "concentration", "unit", "data_label"]]


def summarize_osd575(path=None) -> pd.DataFrame:
    """Return descriptive counts and quantiles by biomarker; no clinical interpretation."""
    df = load_osd575(path)
    summary = df.groupby(["analyte", "unit", "data_label"], as_index=False).agg(
        samples=("concentration", "count"), median=("concentration", "median"),
        q1=("concentration", lambda x: x.quantile(.25)),
        q3=("concentration", lambda x: x.quantile(.75)),
        minimum=("concentration", "min"), maximum=("concentration", "max"),
    )
    return summary
