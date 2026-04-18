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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from osukit import (
    Beatmap,
    ScoreStatistics,
    ScoreState,
    analyze_score_state,
    analyze_api_score,
    estimate_object_index_from_statistics,
)

OSU_STD_MAP = """osu file format v14

[General]
Mode: 0

[Metadata]
Title:Current Test
Artist:Artist
Creator:Mapper
Version:Expert

[Difficulty]
HPDrainRate:6
CircleSize:4
OverallDifficulty:8
ApproachRate:9.2
SliderMultiplier:1.8
SliderTickRate:1

[TimingPoints]
0,400,4,1,0,100,1,0

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


class TestCurrentAnalysis(unittest.TestCase):
    def setUp(self):
        self.bm = Beatmap(content=OSU_STD_MAP)

    def test_failed_analysis_uses_partial_progress(self):
        score = ScoreState(
            mods=0,
            max_combo=4,
            statistics=ScoreStatistics(count_300=5, count_100=1, count_miss=1),
            passed=False,
        )
        analysis = analyze_score_state(self.bm, score, object_index=6)
        self.assertFalse(analysis.passed)
        self.assertLess(analysis.snapshot.progress, 1.0)
        self.assertLessEqual(analysis.partial_max_combo, analysis.full_max_combo)
        self.assertIn('% complete', analysis.map_completion_text)

    def test_passed_analysis_is_full_map(self):
        score = ScoreState(
            mods=0,
            max_combo=self.bm.max_combo,
            statistics=ScoreStatistics(count_300=self.bm.n_objects),
            passed=True,
        )
        analysis = analyze_score_state(self.bm, score)
        self.assertTrue(analysis.passed)
        self.assertEqual(analysis.snapshot.object_index, self.bm.n_objects)
        self.assertAlmostEqual(analysis.snapshot.progress, 1.0)

    def test_object_index_can_be_estimated(self):
        idx = estimate_object_index_from_statistics(
            self.bm,
            ScoreStatistics(count_300=4, count_100=1, count_miss=1),
            passed=False,
        )
        self.assertEqual(idx, 6)

    def test_api_score_analysis(self):
        payload = {
            'mods_int': 0,
            'max_combo': 4,
            'passed': False,
            'rank': 'F',
            'score': 12345,
            'statistics': {
                'count_300': 5,
                'count_100': 1,
                'count_50': 0,
                'count_miss': 1,
            },
        }
        analysis = analyze_api_score(self.bm, payload)
        self.assertFalse(analysis.passed)
        self.assertGreaterEqual(analysis.current_pp, 0.0)
        self.assertGreaterEqual(analysis.if_fc_pp, analysis.current_pp)

if __name__ == '__main__':
    unittest.main()
