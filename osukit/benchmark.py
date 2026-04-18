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

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from statistics import mean
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union
import json
import csv

from .api import Beatmap, Difficulty, Performance
from .difficulty import DifficultyAttributes
from .performance import PerformanceAttributes

Number = Union[int, float]


@dataclass
class DifficultyExpectation:
    stars: Optional[float] = None
    aim: Optional[float] = None
    speed: Optional[float] = None
    flashlight: Optional[float] = None
    max_combo: Optional[int] = None
    tolerance: float = 0.01


@dataclass
class PerformanceExpectation:
    pp: Optional[float] = None
    aim: Optional[float] = None
    speed: Optional[float] = None
    accuracy: Optional[float] = None
    flashlight: Optional[float] = None
    tolerance: float = 0.05


@dataclass
class GoldenScoreCase:
    name: str
    beatmap_path: Optional[str] = None
    beatmap_content: Optional[str] = None
    mods: int = 0
    accuracy: float = 100.0
    combo: Optional[int] = None
    misses: int = 0
    n300: Optional[int] = None
    n100: Optional[int] = None
    n50: Optional[int] = None
    slider_tick_miss: int = 0
    slider_end_miss: int = 0
    clock_rate: Optional[float] = None
    difficulty: DifficultyExpectation = field(default_factory=DifficultyExpectation)
    performance: PerformanceExpectation = field(default_factory=PerformanceExpectation)
    tags: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GoldenScoreCase":
        payload = dict(data)
        payload["difficulty"] = DifficultyExpectation(**payload.get("difficulty", {}))
        payload["performance"] = PerformanceExpectation(**payload.get("performance", {}))
        return cls(**payload)


@dataclass
class MetricComparison:
    metric: str
    actual: float
    expected: float
    absolute_error: float
    relative_error: float
    tolerance: float

    @property
    def passed(self) -> bool:
        return self.absolute_error <= self.tolerance


@dataclass
class FocusRecommendation:
    category: str
    average_relative_error: float
    max_relative_error: float
    failing_checks: int
    affected_cases: int
    suggestion: str


@dataclass
class ReportDelta:
    metric: str
    baseline_average_relative_error: float
    candidate_average_relative_error: float
    delta_relative_error: float

    @property
    def improved(self) -> bool:
        return self.delta_relative_error < 0

@dataclass
class ReferenceImportSummary:
    imported_cases: int
    skipped_rows: int = 0
    source: str = ""


@dataclass
class CandidateComparison:
    name: str
    average_relative_error: float
    max_relative_error: float
    weighted_error: float
    report: "BenchmarkSuiteReport"


@dataclass
class CandidateMatrixReport:
    comparisons: List[CandidateComparison]

    @property
    def best(self) -> Optional[CandidateComparison]:
        if not self.comparisons:
            return None
        return min(self.comparisons, key=lambda c: (c.weighted_error, c.average_relative_error, c.max_relative_error))

    def to_markdown(self) -> str:
        lines = [
            "# Candidate Benchmark Matrix",
            "",
        ]
        for item in sorted(self.comparisons, key=lambda c: (c.weighted_error, c.average_relative_error, c.max_relative_error)):
            marker = " **BEST**" if self.best and item.name == self.best.name else ""
            lines.append(
                f"- `{item.name}` weighted={item.weighted_error:.4%} avg_rel={item.average_relative_error:.4%} max_rel={item.max_relative_error:.4%}{marker}"
            )
        lines.append("")
        return "\n".join(lines)


@dataclass
class BenchmarkResult:
    case_name: str
    difficulty: DifficultyAttributes
    performance: PerformanceAttributes
    difficulty_checks: List[MetricComparison] = field(default_factory=list)
    performance_checks: List[MetricComparison] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in [*self.difficulty_checks, *self.performance_checks])

    def summary_dict(self) -> Dict[str, Any]:
        return {
            "case": self.case_name,
            "passed": self.passed,
            "tags": getattr(self, "tags", []),
            "difficulty": {
                "stars": self.difficulty.stars,
                "aim": self.difficulty.aim_difficulty,
                "speed": self.difficulty.speed_difficulty,
                "flashlight": self.difficulty.flashlight_difficulty,
                "max_combo": self.difficulty.max_combo,
            },
            "performance": {
                "pp": self.performance.pp,
                "aim": self.performance.pp_aim,
                "speed": self.performance.pp_speed,
                "accuracy": self.performance.pp_accuracy,
                "flashlight": self.performance.pp_flashlight,
            },
            "checks": [
                {
                    "metric": c.metric,
                    "actual": c.actual,
                    "expected": c.expected,
                    "absolute_error": c.absolute_error,
                    "relative_error": c.relative_error,
                    "tolerance": c.tolerance,
                    "passed": c.passed,
                }
                for c in [*self.difficulty_checks, *self.performance_checks]
            ],
        }


