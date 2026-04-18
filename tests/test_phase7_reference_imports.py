"""
The MIT License (MIT)

Copyright (c) 2026 Error44s

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from pathlib import Path

from osukit.benchmark import load_reference_cases, run_candidate_matrix
from osukit.tuning import build_candidate_profiles


def _sample_csv(tmp_path: Path, beatmap_path: Path) -> Path:
    csv_path = tmp_path / "cases.csv"
    csv_path.write_text(
        "name,beatmap_path,accuracy,mods,performance_pp,tags\n"
        f"sample,{beatmap_path.name},98.5,0,0.0,aim,accuracy\n",
        encoding="utf-8",
    )
    return csv_path


def test_load_reference_cases_from_csv(tmp_path: Path):
    beatmap_path = Path(__file__).parent / "data" / "sample_std.osu"
    csv_path = _sample_csv(tmp_path, beatmap_path)
    cases, summary = load_reference_cases(csv_path, beatmap_root=beatmap_path.parent)
    assert summary.imported_cases == 1
    assert cases[0].beatmap_path == str(beatmap_path.resolve())
    assert "aim" in cases[0].tags


def test_run_candidate_matrix(tmp_path: Path):
    beatmap_path = Path(__file__).parent / "data" / "sample_std.osu"
    csv_path = _sample_csv(tmp_path, beatmap_path)
    cases, _summary = load_reference_cases(csv_path, beatmap_root=beatmap_path.parent)
    matrix = run_candidate_matrix(cases, build_candidate_profiles())
    assert matrix.best is not None
    assert len(matrix.comparisons) >= 2
    assert "Candidate Benchmark Matrix" in matrix.to_markdown()
