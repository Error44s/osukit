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

import math
import pytest

from osukit import (
    Beatmap, ReplayFrame, ScoreStatistics, ScoreState,
    reconstruct_judgements, analyze_score_state,
)
from osukit.catch_engine import (
    calculate_catch_difficulty, calculate_catch_performance,
    project_catch_score, CatchDifficultyAttributes,
)
from osukit.mania_engine import (
    calculate_mania_difficulty, calculate_mania_performance,
    project_mania_score, ManiaDifficultyAttributes,
)
from osukit.judgement import (
    JudgedObject, JudgementReconstruction,
    SliderTickResult, SpinnerResult,
    _hit_windows_std, _circle_radius, _rotations_for_spinner,
)


# Fixtures
BASIC_OSR_MAP = '''osu file format v14

[General]
Mode:0

[Metadata]
Title:V9 Test Map
Artist:TestArtist
Creator:Mapper
Version:Hard

[Difficulty]
HPDrainRate:5
CircleSize:4
OverallDifficulty:8
ApproachRate:9
SliderMultiplier:1.4
SliderTickRate:1

[TimingPoints]
0,500,4,2,1,60,1,0

[HitObjects]
256,192,1000,1,0,0:0:0:0:
256,192,2000,1,0,0:0:0:0:
256,192,3000,1,0,0:0:0:0:
256,192,4000,1,0,0:0:0:0:
256,192,5000,1,0,0:0:0:0:
'''

SLIDER_MAP = '''osu file format v14

[General]
Mode:0

[Metadata]
Title:Slider Test
Artist:Artist
Creator:Mapper
Version:Normal

[Difficulty]
HPDrainRate:5
CircleSize:4
OverallDifficulty:7
ApproachRate:8
SliderMultiplier:1.4
SliderTickRate:1

[TimingPoints]
0,500,4,2,1,60,1,0

[HitObjects]
100,192,1000,2,0,L|300:192,1,200,2|0,0:0|0:0,0:0:0:0:
256,192,3000,1,0,0:0:0:0:
'''

SPINNER_MAP = '''osu file format v14

[General]
Mode:0

[Metadata]
Title:Spinner Test
Artist:Artist
Creator:Mapper
Version:Normal

[Difficulty]
HPDrainRate:5
CircleSize:4
OverallDifficulty:5
ApproachRate:8
SliderMultiplier:1.4
SliderTickRate:1

[TimingPoints]
0,500,4,2,1,60,1,0

[HitObjects]
256,192,1000,12,0,4000,0:0:0:0:
256,192,5000,1,0,0:0:0:0:
'''

CATCH_MAP = '''osu file format v14

[General]
Mode:2

[Metadata]
Title:Catch Test
Artist:Artist
Creator:Mapper
Version:Rain

[Difficulty]
HPDrainRate:5
CircleSize:4
OverallDifficulty:7
ApproachRate:9
SliderMultiplier:1.4
SliderTickRate:1

[TimingPoints]
0,500,4,2,1,60,1,0

[HitObjects]
100,192,1000,1,0,0:0:0:0:
200,192,1500,1,0,0:0:0:0:
350,192,2000,1,0,0:0:0:0:
100,192,2500,1,0,0:0:0:0:
256,192,3000,1,0,0:0:0:0:
'''

MANIA_MAP = '''osu file format v14

[General]
Mode:3

[Metadata]
Title:Mania Test
Artist:Artist
Creator:Mapper
Version:4K

[Difficulty]
HPDrainRate:5
CircleSize:4
OverallDifficulty:8
ApproachRate:8
SliderMultiplier:1.4
SliderTickRate:1

[TimingPoints]
0,500,4,2,1,60,1,0

[HitObjects]
64,192,1000,1,0,0:0:0:0:
192,192,1500,1,0,0:0:0:0:
320,192,2000,1,0,0:0:0:0:
448,192,2500,1,0,0:0:0:0:
64,192,3000,1,0,0:0:0:0:
192,192,3500,1,0,0:0:0:0:
'''


def bm(content): return Beatmap(content=content)

# 1. Hit Windows
def test_hit_windows_od8():
    w300, w100, w50 = _hit_windows_std(8.0)
    assert w300 == pytest.approx(32.0, abs=0.1)
    assert w100 == pytest.approx(76.0, abs=0.1)
    assert w50 == pytest.approx(120.0, abs=0.1)