@dataclass
class BenchmarkSuiteReport:
    results: List[BenchmarkResult]

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def total_cases(self) -> int:
        return len(self.results)

    @property
    def passed_cases(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_cases(self) -> int:
        return self.total_cases - self.passed_cases

    def summarize_by_tag(self) -> Dict[str, Dict[str, float]]:
        grouped: Dict[str, list[float]] = {}
        for result in self.results:
            tag_list = getattr(result, "tags", [])
            checks = [*result.difficulty_checks, *result.performance_checks]
            rel_errors = [abs(c.relative_error) for c in checks]
            if not rel_errors:
                continue
            avg_error = sum(rel_errors) / len(rel_errors)
            for tag in tag_list:
                grouped.setdefault(tag, []).append(avg_error)
        return {
            tag: {
                "cases": float(len(values)),
                "average_relative_error": sum(values) / len(values),
                "max_relative_error": max(values),
            }
            for tag, values in grouped.items()
        }

    def summarize_by_metric(self) -> Dict[str, Dict[str, float]]:
        grouped: Dict[str, list[float]] = {}
        for result in self.results:
            for check in [*result.difficulty_checks, *result.performance_checks]:
                grouped.setdefault(check.metric, []).append(abs(check.relative_error))
        return {
            metric: {
                "checks": float(len(values)),
                "average_relative_error": mean(values),
                "max_relative_error": max(values),
            }
            for metric, values in grouped.items()
        }

    def summarize_by_mod(self) -> Dict[str, Dict[str, float]]:
        grouped: Dict[str, list[float]] = {}
        for result in self.results:
            mods = getattr(result, "mods", [])
            checks = [*result.difficulty_checks, *result.performance_checks]
            rel_errors = [abs(c.relative_error) for c in checks]
            if not rel_errors:
                continue
            avg_error = sum(rel_errors) / len(rel_errors)
            for mod in mods:
                grouped.setdefault(mod, []).append(avg_error)
        return {
            mod: {
                "cases": float(len(values)),
                "average_relative_error": sum(values) / len(values),
                "max_relative_error": max(values),
            }
            for mod, values in grouped.items()
        }

    def summarize_by_case(self) -> Dict[str, Dict[str, float]]:
        data: Dict[str, Dict[str, float]] = {}
        for result in self.results:
            checks = [*result.difficulty_checks, *result.performance_checks]
            rel_errors = [abs(c.relative_error) for c in checks]
            if not rel_errors:
                continue
            data[result.case_name] = {
                "checks": float(len(rel_errors)),
                "average_relative_error": mean(rel_errors),
                "max_relative_error": max(rel_errors),
            }
        return data

    def worst_cases(self, limit: int = 5) -> List[BenchmarkResult]:
        def score(result: BenchmarkResult) -> tuple[float, float]:
            checks = [*result.difficulty_checks, *result.performance_checks]
            if not checks:
                return (0.0, 0.0)
            rel_errors = [abs(c.relative_error) for c in checks]
            return (mean(rel_errors), max(rel_errors))

        return sorted(self.results, key=score, reverse=True)[: max(0, limit)]

    def recommend_focus(self, limit: int = 5) -> List[FocusRecommendation]:
        suggestions = {
            "hd": "Tune hidden bonus scaling and AR-dependent hidden handling.",
            "dt": "Tune clock-rate-sensitive aim/speed scaling and high-AR bonuses.",
            "hr": "Revisit AR/OD scaling and accuracy pressure under HR.",
            "slider-heavy": "Tune slider nerf, slider miss weighting, and combo-drop handling.",
            "long": "Tune length bonus and long-map miss/combo scaling.",
            "short": "Tune short-map scaling so stars/pp do not overshoot on low object counts.",
            "aim": "Tune aim multiplier, aim acc scaling, and miss penalty on aim-heavy maps.",
            "speed": "Tune speed multiplier, n50 penalty, and speed acc weighting.",
            "accuracy": "Tune accuracy exponent and circle-count scaling.",
            "flashlight": "Tune flashlight multiplier and object-count scaling under FL.",
        }
        tag_summary = self.summarize_by_tag()
        recommendations: List[FocusRecommendation] = []
        for tag, data in tag_summary.items():
            affected = 0
            failing = 0
            for result in self.results:
                if tag not in getattr(result, "tags", []):
                    continue
                affected += 1
                failing += sum(1 for c in [*result.difficulty_checks, *result.performance_checks] if not c.passed)
            recommendations.append(
                FocusRecommendation(
                    category=tag,
                    average_relative_error=data["average_relative_error"],
                    max_relative_error=data["max_relative_error"],
                    failing_checks=failing,
                    affected_cases=affected,
                    suggestion=suggestions.get(tag, "Investigate this category with more golden cases and targeted tuning."),
                )
            )
        recommendations.sort(key=lambda r: (r.average_relative_error, r.max_relative_error, r.failing_checks), reverse=True)
        return recommendations[: max(0, limit)]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "tag_summary": self.summarize_by_tag(),
            "mod_summary": self.summarize_by_mod(),
            "metric_summary": self.summarize_by_metric(),
            "results": [r.summary_dict() for r in self.results],
        }

    def to_markdown(self) -> str:
        lines = [
            "# PP Accuracy Benchmark Report",
            "",
            f"Passed: **{self.passed_cases}/{self.total_cases}**",
            "",
        ]
        tag_summary = self.summarize_by_tag()
        if tag_summary:
            lines.append("## Tag Summary")
            lines.append("")
            for tag, data in sorted(tag_summary.items()):
                lines.append(
                    f"- `{tag}` cases={int(data['cases'])} avg_rel={data['average_relative_error']:.4%} max_rel={data['max_relative_error']:.4%}"
                )
            lines.append("")
        mod_summary = self.summarize_by_mod()
        if mod_summary:
            lines.append("## Mod Summary")
            lines.append("")
            for mod, data in sorted(mod_summary.items()):
                lines.append(
                    f"- `{mod}` cases={int(data['cases'])} avg_rel={data['average_relative_error']:.4%} max_rel={data['max_relative_error']:.4%}"
                )
            lines.append("")
        metric_summary = self.summarize_by_metric()
        if metric_summary:
            lines.append("## Metric Summary")
            lines.append("")
            for metric, data in sorted(metric_summary.items()):
                lines.append(
                    f"- `{metric}` checks={int(data['checks'])} avg_rel={data['average_relative_error']:.4%} max_rel={data['max_relative_error']:.4%}"
                )
            lines.append("")
        recommendations = self.recommend_focus()
        if recommendations:
            lines.append("## Recommended Focus")
            lines.append("")
            for rec in recommendations:
                lines.append(
                    f"- `{rec.category}` avg_rel={rec.average_relative_error:.4%} max_rel={rec.max_relative_error:.4%} cases={rec.affected_cases} failing_checks={rec.failing_checks} — {rec.suggestion}"
                )
            lines.append("")
        for result in self.results:
            status = "PASS" if result.passed else "FAIL"
            lines.append(f"## {result.case_name} — {status}")
            lines.append("")
            lines.append(f"- Stars: `{result.difficulty.stars:.6f}`")
            lines.append(f"- PP: `{result.performance.pp:.6f}`")
            checks = [*result.difficulty_checks, *result.performance_checks]
            if checks:
                lines.append("- Comparisons:")
                for c in checks:
                    lines.append(
                        f"  - `{c.metric}` actual={c.actual:.6f} expected={c.expected:.6f} "
                        f"abs={c.absolute_error:.6f} rel={c.relative_error:.4%} tol={c.tolerance:.6f} "
                        f"[{ 'PASS' if c.passed else 'FAIL' }]"
                    )
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


