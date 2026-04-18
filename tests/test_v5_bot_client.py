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

import asyncio
from pathlib import Path

from osukit import BeatmapResolver, OsuApiClient, OsuBotClient, BotClientConfig, TTLCache


TEST_BEATMAP = """osu file format v14

[General]
Mode:0

[Metadata]
Title:Test Song
Artist:Test Artist
Version:Insane

[Difficulty]
HPDrainRate:5
CircleSize:4
OverallDifficulty:8
ApproachRate:9
SliderMultiplier:1.4
SliderTickRate:1

[TimingPoints]
0,500,4,1,0,100,1,0

[HitObjects]
64,192,0,1,0,0:0:0:0:
128,192,500,1,0,0:0:0:0:
192,192,1000,1,0,0:0:0:0:
256,192,1500,1,0,0:0:0:0:
"""


class FakeApi(OsuApiClient):
    def __init__(self):
        super().__init__(token='test')
        self.calls = []

    def lookup_user(self, user, *, mode='osu'):
        self.calls.append(('lookup_user', user, mode))
        return {
            'id': 10,
            'username': str(user),
            'avatar_url': 'https://example/avatar.png',
            'country_code': 'PT',
            'statistics': {
                'pp': 1234.5,
                'global_rank': 123,
                'country_rank': 10,
                'play_count': 999,
                'hit_accuracy': 98.76,
                'level': {'current': 100, 'progress': 50},
            }
        }

    def get_recent_score(self, user_id, mode='osu', include_fails=True):
        self.calls.append(('get_recent_score', user_id, mode, include_fails))
        return self._score_payload(user_id, beatmap_id=123, passed=False)

    def get_recent_scores(self, user_id, mode='osu', include_fails=True, limit=5):
        self.calls.append(('get_recent_scores', user_id, mode, include_fails, limit))
        return [self._score_payload(user_id, beatmap_id=123 + i, passed=(i % 2 == 0)) for i in range(limit)]

    def get_best_scores(self, user_id, mode='osu', limit=5, offset=None):
        self.calls.append(('get_best_scores', user_id, mode, limit, offset))
        return [self._score_payload(user_id, beatmap_id=123 + i, passed=True) for i in range(limit)]

    def get_beatmap(self, beatmap_id):
        self.calls.append(('get_beatmap', beatmap_id))
        return {'id': beatmap_id, 'beatmapset_id': 999}

    @staticmethod
    def _score_payload(user, beatmap_id=123, passed=False):
        return {
            'user_id': 10,
            'user': {'id': 10, 'username': str(user)},
            'beatmap_id': beatmap_id,
            'beatmap': {
                'id': beatmap_id,
                'beatmapset_id': 999,
                'version': 'Insane',
                'difficulty_rating': 5.2,
                'beatmapset': {'artist': 'Test Artist', 'title': 'Test Song'},
            },
            'mods': ['HD'],
            'mods_int': 8,
            'max_combo': 3,
            'passed': passed,
            'rank': 'A',
            'score': 123456,
            'statistics': {'count_300': 2, 'count_100': 1, 'count_50': 0, 'count_miss': 1},
        }


def build_resolver(tmp_path: Path):
    resolver = BeatmapResolver(cache_dir=tmp_path)
    for beatmap_id in [123,124,125,126,127]:
        resolver.save_content(beatmap_id=beatmap_id, content=TEST_BEATMAP)
    return resolver


def test_ttl_cache_basic():
    cache = TTLCache(ttl_seconds=60)
    cache.set('a', 1)
    assert cache.get('a') == 1
    cache.clear()
    assert cache.get('a') is None


def test_bot_client_current_and_profile(tmp_path):
    client = OsuBotClient(api_client=FakeApi(), resolver=build_resolver(tmp_path), config=BotClientConfig())
    result = client.get_current_play('Error44')
    assert result.kind == 'current'
    assert result.profile is not None
    assert result.profile.username == 'Error44'
    assert result.analysis.score.beatmap_id == 123
    payload = result.to_embed_payload()
    assert payload['title'].startswith('Test Artist - Test Song')


def test_bot_client_recent_and_top_lists(tmp_path):
    client = OsuBotClient(api_client=FakeApi(), resolver=build_resolver(tmp_path), config=BotClientConfig())
    recent = client.get_recent_plays('Error44', limit=3)
    top = client.get_top_plays('Error44', limit=2)
    assert len(recent.plays) == 3
    assert len(top.plays) == 2
    assert recent.to_compact_lines()
    assert top.to_embed_payload()['title'] == 'Best plays'


def test_compare_on_beatmap(tmp_path):
    client = OsuBotClient(api_client=FakeApi(), resolver=build_resolver(tmp_path), config=BotClientConfig())
    compare = client.compare_on_beatmap('A', 'B', beatmap_id=123)
    assert compare.beatmap.title == 'Test Song'
    assert compare.left.user_query == 'A'
    assert compare.right.user_query == 'B'
    assert compare.to_embed_payload()['title'].startswith('Test Artist - Test Song')


def test_async_methods(tmp_path):
    client = OsuBotClient(api_client=FakeApi(), resolver=build_resolver(tmp_path), config=BotClientConfig())

    async def run():
        profile = await client.aget_profile('Error44')
        current = await client.aget_current_play('Error44')
        top = await client.aget_top_plays('Error44', limit=2)
        return profile, current, top

    profile, current, top = asyncio.run(run())
    assert profile.username == 'Error44'
    assert current.kind == 'current'
    assert len(top.plays) == 2
