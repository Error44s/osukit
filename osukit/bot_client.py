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

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from .cache import TTLCache
from .client import OsuApiClient
from .errors import OsuApiError
from .resolver import BeatmapResolver
from .results import CompareResult, MapResult, PlayListResult, PlayResult, ProfileResult
from .bot.helpers import analyze_recent_play
from .replay import ReplayFrame


@dataclass
class BotClientConfig:
    default_mode: str = 'osu'
    score_cache_ttl: int = 45
    user_cache_ttl: int = 300
    beatmap_cache_ttl: int = 900
    max_retries: int = 2
    retry_delay: float = 0.3


class OsuBotClient:
    def __init__(
        self,
        *,
        api_client: OsuApiClient,
        resolver: BeatmapResolver | None = None,
        config: BotClientConfig | None = None,
    ):
        self.api = api_client
        self.resolver = resolver or BeatmapResolver()
        self.config = config or BotClientConfig()
        self._score_cache = TTLCache[Any](ttl_seconds=self.config.score_cache_ttl, max_size=512)
        self._user_cache = TTLCache[Any](ttl_seconds=self.config.user_cache_ttl, max_size=256)
        self._beatmap_payload_cache = TTLCache[Any](ttl_seconds=self.config.beatmap_cache_ttl, max_size=512)

    @classmethod
    def from_client_credentials(
        cls,
        *,
        client_id: int | str,
        client_secret: str,
        resolver: BeatmapResolver | None = None,
        config: BotClientConfig | None = None,
        scope: str = 'public',
        base_url: str = 'https://osu.ppy.sh/api/v2',
        timeout: int = 15,
    ) -> 'OsuBotClient':
        api_client = OsuApiClient.from_client_credentials(
            client_id=client_id,
            client_secret=client_secret,
            scope=scope,
            base_url=base_url,
            timeout=timeout,
        )
        return cls(api_client=api_client, resolver=resolver, config=config)


    def _api_has_custom_async(self, name: str) -> bool:
        method = getattr(self.api, name, None)
        base = getattr(OsuApiClient, name, None)
        if method is None or base is None:
            return False
        func = getattr(method, '__func__', method)
        return func is not base

    def _cached(self, cache: TTLCache, key: str, loader):
        value = cache.get(key)
        if value is not None:
            return value
        value = loader()
        cache.set(key, value)
        return value

    async def _acached(self, cache: TTLCache, key: str, loader):
        value = cache.get(key)
        if value is not None:
            return value
        value = await loader()
        cache.set(key, value)
        return value

    def get_profile(self, user: str | int, *, mode: Optional[str] = None) -> ProfileResult:
        actual_mode = mode or self.config.default_mode
        key = f'profile:{actual_mode}:{user}'
        payload = self._cached(self._user_cache, key, lambda: self.api.lookup_user(user, mode=actual_mode))
        return ProfileResult.from_api_v2(payload)

    async def aget_profile(self, user: str | int, *, mode: Optional[str] = None) -> ProfileResult:
        actual_mode = mode or self.config.default_mode
        key = f'profile:{actual_mode}:{user}'
        payload = await self._acached(self._user_cache, key, lambda: self.api.alookup_user(user, mode=actual_mode) if self._api_has_custom_async('alookup_user') else __import__('asyncio').to_thread(self.api.lookup_user, user, mode=actual_mode))
        return ProfileResult.from_api_v2(payload)

    def get_beatmap_payload(self, beatmap_id: int) -> dict[str, Any]:
        key = f'beatmap:{beatmap_id}'
        return self._cached(self._beatmap_payload_cache, key, lambda: self.api.get_beatmap(beatmap_id))

    async def aget_beatmap_payload(self, beatmap_id: int) -> dict[str, Any]:
        key = f'beatmap:{beatmap_id}'
        return await self._acached(self._beatmap_payload_cache, key, lambda: self.api.aget_beatmap(beatmap_id) if self._api_has_custom_async('aget_beatmap') else __import__('asyncio').to_thread(self.api.get_beatmap, beatmap_id))

    def get_map(self, beatmap_id: int) -> MapResult:
        return MapResult.from_api_v2(self.get_beatmap_payload(beatmap_id))

    async def aget_map(self, beatmap_id: int) -> MapResult:
        return MapResult.from_api_v2(await self.aget_beatmap_payload(beatmap_id))

    def _resolve_beatmap(self, beatmap_id: int):
        self.get_beatmap_payload(beatmap_id)
        return self.resolver.resolve(beatmap_id=beatmap_id)

    async def _aresolve_beatmap(self, beatmap_id: int):
        await self.aget_beatmap_payload(beatmap_id)
        return await self.resolver.aresolve(beatmap_id=beatmap_id)

    def _make_play_result(self, kind: str, user: str | int, api_score: dict[str, Any], *, object_index: int | None = None, profile: ProfileResult | None = None, replay_frames: Sequence[ReplayFrame] | None = None) -> PlayResult:
        beatmap_id = api_score.get('beatmap_id') or (api_score.get('beatmap') or {}).get('id')
        if beatmap_id is None:
            raise OsuApiError('Score payload did not include a beatmap id.')
        beatmap = self._resolve_beatmap(int(beatmap_id))
        analysis = analyze_recent_play(beatmap=beatmap, api_score=api_score, object_index=object_index, replay_frames=replay_frames)
        return PlayResult(kind=kind, user_query=user, beatmap=beatmap, api_score=api_score, analysis=analysis, profile=profile)

    async def _amake_play_result(self, kind: str, user: str | int, api_score: dict[str, Any], *, object_index: int | None = None, profile: ProfileResult | None = None, replay_frames: Sequence[ReplayFrame] | None = None) -> PlayResult:
        beatmap_id = api_score.get('beatmap_id') or (api_score.get('beatmap') or {}).get('id')
        if beatmap_id is None:
            raise OsuApiError('Score payload did not include a beatmap id.')
        beatmap = await self._aresolve_beatmap(int(beatmap_id))
        analysis = analyze_recent_play(beatmap=beatmap, api_score=api_score, object_index=object_index, replay_frames=replay_frames)
        return PlayResult(kind=kind, user_query=user, beatmap=beatmap, api_score=api_score, analysis=analysis, profile=profile)

    def get_current_play(self, user: str | int, *, mode: Optional[str] = None, include_fails: bool = True, object_index: int | None = None, replay_frames: Sequence[ReplayFrame] | None = None) -> PlayResult:
        actual_mode = mode or self.config.default_mode
        profile = self.get_profile(user, mode=actual_mode)
        user_id = profile.user_id
        key = f'current:{actual_mode}:{user_id}:{int(include_fails)}'
        api_score = self._cached(self._score_cache, key, lambda: self.api.get_recent_score(user_id, actual_mode, include_fails))
        if not api_score:
            raise OsuApiError('No recent score found for this user.')
        return self._make_play_result('current', user, api_score, object_index=object_index, profile=profile, replay_frames=replay_frames)

    async def aget_current_play(self, user: str | int, *, mode: Optional[str] = None, include_fails: bool = True, object_index: int | None = None, replay_frames: Sequence[ReplayFrame] | None = None) -> PlayResult:
        actual_mode = mode or self.config.default_mode
        profile = await self.aget_profile(user, mode=actual_mode)
        user_id = profile.user_id
        key = f'current:{actual_mode}:{user_id}:{int(include_fails)}'
        api_score = await self._acached(self._score_cache, key, lambda: self.api.aget_recent_score(user_id, actual_mode, include_fails) if self._api_has_custom_async('aget_recent_score') else __import__('asyncio').to_thread(self.api.get_recent_score, user_id, actual_mode, include_fails))
        if not api_score:
            raise OsuApiError('No recent score found for this user.')
        return await self._amake_play_result('current', user, api_score, object_index=object_index, profile=profile, replay_frames=replay_frames)

    def get_recent_plays(self, user: str | int, *, mode: Optional[str] = None, include_fails: bool = True, limit: int = 5) -> PlayListResult:
        actual_mode = mode or self.config.default_mode
        profile = self.get_profile(user, mode=actual_mode)
        user_id = profile.user_id
        key = f'recent:{actual_mode}:{user_id}:{limit}:{int(include_fails)}'
        payload = self._cached(self._score_cache, key, lambda: self.api.get_recent_scores(user_id, actual_mode, include_fails, limit))
        plays = [self._make_play_result('recent', user, score, profile=profile) for score in (payload or [])[:limit]]
        return PlayListResult(kind='recent', user_query=user, plays=plays, profile=profile)

    async def aget_recent_plays(self, user: str | int, *, mode: Optional[str] = None, include_fails: bool = True, limit: int = 5) -> PlayListResult:
        actual_mode = mode or self.config.default_mode
        profile = await self.aget_profile(user, mode=actual_mode)
        user_id = profile.user_id
        key = f'recent:{actual_mode}:{user_id}:{limit}:{int(include_fails)}'
        payload = await self._acached(self._score_cache, key, lambda: self.api.aget_recent_scores(user_id, actual_mode, include_fails, limit) if self._api_has_custom_async('aget_recent_scores') else __import__('asyncio').to_thread(self.api.get_recent_scores, user_id, actual_mode, include_fails, limit))
        plays = [await self._amake_play_result('recent', user, score, profile=profile) for score in (payload or [])[:limit]]
        return PlayListResult(kind='recent', user_query=user, plays=plays, profile=profile)

    def get_recent_fails(self, user: str | int, *, mode: Optional[str] = None, limit: int = 5) -> PlayListResult:
        recent = self.get_recent_plays(user, mode=mode, include_fails=True, limit=max(limit * 3, limit))
        return PlayListResult(kind='fails', user_query=user, plays=[p for p in recent.plays if not p.passed][:limit], profile=recent.profile)

    async def aget_recent_fails(self, user: str | int, *, mode: Optional[str] = None, limit: int = 5) -> PlayListResult:
        recent = await self.aget_recent_plays(user, mode=mode, include_fails=True, limit=max(limit * 3, limit))
        return PlayListResult(kind='fails', user_query=user, plays=[p for p in recent.plays if not p.passed][:limit], profile=recent.profile)

    def get_top_plays(self, user: str | int, *, mode: Optional[str] = None, limit: int = 5, offset: int | None = None) -> PlayListResult:
        actual_mode = mode or self.config.default_mode
        profile = self.get_profile(user, mode=actual_mode)
        user_id = profile.user_id
        key = f'top:{actual_mode}:{user_id}:{limit}:{offset}'
        payload = self._cached(self._score_cache, key, lambda: self.api.get_best_scores(user_id, actual_mode, limit, offset))
        plays = [self._make_play_result('best', user, score, profile=profile) for score in (payload or [])[:limit]]
        return PlayListResult(kind='best', user_query=user, plays=plays, profile=profile)

    async def aget_top_plays(self, user: str | int, *, mode: Optional[str] = None, limit: int = 5, offset: int | None = None) -> PlayListResult:
        actual_mode = mode or self.config.default_mode
        profile = await self.aget_profile(user, mode=actual_mode)
        user_id = profile.user_id
        key = f'top:{actual_mode}:{user_id}:{limit}:{offset}'
        payload = await self._acached(self._score_cache, key, lambda: self.api.aget_best_scores(user_id, actual_mode, limit, offset) if self._api_has_custom_async('aget_best_scores') else __import__('asyncio').to_thread(self.api.get_best_scores, user_id, actual_mode, limit, offset))
        plays = [await self._amake_play_result('best', user, score, profile=profile) for score in (payload or [])[:limit]]
        return PlayListResult(kind='best', user_query=user, plays=plays, profile=profile)

    def get_best_play(self, user: str | int, *, mode: Optional[str] = None) -> PlayResult:
        top = self.get_top_plays(user, mode=mode, limit=1)
        if not top.plays:
            raise OsuApiError('No best score found for this user.')
        return top.plays[0]

    async def aget_best_play(self, user: str | int, *, mode: Optional[str] = None) -> PlayResult:
        top = await self.aget_top_plays(user, mode=mode, limit=1)
        if not top.plays:
            raise OsuApiError('No best score found for this user.')
        return top.plays[0]

    def compare_on_beatmap(self, left_user: str | int, right_user: str | int, *, beatmap_id: int, mode: Optional[str] = None, include_fails: bool = True) -> CompareResult:
        actual_mode = mode or self.config.default_mode

        def pick(user: str | int) -> PlayResult:
            profile = self.get_profile(user, mode=actual_mode)
            user_id = profile.user_id
            payload = self.api.get_recent_scores(user_id, actual_mode, include_fails, 10)
            for score in payload or []:
                score_beatmap_id = score.get('beatmap_id') or (score.get('beatmap') or {}).get('id')
                if score_beatmap_id == beatmap_id:
                    return self._make_play_result('recent', user, score, profile=profile)
            raise OsuApiError(f'No recent play found on beatmap {beatmap_id} for {user}.')

        left = pick(left_user)
        right = pick(right_user)
        return CompareResult(beatmap=left.beatmap, left=left, right=right)

    async def acompare_on_beatmap(self, left_user: str | int, right_user: str | int, *, beatmap_id: int, mode: Optional[str] = None, include_fails: bool = True) -> CompareResult:
        actual_mode = mode or self.config.default_mode

        async def pick(user: str | int) -> PlayResult:
            profile = await self.aget_profile(user, mode=actual_mode)
            user_id = profile.user_id
            payload = await (self.api.aget_recent_scores(user_id, actual_mode, include_fails, 10) if self._api_has_custom_async('aget_recent_scores') else __import__('asyncio').to_thread(self.api.get_recent_scores, user_id, actual_mode, include_fails, 10))
            for score in payload or []:
                score_beatmap_id = score.get('beatmap_id') or (score.get('beatmap') or {}).get('id')
                if score_beatmap_id == beatmap_id:
                    return await self._amake_play_result('recent', user, score, profile=profile)
            raise OsuApiError(f'No recent play found on beatmap {beatmap_id} for {user}.')

        left = await pick(left_user)
        right = await pick(right_user)
        return CompareResult(beatmap=left.beatmap, left=left, right=right)
