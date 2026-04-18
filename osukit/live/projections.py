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

from typing import Any, Optional, Sequence

from ..api import Beatmap, Performance
from ..beatmap import Beatmap as CoreBeatmap
from ..errors import ScoreAnalysisError
from ..judgement import reconstruct_judgements
from ..models.scores import (
    ScoreStatistics,
    ScoreState,
    PartialPlaySnapshot,
    ProjectedScore,
    AnalyzedScore,
    PaceMetrics,
)
from ..replay import ReplayCursor, ReplayFrame, infer_object_index_from_replay_frames


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _estimate_combo_until_object(beatmap: CoreBeatmap, object_count: int) -> int:
    combo = 0
    for obj in beatmap.hit_objects[:object_count]:
        combo += 1
        tick_count = getattr(obj, 'tick_count', 0)
        repeats = getattr(obj, 'repeats', 1)
        if hasattr(obj, 'tick_count'):
            combo += tick_count + max(0, repeats - 1) + 1
    return combo


def _normalise_beatmap(beatmap: Beatmap | CoreBeatmap) -> CoreBeatmap:
    return beatmap._inner if isinstance(beatmap, Beatmap) else beatmap


def _slice_beatmap(beatmap: CoreBeatmap, object_index: int) -> CoreBeatmap:
    idx = _clamp_int(object_index, 0, len(beatmap.hit_objects))
    return CoreBeatmap(
        title=beatmap.title,
        artist=beatmap.artist,
        creator=beatmap.creator,
        version=beatmap.version,
        mode=beatmap.mode,
        hp=beatmap.hp,
        cs=beatmap.cs,
        od=beatmap.od,
        ar=beatmap.ar,
        slider_multiplier=beatmap.slider_multiplier,
        slider_tick_rate=beatmap.slider_tick_rate,
        hit_objects=list(beatmap.hit_objects[:idx]),
        timing_points=list(beatmap.timing_points),
    )


