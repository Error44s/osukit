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

from osukit import (
    Beatmap,
    ReplayFrame,
    ScoreState,
    ScoreStatistics,
    analyze_score_state,
    infer_object_index_from_replay_frames,
    MapResult,
)


def sample_map():
    return Beatmap(content='''
osu file format v14

[General]
Mode:0

[Metadata]
Title:Test
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
64,192,1000,1,0,0:0:0:0:
192,192,2000,1,0,0:0:0:0:
320,192,3000,1,0,0:0:0:0:
448,192,4000,1,0,0:0:0:0:
''')


def test_replay_cursor_progress():
    beatmap = sample_map()
    cursor = infer_object_index_from_replay_frames(beatmap, [ReplayFrame(time_ms=2500)])
    assert cursor.object_index == 2
    assert cursor.progress > 0.4


def test_analyze_score_state_with_replay_frames():
    beatmap = sample_map()
    score = ScoreState(mode='osu', passed=False, max_combo=100, statistics=ScoreStatistics(count_300=2, count_miss=1))
    analysis = analyze_score_state(beatmap, score, replay_frames=[ReplayFrame(time_ms=2500)])
    assert analysis.replay_cursor is not None
    assert analysis.snapshot.object_index == 2


def test_map_result_embed_payload():
    result = MapResult.from_api_v2({'id': 1, 'version': 'Insane', 'mode': 'osu', 'difficulty_rating': 5.4, 'bpm': 180, 'total_length': 123, 'ar': 9.3, 'accuracy': 8.7, 'cs': 4, 'drain': 5, 'beatmapset': {'artist': 'Artist', 'title': 'Song', 'status': 'ranked', 'covers': {'card': 'https://example.com/x.png'}}})
    payload = result.to_embed_payload()
    assert payload['title'].startswith('Artist - Song')
    assert payload['thumbnail']['url'].startswith('https://')
