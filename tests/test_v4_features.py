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

from pathlib import Path

from osukit import (
    BeatmapResolver,
    ScoreState,
    format_mods,
    mods_to_int,
    parse_mods,
)
from osukit.oauth import OAuthToken


def test_score_state_from_api_v2_rich_fields():
    payload = {
        'mods': ['HD', 'NC'],
        'mods_int': 576,
        'max_combo': 1234,
        'statistics': {'count_300': 500, 'count_100': 10, 'count_50': 1, 'count_miss': 2},
        'passed': False,
        'rank': 'F',
        'score': 1234567,
        'legacy_total_score': 999,
        'pp': 321.45,
        'user_id': 55,
        'created_at': '2026-04-18T10:00:00Z',
        'mode': 'osu',
        'perfect': False,
        'beatmap': {
            'id': 987,
            'beatmapset_id': 654,
            'version': 'Insane',
            'mode': 'osu',
            'difficulty_rating': 6.5,
            'beatmapset': {'artist': 'Artist', 'title': 'Title'},
        },
        'user': {'id': 55, 'username': 'Pedro'},
    }
    score = ScoreState.from_api_v2(payload)
    assert score.mods_list == ['HD', 'NC']
    assert score.beatmap_id == 987
    assert score.beatmap.artist == 'Artist'
    assert score.user.username == 'Pedro'
    assert score.pp == 321.45
    assert score.accuracy() > 0


def test_mod_helpers_normalize_special_cases():
    assert parse_mods('HDNC') == ['HD', 'NC']
    assert mods_to_int(['NC']) & (1 << 6)  # NC implies DT bit
    assert format_mods((1 << 9) | (1 << 6)) == 'NC'
    assert format_mods(mods_to_int(['HD', 'NC']), ['HD', 'NC', 'DT']) == 'HDNC'


def test_oauth_token_expiry_logic():
    token = OAuthToken(access_token='abc', expires_in=1, acquired_at=0)
    assert token.expires_at == 1
    assert token.is_expired(skew_seconds=0) is True


def test_beatmap_resolver_inline_and_cache(tmp_path: Path):
    resolver = BeatmapResolver(cache_dir=tmp_path)
    content = 'osu file format v14\n\n[Metadata]\nTitle:Test\nArtist:Test\nVersion:Normal\n\n[Difficulty]\nHPDrainRate:5\nCircleSize:4\nOverallDifficulty:8\nApproachRate:9\n\n[TimingPoints]\n0,500,4,2,1,60,1,0\n\n[HitObjects]\n64,192,0,1,0,0:0:0:0:\n'
    beatmap = resolver.resolve(beatmap_id=123, beatmap_content=content)
    assert beatmap.title == 'Test'
    cached = resolver.find_cached(123)
    assert cached is not None and cached.exists()