def estimate_object_index_from_statistics(beatmap: Beatmap | CoreBeatmap, statistics: ScoreStatistics, *, passed: bool = False) -> int:
    bm = _normalise_beatmap(beatmap)
    if passed:
        return len(bm.hit_objects)
    total = statistics.count_300 + statistics.count_100 + statistics.count_50 + statistics.count_miss
    weighted = total + statistics.slider_tick_miss + statistics.slider_end_miss + max(0, statistics.katu // 2)
    return _clamp_int(weighted, 0, len(bm.hit_objects))


def build_partial_snapshot(
    beatmap: Beatmap | CoreBeatmap,
    object_index: Optional[int],
    statistics: ScoreStatistics,
    combo: int,
    *,
    passed: bool,
) -> PartialPlaySnapshot:
    bm = _normalise_beatmap(beatmap)
    total_objects = len(bm.hit_objects)
    idx = total_objects if passed else estimate_object_index_from_statistics(bm, statistics, passed=False) if object_index is None else object_index
    idx = _clamp_int(idx, 0, total_objects)
    progress = (idx / total_objects) if total_objects else 0.0
    est_combo = _estimate_combo_until_object(bm, idx)
    return PartialPlaySnapshot(
        object_index=idx,
        object_count=total_objects,
        progress=progress,
        combo=combo,
        statistics=statistics,
        estimated_max_combo_at_progress=est_combo,
        passed=passed,
    )


def _performance_for_snapshot(beatmap: CoreBeatmap, snapshot: PartialPlaySnapshot, mods: int = 0) -> Any:
    partial_bm = _slice_beatmap(beatmap, snapshot.object_index)
    return Performance(
        mods=mods,
        accuracy=snapshot.accuracy('osu'),
        combo=min(snapshot.combo, max(0, partial_bm.max_combo)),
        misses=snapshot.statistics.count_miss,
        n300=snapshot.statistics.count_300,
        n100=snapshot.statistics.count_100,
        n50=snapshot.statistics.count_50,
        slider_tick_miss=snapshot.statistics.slider_tick_miss,
        slider_end_miss=snapshot.statistics.slider_end_miss,
    ).calculate(partial_bm)


def _build_pace(snapshot: PartialPlaySnapshot, current_pp: float | None, elapsed_time_ms: float | None) -> PaceMetrics:
    seconds = (elapsed_time_ms / 1000.0) if elapsed_time_ms and elapsed_time_ms > 0 else None
    return PaceMetrics(
        elapsed_time_ms=elapsed_time_ms,
        objects_per_second=(snapshot.object_index / seconds) if seconds else None,
        combo_per_second=(snapshot.combo / seconds) if seconds else None,
        current_pp_per_second=(current_pp / seconds) if (seconds and current_pp is not None) else None,
    )


def _estimate_nonstd_pp(mode: str, score: ScoreState, snapshot: PartialPlaySnapshot) -> float | None:
    stars = score.beatmap.stars or 0.0
    if stars <= 0:
        return None
    acc = max(0.0, min(1.0, score.accuracy() / 100.0))
    combo_ratio = min(1.0, (score.max_combo or snapshot.combo or 0) / max(1, snapshot.estimated_max_combo_at_progress or 1))
    length_factor = 1.0 + min(0.35, snapshot.object_index / 2500.0)
    if mode in {'catch', 'fruits'}:
        return (stars ** 2.2) * (0.55 + 0.45 * acc) * (0.7 + 0.3 * combo_ratio) * 8.0 * length_factor
    if mode == 'mania':
        return (stars ** 2.4) * (acc ** 3.2) * 12.0 * length_factor
    return None


def estimate_failed_score(
    beatmap: Beatmap | CoreBeatmap,
    *,
    object_index: int,
    combo: int,
    count_300: int,
    count_100: int,
    count_50: int = 0,
    count_miss: int,
    slider_tick_miss: int = 0,
    slider_end_miss: int = 0,
    mods: int = 0,
) -> ProjectedScore:
    stats = ScoreStatistics(
        count_300=count_300,
        count_100=count_100,
        count_50=count_50,
        count_miss=count_miss,
        slider_tick_miss=slider_tick_miss,
        slider_end_miss=slider_end_miss,
    )
    snapshot = build_partial_snapshot(beatmap=beatmap, object_index=object_index, statistics=stats, combo=combo, passed=False)
    return project_score(beatmap=beatmap, snapshot=snapshot, mods=mods)


def project_score(beatmap: Beatmap | CoreBeatmap, snapshot: PartialPlaySnapshot, mods: int = 0) -> ProjectedScore:
    bm = _normalise_beatmap(beatmap)
    if snapshot.object_count < 0:
        raise ScoreAnalysisError('Snapshot contains an invalid object count.')

    try:
        current = _performance_for_snapshot(bm, snapshot, mods=mods)
        if_fc = Performance(mods=mods, accuracy=snapshot.accuracy('osu'), combo=bm.max_combo, misses=0).calculate(bm)
        partial_bm = _slice_beatmap(bm, snapshot.object_index)
        choke = Performance(
            mods=mods,
            accuracy=snapshot.accuracy('osu'),
            combo=min(snapshot.estimated_max_combo_at_progress, max(0, partial_bm.max_combo)),
            misses=0,
            n300=snapshot.statistics.count_300 + snapshot.statistics.count_miss,
            n100=snapshot.statistics.count_100,
            n50=snapshot.statistics.count_50,
            slider_tick_miss=snapshot.statistics.slider_tick_miss,
            slider_end_miss=snapshot.statistics.slider_end_miss,
        ).calculate(partial_bm)
    except Exception:
        partial_bm = _slice_beatmap(bm, snapshot.object_index)
        current = type('FallbackPP', (), {'pp': None})()
        if_fc = type('FallbackPP', (), {'pp': None})()
        choke = type('FallbackPP', (), {'pp': None})()

    current_pp = current.pp
    if_fc_pp = if_fc.pp
    choke_pp = choke.pp
    if current_pp is not None and if_fc_pp is not None:
        if_fc_pp = max(if_fc_pp, current_pp)
    if current_pp is not None and choke_pp is not None:
        choke_pp = max(choke_pp, current_pp)

    progress_text = '100.0% complete' if snapshot.passed else f'{snapshot.progress * 100:.1f}% complete'
    return ProjectedScore(
        snapshot=snapshot,
        current_pp=current_pp,
        if_fc_pp=if_fc_pp,
        estimated_full_combo_pp=if_fc_pp,
        choke_pp=choke_pp,
        partial_max_combo=partial_bm.max_combo,
        map_completion_text=progress_text,
    )


def _api_only_analysis(
    beatmap: Beatmap | CoreBeatmap,
    score: ScoreState,
    object_index: int | None = None,
    replay_cursor: ReplayCursor | None = None,
    replay_reconstruction: Any = None,
) -> AnalyzedScore:
    bm = _normalise_beatmap(beatmap)
    idx = object_index if object_index is not None else (len(bm.hit_objects) if score.passed else estimate_object_index_from_statistics(bm, score.statistics, passed=False))
    snapshot = build_partial_snapshot(bm, idx, score.statistics, combo=score.max_combo or 0, passed=score.passed)
    current_pp = score.pp
    map_completion_text = '100.0% complete' if score.passed else f'{snapshot.progress * 100:.1f}% complete'
    elapsed = getattr(replay_reconstruction, 'fail_time_ms', None) or getattr(replay_cursor, 'frame_time_ms', None)
    return AnalyzedScore(
        score=score,
        snapshot=snapshot,
        current_pp=current_pp,
        if_fc_pp=current_pp,
        choke_pp=current_pp,
        estimated_full_combo_pp=current_pp,
        partial_max_combo=snapshot.estimated_max_combo_at_progress,
        full_max_combo=bm.max_combo,
        map_completion_text=map_completion_text,
        analysis_source='api_only',
        replay_cursor=replay_cursor,
        replay_reconstruction=replay_reconstruction,
        pace=_build_pace(snapshot, current_pp, elapsed),
    )


def analyze_score_state(
    beatmap: Beatmap | CoreBeatmap,
    score: ScoreState,
    object_index: Optional[int] = None,
    replay_frames: Optional[Sequence[ReplayFrame]] = None,
) -> AnalyzedScore:
    bm = _normalise_beatmap(beatmap)
    replay_cursor = None
    replay_reconstruction = None
    if replay_frames:
        replay_cursor = infer_object_index_from_replay_frames(bm, replay_frames)
        replay_reconstruction = reconstruct_judgements(bm, replay_frames, mods=score.mods, mode=score.mode or score.beatmap.mode)
        object_index = replay_reconstruction.object_index or replay_cursor.object_index

    mode = (score.mode or score.beatmap.mode or ('taiko' if bm.mode == 1 else 'osu')).lower()
    if mode not in {'osu', 'taiko'}:
        analysis = _api_only_analysis(bm, score, object_index=object_index, replay_cursor=replay_cursor, replay_reconstruction=replay_reconstruction)
        if analysis.current_pp is None:
            analysis.current_pp = _estimate_nonstd_pp(mode, score, analysis.snapshot)
            analysis.if_fc_pp = analysis.current_pp
            analysis.choke_pp = analysis.current_pp
            analysis.estimated_full_combo_pp = analysis.current_pp
            if analysis.current_pp is not None:
                analysis.analysis_source = 'local_preview'
                elapsed = getattr(replay_reconstruction, 'fail_time_ms', None) if replay_reconstruction else getattr(replay_cursor, 'frame_time_ms', None) if replay_cursor else None
                analysis.pace = _build_pace(analysis.snapshot, analysis.current_pp, elapsed)
        return analysis

    if object_index is None and not score.passed:
        object_index = estimate_object_index_from_statistics(bm, score.statistics, passed=False)

    if replay_reconstruction is not None and not score.passed:
        stats = replay_reconstruction.statistics
        combo = replay_reconstruction.max_combo_achieved
    else:
        stats = score.statistics
        combo = score.max_combo or 0

    snapshot = build_partial_snapshot(
        beatmap=bm,
        object_index=(len(bm.hit_objects) if score.passed else object_index),
        statistics=stats,
        combo=combo,
        passed=score.passed,
    )

    if mode == 'taiko' and score.pp is not None:
        return _api_only_analysis(bm, score, object_index=snapshot.object_index, replay_cursor=replay_cursor, replay_reconstruction=replay_reconstruction)

    projection = project_score(bm, snapshot=snapshot, mods=score.mods)
    elapsed = getattr(replay_reconstruction, 'fail_time_ms', None) if replay_reconstruction else getattr(replay_cursor, 'frame_time_ms', None) if replay_cursor else None
    return AnalyzedScore(
        score=score,
        snapshot=snapshot,
        current_pp=projection.current_pp,
        if_fc_pp=projection.if_fc_pp,
        choke_pp=projection.choke_pp,
        estimated_full_combo_pp=projection.estimated_full_combo_pp,
        partial_max_combo=projection.partial_max_combo,
        full_max_combo=bm.max_combo,
        map_completion_text=projection.map_completion_text,
        analysis_source='local',
        replay_cursor=replay_cursor,
        replay_reconstruction=replay_reconstruction,
        pace=_build_pace(snapshot, projection.current_pp, elapsed),
    )


def analyze_api_score(
    beatmap: Beatmap | CoreBeatmap,
    api_score: dict[str, Any],
    object_index: Optional[int] = None,
    replay_frames: Optional[Sequence[ReplayFrame]] = None,
) -> AnalyzedScore:
    score = ScoreState.from_api_v2(api_score)
    if object_index is None and not score.passed:
        object_index = estimate_object_index_from_statistics(beatmap, score.statistics, passed=False)
    return analyze_score_state(beatmap=beatmap, score=score, object_index=object_index, replay_frames=replay_frames)
