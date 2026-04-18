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

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from osukit import (
    Beatmap,
    Difficulty,
    Performance,
    ScoreStatistics,
    ScoreState,
    build_partial_snapshot,
    estimate_failed_score,
)

OSU_STD_MAP = """osu file format v14

[General]
Mode: 0

[Metadata]
Title:Projection Test
Artist:Artist
Creator:Mapper
Version:Insane

[Difficulty]
HPDrainRate:6
CircleSize:4
OverallDifficulty:8
ApproachRate:9.2
SliderMultiplier:1.8
SliderTickRate:1

[TimingPoints]
0,400,4,1,0,100,1,0
1200,-100,4,1,0,100,0,0

[HitObjects]
100,100,500,1,0
200,150,750,1,0
300,100,1000,1,0
400,200,1125,1,0
200,200,1250,2,0,L|350:200,1,150
100,100,2000,1,0
300,100,2200,1,0
150,200,2400,1,0
350,200,2500,1,0
250,150,2600,1,0
100,100,2700,1,0
300,100,2800,1,0
150,200,2900,12,0,3500
"""


class TestLiveFeatures(unittest.TestCase):
    def setUp(self):
        self.bm = Beatmap(content=OSU_STD_MAP)

    def test_reuse_difficulty_attrs(self):
        diff = Difficulty().calculate(self.bm)
        perf = Performance(accuracy=98.5, combo=10, misses=1).calculate(diff, beatmap=self.bm)
        self.assertGreaterEqual(perf.pp, 0.0)

    def test_score_state_builder(self):
        score = ScoreState(
            mods=0,
            max_combo=10,
            statistics=ScoreStatistics(count_300=9, count_100=1, count_miss=1),
            passed=False,
        )
        perf = Performance.from_score_state(score).calculate(self.bm)
        self.assertGreaterEqual(perf.pp, 0.0)

    def test_partial_snapshot(self):
        snapshot = build_partial_snapshot(
            beatmap=self.bm._inner,
            object_index=6,
            statistics=ScoreStatistics(count_300=5, count_100=1, count_miss=1),
            combo=4,
            passed=False,
        )
        self.assertGreater(snapshot.progress, 0.0)
        self.assertFalse(snapshot.passed)

    def test_failed_projection(self):
        projection = estimate_failed_score(
            beatmap=self.bm._inner,
            object_index=6,
            combo=4,
            count_300=5,
            count_100=1,
            count_miss=1,
        )
        self.assertIn('% complete', projection.map_completion_text)
        self.assertGreaterEqual(projection.if_fc_pp, projection.current_pp)


if __name__ == '__main__':
    unittest.main()