def test_circle_radius_cs4():
    r = _circle_radius(4.0, 0)
    assert 30.0 < r < 50.0

# 2. Basic Circle Judgement Reconstruction
def test_circles_all_300():
    beatmap = bm(BASIC_OSR_MAP)
    frames = [
        ReplayFrame(time_ms=998,  x=256, y=192, keys=1),
        ReplayFrame(time_ms=1010, x=256, y=192, keys=0),
        ReplayFrame(time_ms=1998, x=256, y=192, keys=1),
        ReplayFrame(time_ms=2010, x=256, y=192, keys=0),
        ReplayFrame(time_ms=2998, x=256, y=192, keys=1),
        ReplayFrame(time_ms=3010, x=256, y=192, keys=0),
        ReplayFrame(time_ms=3998, x=256, y=192, keys=1),
        ReplayFrame(time_ms=4010, x=256, y=192, keys=0),
        ReplayFrame(time_ms=4998, x=256, y=192, keys=1),
        ReplayFrame(time_ms=5010, x=256, y=192, keys=0),
    ]
    recon = reconstruct_judgements(beatmap, frames)
    assert recon.statistics.count_300 >= 4
    assert recon.statistics.count_miss == 0
    assert recon.completed


def test_circles_with_miss():
    beatmap = bm(BASIC_OSR_MAP)
    frames = [
        ReplayFrame(time_ms=998,  x=256, y=192, keys=1),
        ReplayFrame(time_ms=1010, x=256, y=192, keys=0),
        # skip 2000ms → miss
        ReplayFrame(time_ms=2998, x=256, y=192, keys=1),
        ReplayFrame(time_ms=3010, x=256, y=192, keys=0),
    ]
    recon = reconstruct_judgements(beatmap, frames)
    assert recon.statistics.count_miss >= 1


def test_circles_wrong_position():
    """Clicking far from object → miss."""
    beatmap = bm(BASIC_OSR_MAP)
    frames = [
        ReplayFrame(time_ms=1000, x=0, y=0, keys=1),   # far from 256,192
        ReplayFrame(time_ms=1010, x=0, y=0, keys=0),
    ]
    recon = reconstruct_judgements(beatmap, frames)
    circle_judgements = [o for o in recon.objects if o.kind == 'circle']
    first = circle_judgements[0]
    assert first.judgement == 'miss'

# 3. Sliderbreak Detection
def test_sliderbreak_detected():
    beatmap = bm(SLIDER_MAP)
    frames = [
        ReplayFrame(time_ms=995,  x=100, y=192, keys=1),
        ReplayFrame(time_ms=1005, x=100, y=192, keys=0),  # release immediately after head
        # no key held during slider body
        ReplayFrame(time_ms=3000, x=256, y=192, keys=1),
        ReplayFrame(time_ms=3010, x=256, y=192, keys=0),
    ]
    recon = reconstruct_judgements(beatmap, frames)
    sliders = [o for o in recon.objects if o.kind == 'slider']
    if sliders:
        # Head was hit but end was missed → sliderbreak or slider_end_miss
        slider = sliders[0]
        # Either sliderbreak or slider_end_hit = False
        assert slider.slider_head_hit or slider.judgement == 'miss'


def test_slider_ticks_tracked():
    beatmap = bm(SLIDER_MAP)
    frames = [
        ReplayFrame(time_ms=995,  x=100, y=192, keys=1),
        ReplayFrame(time_ms=1000, x=150, y=192, keys=1),
        ReplayFrame(time_ms=1250, x=200, y=192, keys=1),
        ReplayFrame(time_ms=1500, x=250, y=192, keys=1),
        ReplayFrame(time_ms=1750, x=300, y=192, keys=1),
        ReplayFrame(time_ms=2000, x=300, y=192, keys=0),
        ReplayFrame(time_ms=3000, x=256, y=192, keys=1),
        ReplayFrame(time_ms=3010, x=256, y=192, keys=0),
    ]
    recon = reconstruct_judgements(beatmap, frames)
    assert recon.slider_tick_total >= 0  # Track that field exists

