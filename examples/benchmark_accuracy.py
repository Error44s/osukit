from __future__ import annotations

from pathlib import Path

from osukit import create_golden_case, run_golden_suite, save_golden_cases

ROOT = Path(__file__).resolve().parent.parent
MAP = ROOT / "tests" / "data" / "sample_std.osu"
OUT = ROOT / "tests" / "data" / "golden_cases.generated.json"

cases = [
    create_golden_case(
        name="sample_std_nm_fc",
        beatmap_path=str(MAP),
        accuracy=100.0,
    ),
    create_golden_case(
        name="sample_std_hdhr_choke",
        beatmap_path=str(MAP),
        mods=24,
        accuracy=98.5,
        combo=350,
        misses=2,
        slider_end_miss=1,
    ),
]

save_golden_cases(cases, OUT)
report = run_golden_suite(cases)
print(report.to_markdown())
print(f"Saved cases to: {OUT}")