def _relative_error(actual: float, expected: float) -> float:
    if expected == 0:
        return 0.0 if actual == 0 else 1.0
    return abs(actual - expected) / abs(expected)


def _metric_checks(prefix: str, actuals: Dict[str, Number], expectation: Any) -> List[MetricComparison]:
    checks: List[MetricComparison] = []
    tolerance = float(getattr(expectation, "tolerance", 0.0))
    for metric, expected in expectation.__dict__.items():
        if metric == "tolerance" or expected is None:
            continue
        actual = float(actuals[metric])
        exp = float(expected)
        checks.append(
            MetricComparison(
                metric=f"{prefix}.{metric}",
                actual=actual,
                expected=exp,
                absolute_error=abs(actual - exp),
                relative_error=_relative_error(actual, exp),
                tolerance=tolerance,
            )
        )
    return checks


def _load_beatmap(case: GoldenScoreCase) -> Beatmap:
    if case.beatmap_content is not None:
        return Beatmap(content=case.beatmap_content)
    if case.beatmap_path is not None:
        return Beatmap(path=case.beatmap_path)
    raise ValueError(f"Case {case.name!r} is missing beatmap_path or beatmap_content")


def run_golden_case(case: GoldenScoreCase, tuning=None) -> BenchmarkResult:
    beatmap = _load_beatmap(case)
    difficulty = Difficulty(mods=case.mods, clock_rate=case.clock_rate).calculate(beatmap)
    performance = Performance(
        mods=case.mods,
        accuracy=case.accuracy,
        combo=case.combo,
        misses=case.misses,
        n300=case.n300,
        n100=case.n100,
        n50=case.n50,
        slider_tick_miss=case.slider_tick_miss,
        slider_end_miss=case.slider_end_miss,
        clock_rate=case.clock_rate,
        tuning=tuning,
    ).calculate(difficulty, beatmap=beatmap)

    difficulty_checks = _metric_checks(
        "difficulty",
        {
            "stars": difficulty.stars,
            "aim": difficulty.aim_difficulty,
            "speed": difficulty.speed_difficulty,
            "flashlight": difficulty.flashlight_difficulty,
            "max_combo": difficulty.max_combo,
        },
        case.difficulty,
    )
    performance_checks = _metric_checks(
        "performance",
        {
            "pp": performance.pp,
            "aim": performance.pp_aim,
            "speed": performance.pp_speed,
            "accuracy": performance.pp_accuracy,
            "flashlight": performance.pp_flashlight,
        },
        case.performance,
    )

    result = BenchmarkResult(
        case_name=case.name,
        difficulty=difficulty,
        performance=performance,
        difficulty_checks=difficulty_checks,
        performance_checks=performance_checks,
    )
    result.tags = infer_case_tags(case)
    result.mods = _mod_names(case.mods)
    return result