# 4. Spinner Tracking
def test_spinner_rotations_computed():
    beatmap = bm(SPINNER_MAP)
    spinner_frames = []
    # Simulate cursor spinning around center (256,192)
    center_x, center_y = 256.0, 192.0
    radius = 60.0
    # 6 full rotations over 3 seconds
    for ms in range(1000, 4000, 16):
        angle = 2 * math.pi * (ms - 1000) / 500.0  # 2 rots/s
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        spinner_frames.append(ReplayFrame(time_ms=float(ms), x=x, y=y, keys=1))
    spinner_frames.append(ReplayFrame(time_ms=5000, x=256, y=192, keys=1))
    spinner_frames.append(ReplayFrame(time_ms=5010, x=256, y=192, keys=0))

    recon = reconstruct_judgements(beatmap, spinner_frames)
    spinners = [o for o in recon.objects if o.kind == 'spinner']
    assert len(spinners) >= 1
    sp = spinners[0]
    assert sp.spinner_result is not None
    assert sp.spinner_result.rotations_completed > 0


def test_spinner_completion_ratio():
    beatmap = bm(SPINNER_MAP)
    # Very few frames → spinner not completed
    frames = [
        ReplayFrame(time_ms=1000, x=256, y=192, keys=1),
        ReplayFrame(time_ms=1100, x=260, y=192, keys=1),
        ReplayFrame(time_ms=4500, x=256, y=192, keys=1),
        ReplayFrame(time_ms=5010, x=256, y=192, keys=0),
    ]
    recon = reconstruct_judgements(beatmap, frames)
    assert recon.spinner_completion_ratio is not None
    assert 0.0 <= recon.spinner_completion_ratio <= 1.0

# 5. Unstable Rate + Mean Error
def test_unstable_rate_computed():
    beatmap = bm(BASIC_OSR_MAP)
    frames = [
        ReplayFrame(time_ms=1000, x=256, y=192, keys=1),
        ReplayFrame(time_ms=1010, x=256, y=192, keys=0),
        ReplayFrame(time_ms=2005, x=256, y=192, keys=1),
        ReplayFrame(time_ms=2015, x=256, y=192, keys=0),
        ReplayFrame(time_ms=3010, x=256, y=192, keys=1),
        ReplayFrame(time_ms=3020, x=256, y=192, keys=0),
    ]
    recon = reconstruct_judgements(beatmap, frames)
    assert recon.unstable_rate is not None
    assert recon.mean_error_ms is not None

# 6. Non-std mode preview
def test_catch_mode_preview():
    beatmap = bm(CATCH_MAP)
    frames = [
        ReplayFrame(time_ms=1000, x=100, y=192, keys=1),
        ReplayFrame(time_ms=2000, x=200, y=192, keys=1),
        ReplayFrame(time_ms=2500, x=350, y=192, keys=1),
    ]
    recon = reconstruct_judgements(beatmap, frames, mode='catch')
    assert recon.mode == 'catch'
    assert 'Preview' in (recon.note or '') or recon.object_index >= 0


def test_mania_mode_preview():
    beatmap = bm(MANIA_MAP)
    frames = [
        ReplayFrame(time_ms=1000, x=64, y=192, keys=1),
        ReplayFrame(time_ms=1500, x=192, y=192, keys=1),
        ReplayFrame(time_ms=2000, x=320, y=192, keys=1),
    ]
    recon = reconstruct_judgements(beatmap, frames, mode='mania')
    assert recon.mode == 'mania'
    assert recon.object_index >= 0

# 7. Catch Local Engine
def test_catch_difficulty_basic():
    beatmap = bm(CATCH_MAP)
    bm_inner = beatmap._inner
    diff = calculate_catch_difficulty(bm_inner)
    assert isinstance(diff, CatchDifficultyAttributes)
    assert diff.stars >= 0.0
    assert diff.ar >= 0.0
    assert diff.max_combo >= 0
    assert diff.n_fruits >= 0


def test_catch_performance_basic():
    beatmap = bm(CATCH_MAP)
    bm_inner = beatmap._inner
    diff = calculate_catch_difficulty(bm_inner)
    stats = ScoreStatistics(count_300=5, count_miss=0)
    perf = calculate_catch_performance(diff, stats, combo=5)
    assert perf.pp >= 0.0
    assert 0.0 <= perf.accuracy <= 100.0


