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

from osukit import Beatmap, ReplayFrame, ScoreState, ScoreStatistics, analyze_score_state, reconstruct_judgements


def sample_map():
    return Beatmap(content='''
osu file format v14

[General]
Mode:0

[Metadata]
Title:Replay Test
Artist:Artist
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
''')


def test_reconstruct_judgements_std():
    bm = sample_map()
    frames = [
        ReplayFrame(time_ms=995, x=256, y=192, keys=1),
        ReplayFrame(time_ms=1010, x=256, y=192, keys=0),
        ReplayFrame(time_ms=2005, x=256, y=192, keys=1),
        ReplayFrame(time_ms=2015, x=256, y=192, keys=0),
    ]
    recon = reconstruct_judgements(bm, frames)
    assert recon.object_index >= 2
    assert recon.statistics.count_300 >= 2
    assert recon.progress > 0.5


def test_analyze_score_state_with_reconstruction_and_pace():
    bm = sample_map()
    score = ScoreState(mode='osu', passed=False, max_combo=2, statistics=ScoreStatistics(count_300=2, count_miss=1))
    frames = [
        ReplayFrame(time_ms=995, x=256, y=192, keys=1),
        ReplayFrame(time_ms=1010, x=256, y=192, keys=0),
        ReplayFrame(time_ms=2005, x=256, y=192, keys=1),
        ReplayFrame(time_ms=2015, x=256, y=192, keys=0),
    ]
    analysis = analyze_score_state(bm, score, replay_frames=frames)
    assert analysis.replay_reconstruction is not None
    assert analysis.pace is not None
    assert analysis.pace.objects_per_second is not None
