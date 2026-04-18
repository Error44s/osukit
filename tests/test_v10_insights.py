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

from osukit.insights import (
    classify_choke,
    analyze_skill_profile,
    recommend_training_focus,
    summarize_recent_fails,
    build_session_insight,
)
from osukit.models import ScoreState, ScoreStatistics, BeatmapRef, PartialPlaySnapshot, AnalyzedScore, PaceMetrics


def make_analysis(*, passed: bool, progress: float, acc: float, miss: int, current_pp: float, if_fc_pp: float, stars: float = 6.0):
    total = 100
    c300 = int(total * (acc / 100.0))
    remaining = total - c300 - miss
    stats = ScoreStatistics(count_300=max(0, c300), count_100=max(0, remaining), count_miss=miss)
    score = ScoreState(
        passed=passed,
        max_combo=500,
        pp=current_pp,
        statistics=stats,
        mode='osu',
        beatmap=BeatmapRef(stars=stars, mode='osu', title='Map', artist='Artist'),
    )
    snapshot = PartialPlaySnapshot(
        object_index=int(progress * 1000),
        object_count=1000,
        progress=progress,
        combo=300,
        statistics=stats,
        estimated_max_combo_at_progress=350,
        passed=passed,
    )
    return AnalyzedScore(
        score=score,
        snapshot=snapshot,
        current_pp=current_pp,
        if_fc_pp=if_fc_pp,
        choke_pp=if_fc_pp,
        estimated_full_combo_pp=if_fc_pp,
        partial_max_combo=350,
        full_max_combo=700,
        map_completion_text=f'{progress*100:.1f}% complete',
        pace=PaceMetrics(elapsed_time_ms=120000.0),
    )


def test_classify_choke_tragic_fail():
    analysis = make_analysis(passed=False, progress=0.95, acc=98.2, miss=1, current_pp=230.0, if_fc_pp=370.0)
    choke = classify_choke(analysis)
    assert choke.is_choke is True
    assert choke.severity == 'tragic'
    assert choke.lost_pp == 140.0


def test_analyze_skill_profile_and_recommendations():
    analyses = [
        make_analysis(passed=False, progress=0.62, acc=95.5, miss=4, current_pp=120.0, if_fc_pp=240.0),
        make_analysis(passed=True, progress=1.0, acc=96.2, miss=2, current_pp=180.0, if_fc_pp=220.0),
        make_analysis(passed=False, progress=0.71, acc=94.8, miss=5, current_pp=130.0, if_fc_pp=260.0),
    ]
    profile = analyze_skill_profile(analyses)
    assert profile.mode == 'osu'
    assert 0.0 <= profile.aim <= 10.0
    assert 'Strongest area' in profile.summary

    recs = recommend_training_focus(analyses)
    assert recs
    assert any(r.category in {'consistency', 'accuracy', 'aim', 'speed', 'reading', 'general'} for r in recs)


def test_fail_summary_and_session_insight():
    analyses = [
        make_analysis(passed=False, progress=0.81, acc=97.0, miss=2, current_pp=200.0, if_fc_pp=280.0),
        make_analysis(passed=False, progress=0.56, acc=95.2, miss=3, current_pp=110.0, if_fc_pp=200.0),
        make_analysis(passed=True, progress=1.0, acc=98.1, miss=0, current_pp=250.0, if_fc_pp=250.0),
    ]
    summary = summarize_recent_fails(analyses)
    assert 'failed runs' in summary
    insight = build_session_insight(analyses)
    assert 0.0 <= insight.fail_rate <= 1.0
    assert insight.recommendations