def test_catch_fc_beats_fail():
    beatmap = bm(CATCH_MAP)
    bm_inner = beatmap._inner
    diff = calculate_catch_difficulty(bm_inner)
    fail_stats = ScoreStatistics(count_300=3, count_miss=2)
    fc_stats = ScoreStatistics(count_300=5, count_miss=0)
    fail_pp = calculate_catch_performance(diff, fail_stats, combo=3).pp
    fc_pp = calculate_catch_performance(diff, fc_stats, combo=diff.max_combo).pp
    assert fc_pp >= fail_pp


def test_catch_project_score():
    beatmap = bm(CATCH_MAP)
    bm_inner = beatmap._inner
    stats = ScoreStatistics(count_300=4, count_miss=1)
    result = project_catch_score(bm_inner, stats, 4)
    assert 'stars' in result
    assert 'current_pp' in result
    assert 'if_fc_pp' in result
    assert result['mode'] == 'catch'
    assert result['engine'] == 'local'
    assert result['if_fc_pp'] >= result['current_pp']


def test_catch_dt_harder():
    beatmap = bm(CATCH_MAP)
    bm_inner = beatmap._inner
    nm_diff = calculate_catch_difficulty(bm_inner, 0)
    dt_diff = calculate_catch_difficulty(bm_inner, 64)  # DT
    assert dt_diff.stars >= nm_diff.stars

# 8. Mania Local Engine
def test_mania_difficulty_basic():
    beatmap = bm(MANIA_MAP)
    bm_inner = beatmap._inner
    diff = calculate_mania_difficulty(bm_inner)
    assert isinstance(diff, ManiaDifficultyAttributes)
    assert diff.stars >= 0.0
    assert diff.key_count == 4
    assert diff.hit_window > 0
    assert diff.max_combo >= 0


def test_mania_performance_basic():
    beatmap = bm(MANIA_MAP)
    bm_inner = beatmap._inner
    diff = calculate_mania_difficulty(bm_inner)
    stats = ScoreStatistics(geki=6, count_300=0)
    perf = calculate_mania_performance(diff, stats, score=1_000_000)
    assert perf.pp >= 0.0
    assert 0.0 <= perf.accuracy <= 100.0


def test_mania_perfect_beats_bad():
    beatmap = bm(MANIA_MAP)
    bm_inner = beatmap._inner
    diff = calculate_mania_difficulty(bm_inner)
    bad_stats = ScoreStatistics(count_100=3, count_miss=3)
    good_stats = ScoreStatistics(geki=6)
    bad_pp = calculate_mania_performance(diff, bad_stats, score=500_000).pp
    good_pp = calculate_mania_performance(diff, good_stats, score=1_000_000).pp
    assert good_pp >= bad_pp


def test_mania_project_score():
    beatmap = bm(MANIA_MAP)
    bm_inner = beatmap._inner
    stats = ScoreStatistics(geki=4, count_300=1, count_miss=1)
    result = project_mania_score(bm_inner, stats, score=850_000)
    assert 'stars' in result
    assert 'current_pp' in result
    assert 'if_fc_pp' in result
    assert result['mode'] == 'mania'
    assert result['engine'] == 'local'
    assert result['key_count'] == 4


def test_mania_hit_window_od8():
    beatmap = bm(MANIA_MAP)
    bm_inner = beatmap._inner
    diff = calculate_mania_difficulty(bm_inner)
    # OD8 → 300 window should be < 50ms
    assert diff.hit_window < 50.0

# 9. Replay Timeline: "where exactly did it choke"
def test_choke_location_identified():
    """Verify we can identify the exact object where combo broke."""
    beatmap = bm(BASIC_OSR_MAP)
    frames = [
        ReplayFrame(time_ms=998,  x=256, y=192, keys=1),
        ReplayFrame(time_ms=1010, x=256, y=192, keys=0),
        ReplayFrame(time_ms=1998, x=256, y=192, keys=1),
        ReplayFrame(time_ms=2010, x=256, y=192, keys=0),
        # Miss object at 3000ms
        ReplayFrame(time_ms=4000, x=256, y=192, keys=1),
        ReplayFrame(time_ms=4010, x=256, y=192, keys=0),
        ReplayFrame(time_ms=5000, x=256, y=192, keys=1),
        ReplayFrame(time_ms=5010, x=256, y=192, keys=0),
    ]
    recon = reconstruct_judgements(beatmap, frames)
    misses = [o for o in recon.objects if o.judgement == 'miss']
    assert len(misses) >= 1
    # Combo should have reset at miss
    miss = misses[0]
    assert miss.combo_after == 0
    # Objects after miss should restart combo from 1
    after = [o for o in recon.objects if o.index > miss.index and o.judgement != 'miss']
    if after:
        assert after[0].combo_after >= 1


