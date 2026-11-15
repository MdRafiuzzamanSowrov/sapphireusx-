# Task 1 – Health Data & Monitoring

Part of SapphireUSX (NASA Space Apps Challenge 2026). Author: Riya Kumari.

Defines the health indicators the app monitors and provides the data the other modules use.

**All vital-sign data here is SIMULATED.** The only real NASA data used is the OSD-575
cardiovascular biomarker panel (SpaceX Inspiration4), which stays in the team's research files.

## Folders

| Folder | Contents |
|---|---|
| `data/` | Simulated dataset (`simulated_vitals_long.zip`, unzip first), daily summary, answer key (`planted_events.csv`), sleep/exercise schedule |
| `reference/` | `metric_table.csv` and `reference_ranges.csv` (normal ranges with sources), indicator workbook |
| `scripts/` | `generate_simulated_vitals.py` – recreates every data file (seed 575) |
| `docs/` | Task 1 report (PDF and DOCX), screenshots, full data guide (`DATA_README.md`) |

## Recreate the data

```bash
cd scripts
pip install numpy pandas
python generate_simulated_vitals.py
```

See `docs/DATA_README.md` for every column, the 20 test cases and the limitations.