def run_golden_suite(cases: Sequence[GoldenScoreCase], tuning=None) -> BenchmarkSuiteReport:
    return BenchmarkSuiteReport([run_golden_case(case, tuning=tuning) for case in cases])


def save_golden_cases(cases: Sequence[GoldenScoreCase], path: Union[str, Path]) -> None:
    Path(path).write_text(json.dumps([c.to_dict() for c in cases], indent=2), encoding="utf-8")


def load_golden_cases(path: Union[str, Path]) -> List[GoldenScoreCase]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [GoldenScoreCase.from_dict(item) for item in data]


def create_golden_case(
    name: str,
    beatmap_path: Optional[str] = None,
    beatmap_content: Optional[str] = None,
    mods: int = 0,
    accuracy: float = 100.0,
    combo: Optional[int] = None,
    misses: int = 0,
    n300: Optional[int] = None,
    n100: Optional[int] = None,
    n50: Optional[int] = None,
    slider_tick_miss: int = 0,
    slider_end_miss: int = 0,
    clock_rate: Optional[float] = None,
    difficulty_tolerance: float = 0.01,
    performance_tolerance: float = 0.05,
    meta: Optional[Dict[str, Any]] = None,
) -> GoldenScoreCase:
    case = GoldenScoreCase(
        name=name,
        beatmap_path=beatmap_path,
        beatmap_content=beatmap_content,
        mods=mods,
        accuracy=accuracy,
        combo=combo,
        misses=misses,
        n300=n300,
        n100=n100,
        n50=n50,
        slider_tick_miss=slider_tick_miss,
        slider_end_miss=slider_end_miss,
        clock_rate=clock_rate,
        difficulty=DifficultyExpectation(tolerance=difficulty_tolerance),
        performance=PerformanceExpectation(tolerance=performance_tolerance),
        meta=meta or {},
    )
    result = run_golden_case(case)
    case.difficulty.stars = result.difficulty.stars
    case.difficulty.aim = result.difficulty.aim_difficulty
    case.difficulty.speed = result.difficulty.speed_difficulty
    case.difficulty.flashlight = result.difficulty.flashlight_difficulty
    case.difficulty.max_combo = result.difficulty.max_combo
    case.performance.pp = result.performance.pp
    case.performance.aim = result.performance.pp_aim
    case.performance.speed = result.performance.pp_speed
    case.performance.accuracy = result.performance.pp_accuracy
    case.performance.flashlight = result.performance.pp_flashlight
    case.tags = infer_case_tags(case)
    return case