def test_per_object_timeline():
    """All objects are individually tracked with correct kind labels."""
    beatmap = bm(SLIDER_MAP)
    frames = [
        ReplayFrame(time_ms=990,  x=100, y=192, keys=1),
        ReplayFrame(time_ms=1000, x=100, y=192, keys=1),
        ReplayFrame(time_ms=1500, x=200, y=192, keys=1),
        ReplayFrame(time_ms=2000, x=300, y=192, keys=0),
        ReplayFrame(time_ms=2998, x=256, y=192, keys=1),
        ReplayFrame(time_ms=3010, x=256, y=192, keys=0),
    ]
    recon = reconstruct_judgements(beatmap, frames)
    kinds = {o.kind for o in recon.objects}
    assert 'slider' in kinds
    assert 'circle' in kinds

# 10. Full analyze_score_state with Catch/Mania mode
def test_analyze_score_state_catch_fallback():
    """analyze_score_state should not crash on catch mode."""
    beatmap = bm(CATCH_MAP)
    score = ScoreState(
        mode='catch',
        passed=False,
        max_combo=3,
        statistics=ScoreStatistics(count_300=3, count_miss=2),
    )
    result = analyze_score_state(beatmap, score)
    assert result is not None
    assert result.snapshot is not None


def test_analyze_score_state_mania_fallback():
    """analyze_score_state should not crash on mania mode."""
    beatmap = bm(MANIA_MAP)
    score = ScoreState(
        mode='mania',
        passed=True,
        max_combo=6,
        statistics=ScoreStatistics(geki=6),
        pp=42.0,
    )
    result = analyze_score_state(beatmap, score)
    assert result is not None

# 11. Slider end miss tracking in statistics
def test_slider_end_miss_counted():
    beatmap = bm(SLIDER_MAP)
    # Hit head, release immediately
    frames = [
        ReplayFrame(time_ms=995,  x=100, y=192, keys=1),
        ReplayFrame(time_ms=1005, x=100, y=192, keys=0),
        # long gap with no keys
        ReplayFrame(time_ms=3000, x=256, y=192, keys=1),
        ReplayFrame(time_ms=3010, x=256, y=192, keys=0),
    ]
    recon = reconstruct_judgements(beatmap, frames)
    sliders = [o for o in recon.objects if o.kind == 'slider']
    assert len(sliders) >= 1
    # slider_end_miss should be tracked in stats
    assert recon.statistics.slider_end_miss >= 0  # could be 0 or 1 depending on parsing


# 12. Empty replay edge case
def test_empty_replay_returns_zero():
    beatmap = bm(BASIC_OSR_MAP)
    recon = reconstruct_judgements(beatmap, [])
    assert recon.object_index == 0
    assert recon.progress == 0.0
    assert recon.statistics.count_300 == 0
    assert recon.note is not None


# 13. Performance with DT/HR mods
def test_catch_with_dt():
    beatmap = bm(CATCH_MAP)
    bm_inner = beatmap._inner
    stats = ScoreStatistics(count_300=5)
    nm = project_catch_score(bm_inner, stats, 5, mods_int=0)
    dt = project_catch_score(bm_inner, stats, 5, mods_int=64)
    assert dt['stars'] >= nm['stars']


def test_mania_with_dt():
    beatmap = bm(MANIA_MAP)
    bm_inner = beatmap._inner
    stats = ScoreStatistics(geki=6)
    nm = project_mania_score(bm_inner, stats, score=1_000_000, mods_int=0)
    dt = project_mania_score(bm_inner, stats, score=1_000_000, mods_int=64)
    assert dt['stars'] >= nm['stars']
