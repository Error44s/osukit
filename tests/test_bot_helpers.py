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

from osukit import Beatmap, analyze_api_score
from osukit.bot import format_analysis_markdown, build_embed_payload, format_mods

OSU_STD_MAP = """osu file format v14

[General]
Mode: 0

[Metadata]
Title:Bot Test
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
"""


class TestBotHelpers(unittest.TestCase):
    def setUp(self):
        self.beatmap = Beatmap(content=OSU_STD_MAP)
        self.payload = {
            'mods_int': 0,
            'max_combo': 4,
            'passed': False,
            'rank': 'F',
            'score': 12345,
            'user': {'username': 'Pedro'},
            'beatmap': {'title': 'Bot Test', 'artist': 'Artist', 'version': 'Insane', 'id': 1},
            'statistics': {
                'count_300': 5,
                'count_100': 1,
                'count_50': 0,
                'count_miss': 1,
            },
        }

    def test_markdown_formatter(self):
        analysis = analyze_api_score(self.beatmap, self.payload)
        text = format_analysis_markdown(analysis, self.beatmap, self.payload)
        self.assertIn('Pedro', text)
        self.assertIn('If FC', text)
        self.assertIn('FAILED', text)

    def test_embed_payload(self):
        analysis = analyze_api_score(self.beatmap, self.payload)
        embed = build_embed_payload(analysis, self.beatmap, self.payload)
        self.assertIn('fields', embed)
        self.assertGreaterEqual(len(embed['fields']), 4)

    def test_mod_formatter(self):
        self.assertEqual(format_mods(0), 'NM')
        self.assertEqual(format_mods((1 << 3) | (1 << 4)), 'HDHR')


if __name__ == '__main__':
    unittest.main()