def infer_case_tags(case: GoldenScoreCase) -> List[str]:
    tags = list(case.tags)
    beatmap = _load_beatmap(case)
    inner = beatmap._inner
    mods = int(case.mods)
    slider_ratio = (beatmap.n_sliders / beatmap.n_objects) if beatmap.n_objects else 0.0
    spinner_ratio = (beatmap.n_spinners / beatmap.n_objects) if beatmap.n_objects else 0.0
    if beatmap.n_objects > 1:
        first = inner.hit_objects[0].time
        last_obj = inner.hit_objects[-1]
        last = getattr(last_obj, "end_time", last_obj.time)
        duration_s = max(1.0, (last - first) / 1000.0)
    else:
        duration_s = 1.0
    object_density = beatmap.n_objects / duration_s

    def add(tag: str) -> None:
        if tag not in tags:
            tags.append(tag)

    if mods & 8:
        add("hd")
    if mods & 16:
        add("hr")
    if mods & 64 or mods & 512:
        add("dt")
    if (mods & 8) and (mods & 64 or mods & 512):
        add("hddt")
    if mods & 1024:
        add("flashlight")
    if slider_ratio >= 0.35:
        add("slider-heavy")
    if spinner_ratio >= 0.12:
        add("spinner-heavy")
    if beatmap.n_objects >= 600:
        add("long")
    elif beatmap.n_objects <= 120:
        add("short")
    if object_density >= 4.5:
        add("speed")
    if object_density >= 5.8:
        add("stream")
    if inner.ar >= 9.3 or (mods & 16 and inner.ar >= 8.8):
        add("aim")
    if case.accuracy >= 99.0:
        add("accuracy")
    return tags


def _mod_names(mods: int) -> List[str]:
    names: List[str] = []
    if mods & 8:
        names.append("HD")
    if mods & 16:
        names.append("HR")
    if mods & 64 or mods & 512:
        names.append("DT")
    if mods & 1024:
        names.append("FL")
    if mods & 256:
        names.append("HT")
    if mods & 2:
        names.append("EZ")
    return names or ["NM"]


def compare_benchmark_reports(
    baseline: BenchmarkSuiteReport,
    candidate: BenchmarkSuiteReport,
) -> List[ReportDelta]:
    baseline_metrics = baseline.summarize_by_metric()
    candidate_metrics = candidate.summarize_by_metric()
    deltas: List[ReportDelta] = []
    for metric in sorted(set(baseline_metrics) | set(candidate_metrics)):
        base = baseline_metrics.get(metric, {}).get("average_relative_error", 0.0)
        cand = candidate_metrics.get(metric, {}).get("average_relative_error", 0.0)
        deltas.append(
            ReportDelta(
                metric=metric,
                baseline_average_relative_error=base,
                candidate_average_relative_error=cand,
                delta_relative_error=cand - base,
            )
        )
    deltas.sort(key=lambda d: abs(d.delta_relative_error), reverse=True)
    return deltas



