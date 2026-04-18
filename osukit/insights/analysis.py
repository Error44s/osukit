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

from dataclasses import dataclass, field
from statistics import mean
from typing import Sequence

from ..models import AnalyzedScore


def _clamp(value: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, value))


@dataclass
class SkillProfile:
    mode: str
    aim: float
    speed: float
    accuracy: float
    consistency: float
    reading: float
    control: float
    confidence: float
    summary: str
    notes: list[str] = field(default_factory=list)


@dataclass
class ChokeInfo:
    severity: str
    is_choke: bool
    confidence: float
    reason: str
    lost_pp: float | None = None
    progress_percent: float | None = None


@dataclass
class Recommendation:
    category: str
    priority: str
    message: str


@dataclass
class SessionInsight:
    profile: SkillProfile
    common_choke_severity: str
    fail_rate: float
    average_accuracy: float
    average_progress: float
    recommendations: list[Recommendation] = field(default_factory=list)


def classify_choke(analysis: AnalyzedScore) -> ChokeInfo:
    progress = analysis.snapshot.progress * 100.0
    misses = analysis.score.statistics.count_miss
    lost_pp = None
    if analysis.if_fc_pp is not None and analysis.current_pp is not None:
        lost_pp = max(0.0, analysis.if_fc_pp - analysis.current_pp)

    severity = 'none'
    confidence = 0.25
    reason = 'Run does not strongly resemble a choke.'

    if analysis.passed:
        if misses == 0:
            reason = 'Full combo or clean pass.'
        elif progress >= 99.0 and misses <= 2:
            severity = 'small'
            confidence = 0.6
            reason = 'Pass with very late mistakes near the end of the map.'
        elif lost_pp is not None and lost_pp >= 30:
            severity = 'small'
            confidence = 0.55
            reason = 'Passed, but a meaningful amount of PP was lost to combo breaks.'
    else:
        if progress >= 92.0:
            severity = 'tragic'
            confidence = 0.95
            reason = 'Fail happened extremely late into the map.'
        elif progress >= 82.0:
            severity = 'hard'
            confidence = 0.85
            reason = 'Late fail with high completion strongly suggests a choke.'
        elif progress >= 68.0:
            severity = 'medium'
            confidence = 0.72
            reason = 'Fail happened after most of the map was already completed.'
        elif progress >= 50.0 and misses <= 2:
            severity = 'small'
            confidence = 0.58
            reason = 'Moderately late fail with relatively contained miss count.'
        else:
            reason = 'Fail was too early to confidently classify as a choke.'

    return ChokeInfo(
        severity=severity,
        is_choke=severity != 'none',
        confidence=round(confidence, 3),
        reason=reason,
        lost_pp=round(lost_pp, 3) if lost_pp is not None else None,
        progress_percent=round(progress, 2),
    )