def load_reference_cases(
    path: Union[str, Path],
    *,
    beatmap_root: Optional[Union[str, Path]] = None,
    difficulty_tolerance: float = 0.01,
    performance_tolerance: float = 0.05,
) -> tuple[List[GoldenScoreCase], ReferenceImportSummary]:
    """Load golden/reference cases from JSON or CSV.

    Expected JSON payload: list of GoldenScoreCase-compatible dicts.
    Expected CSV columns include at minimum: name, beatmap_path or beatmap_content.
    Optional columns: mods, accuracy, combo, misses, n300, n100, n50,
    difficulty_stars, difficulty_aim, difficulty_speed, difficulty_flashlight, difficulty_max_combo,
    performance_pp, performance_aim, performance_speed, performance_accuracy, performance_flashlight,
    tags (comma-separated), meta (JSON object).
    """
    path = Path(path)
    root = Path(beatmap_root) if beatmap_root is not None else None
    cases: List[GoldenScoreCase] = []
    skipped = 0

    def _num(value: Any, *, integer: bool = False):
        if value in (None, ""):
            return None
        return int(value) if integer else float(value)

    if path.suffix.lower() == '.json':
        cases = load_golden_cases(path)
        return cases, ReferenceImportSummary(imported_cases=len(cases), skipped_rows=0, source=str(path))

    if path.suffix.lower() != '.csv':
        raise ValueError(f'Unsupported reference format: {path.suffix}')

    with path.open('r', encoding='utf-8', newline='') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if not row.get('name'):
                skipped += 1
                continue
            beatmap_path = row.get('beatmap_path') or None
            if beatmap_path and root is not None and not Path(beatmap_path).is_absolute():
                beatmap_path = str((root / beatmap_path).resolve())
            beatmap_content = row.get('beatmap_content') or None
            if not beatmap_path and not beatmap_content:
                skipped += 1
                continue
            tags = [t.strip() for t in (row.get('tags') or '').split(',') if t.strip()]
            meta = {}
            if row.get('meta'):
                try:
                    meta = json.loads(row['meta'])
                except Exception:
                    meta = {'raw_meta': row['meta']}
            case = GoldenScoreCase(
                name=row['name'],
                beatmap_path=beatmap_path,
                beatmap_content=beatmap_content,
                mods=int(row.get('mods') or 0),
                accuracy=float(row.get('accuracy') or 100.0),
                combo=_num(row.get('combo'), integer=True),
                misses=int(row.get('misses') or 0),
                n300=_num(row.get('n300'), integer=True),
                n100=_num(row.get('n100'), integer=True),
                n50=_num(row.get('n50'), integer=True),
                slider_tick_miss=int(row.get('slider_tick_miss') or 0),
                slider_end_miss=int(row.get('slider_end_miss') or 0),
                clock_rate=_num(row.get('clock_rate')),
                difficulty=DifficultyExpectation(
                    stars=_num(row.get('difficulty_stars')),
                    aim=_num(row.get('difficulty_aim')),
                    speed=_num(row.get('difficulty_speed')),
                    flashlight=_num(row.get('difficulty_flashlight')),
                    max_combo=_num(row.get('difficulty_max_combo'), integer=True),
                    tolerance=float(row.get('difficulty_tolerance') or difficulty_tolerance),
                ),
                performance=PerformanceExpectation(
                    pp=_num(row.get('performance_pp')),
                    aim=_num(row.get('performance_aim')),
                    speed=_num(row.get('performance_speed')),
                    accuracy=_num(row.get('performance_accuracy')),
                    flashlight=_num(row.get('performance_flashlight')),
                    tolerance=float(row.get('performance_tolerance') or performance_tolerance),
                ),
                tags=tags,
                meta=meta,
            )
            cases.append(case)

    return cases, ReferenceImportSummary(imported_cases=len(cases), skipped_rows=skipped, source=str(path))


def run_candidate_matrix(cases: Sequence[GoldenScoreCase], candidates: Dict[str, Any], objective=None) -> CandidateMatrixReport:
    from .tuning import score_suite

    comparisons: List[CandidateComparison] = []
    for name, tuning in candidates.items():
        report = run_golden_suite(cases, tuning=tuning)
        avg, max_err, _count, weighted = score_suite(report, objective)
        comparisons.append(CandidateComparison(name=name, average_relative_error=avg, max_relative_error=max_err, weighted_error=weighted, report=report))
    comparisons.sort(key=lambda c: (c.weighted_error, c.average_relative_error, c.max_relative_error))
    return CandidateMatrixReport(comparisons=comparisons)


__all__ = [
    "DifficultyExpectation",
    "PerformanceExpectation",
    "GoldenScoreCase",
    "MetricComparison",
    "FocusRecommendation",
    "BenchmarkResult",
    "BenchmarkSuiteReport",
    "ReportDelta",
    "ReferenceImportSummary",
    "CandidateComparison",
    "CandidateMatrixReport",
    "run_golden_case",
    "run_golden_suite",
    "save_golden_cases",
    "load_golden_cases",
    "create_golden_case",
    "infer_case_tags",
    "compare_benchmark_reports",
    "load_reference_cases",
    "run_candidate_matrix",
]