def analyze_skill_profile(analyses: Sequence[AnalyzedScore]) -> SkillProfile:
    if not analyses:
        return SkillProfile(
            mode='osu', aim=0.0, speed=0.0, accuracy=0.0, consistency=0.0,
            reading=0.0, control=0.0, confidence=0.0,
            summary='No scores were provided.', notes=['Provide at least one analyzed score.'],
        )

    mode = (analyses[0].score.mode or analyses[0].score.beatmap.mode or 'osu').lower()
    accs = [a.accuracy for a in analyses]
    progresses = [a.snapshot.progress for a in analyses]
    misses = [a.score.statistics.count_miss for a in analyses]
    if_fc_deltas = [
        max(0.0, (a.if_fc_pp or a.current_pp or 0.0) - (a.current_pp or 0.0))
        for a in analyses
    ]
    star_values = [float(a.score.beatmap.stars or 0.0) for a in analyses]

    avg_acc = mean(accs)
    avg_progress = mean(progresses)
    avg_miss = mean(misses)
    avg_delta = mean(if_fc_deltas)
    avg_stars = mean(star_values) if star_values else 0.0

    accuracy = _clamp((avg_acc - 90.0) / 1.0)
    consistency = _clamp(avg_progress * 10.0 - avg_miss * 0.7)
    aim = _clamp(4.2 + avg_stars * 0.8 + (avg_acc - 95.0) * 0.18 - avg_miss * 0.35)
    speed = _clamp(4.0 + avg_stars * 0.6 + avg_progress * 2.0 - avg_miss * 0.25)
    reading = _clamp(4.5 + (avg_acc - 95.0) * 0.22 + avg_progress * 1.5)
    control = _clamp(accuracy * 0.45 + consistency * 0.55)
    confidence = _clamp(10.0 - min(10.0, avg_delta / 18.0) + avg_progress)

    notes: list[str] = []
    if avg_delta >= 80:
        notes.append('Large FC delta suggests major pp loss from breaks or fails.')
    if avg_progress < 0.7:
        notes.append('Runs tend to collapse before the end of the map.')
    if avg_acc < 97.0:
        notes.append('Accuracy is a visible source of score loss.')
    if not notes:
        notes.append('Current scores look stable overall.')

    weakest = min(
        [('aim', aim), ('speed', speed), ('accuracy', accuracy), ('consistency', consistency), ('reading', reading), ('control', control)],
        key=lambda item: item[1],
    )[0]
    strongest = max(
        [('aim', aim), ('speed', speed), ('accuracy', accuracy), ('consistency', consistency), ('reading', reading), ('control', control)],
        key=lambda item: item[1],
    )[0]
    summary = f'Strongest area: {strongest}. Weakest area: {weakest}.'

    return SkillProfile(
        mode=mode,
        aim=round(aim, 2),
        speed=round(speed, 2),
        accuracy=round(accuracy, 2),
        consistency=round(consistency, 2),
        reading=round(reading, 2),
        control=round(control, 2),
        confidence=round(confidence, 2),
        summary=summary,
        notes=notes,
    )


def recommend_training_focus(analyses: Sequence[AnalyzedScore]) -> list[Recommendation]:
    profile = analyze_skill_profile(analyses)
    recs: list[Recommendation] = []

    if profile.consistency < 6.0:
        recs.append(Recommendation('consistency', 'high', 'Play easier maps to the end and focus on closing runs without late collapses.'))
    if profile.accuracy < 6.5:
        recs.append(Recommendation('accuracy', 'high', 'Spend sessions on lower-star control maps and aim for tighter hit windows.'))
    if profile.reading < 6.0:
        recs.append(Recommendation('reading', 'medium', 'Mix in maps with denser patterns or AR changes to build reading confidence.'))
    if profile.aim < 6.0:
        recs.append(Recommendation('aim', 'medium', 'Practice maps slightly below your comfort ceiling and prioritize cursor stability over raw speed.'))
    if profile.speed < 6.0:
        recs.append(Recommendation('speed', 'medium', 'Use short, burst-heavy maps and focus on maintaining accuracy under denser note streams.'))
    if not recs:
        recs.append(Recommendation('general', 'low', 'Your recent scores look balanced; keep building map variety and consistency.'))
    return recs


def summarize_recent_fails(analyses: Sequence[AnalyzedScore]) -> str:
    fails = [a for a in analyses if not a.passed]
    if not fails:
        return 'No failed runs in the provided set.'

    avg_progress = mean(a.snapshot.progress * 100.0 for a in fails)
    avg_acc = mean(a.accuracy for a in fails)
    severe = sum(1 for a in fails if classify_choke(a).severity in {'hard', 'tragic'})
    return (
        f'{len(fails)} failed runs | avg fail point {avg_progress:.1f}% | '
        f'avg accuracy {avg_acc:.2f}% | {severe} hard/tragic chokes'
    )


def build_session_insight(analyses: Sequence[AnalyzedScore]) -> SessionInsight:
    profile = analyze_skill_profile(analyses)
    if not analyses:
        return SessionInsight(
            profile=profile,
            common_choke_severity='none',
            fail_rate=0.0,
            average_accuracy=0.0,
            average_progress=0.0,
            recommendations=[],
        )

    choke_levels = [classify_choke(a).severity for a in analyses]
    ordering = ['none', 'small', 'medium', 'hard', 'tragic']
    common = max(ordering, key=lambda sev: choke_levels.count(sev))
    fails = [a for a in analyses if not a.passed]
    return SessionInsight(
        profile=profile,
        common_choke_severity=common,
        fail_rate=round(len(fails) / len(analyses), 3),
        average_accuracy=round(mean(a.accuracy for a in analyses), 3),
        average_progress=round(mean(a.snapshot.progress for a in analyses), 3),
        recommendations=recommend_training_focus(analyses),
    )
