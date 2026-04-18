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

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..errors import OsuApiError, RateLimitError, TokenError
from ..oauth import OAuthToken, OsuOAuthClient

try: # pragma: no cover - optional dependency
    import aiohttp
except Exception: # pragma: no cover - optional dependency
    aiohttp = None


@dataclass
class OsuApiClient:
    token: str | None = None
    base_url: str = 'https://osu.ppy.sh/api/v2'
    timeout: int = 15
    oauth: OsuOAuthClient | None = None
    oauth_token: OAuthToken | None = None
    user_agent: str = 'osukit/1.4.0'
    max_retries: int = 3
    retry_backoff: float = 0.5

    @classmethod
    def from_client_credentials(
        cls,
        *,
        client_id: int | str,
        client_secret: str,
        scope: str = 'public',
        base_url: str = 'https://osu.ppy.sh/api/v2',
        timeout: int = 15,
        max_retries: int = 3,
        retry_backoff: float = 0.5,
    ) -> 'OsuApiClient':
        oauth = OsuOAuthClient(client_id=client_id, client_secret=client_secret, scope=scope, timeout=timeout)
        token = oauth.request_client_credentials_token(scope=scope)
        return cls(
            token=token.access_token,
            base_url=base_url,
            timeout=timeout,
            oauth=oauth,
            oauth_token=token,
            max_retries=max_retries,
            retry_backoff=retry_backoff,
        )

    def ensure_token(self) -> str:
        if self.oauth_token is not None:
            if self.oauth_token.is_expired():
                if self.oauth is None:
                    raise TokenError('OAuth token is expired and no OAuth client is configured.')
                self.oauth_token = self.oauth.request_client_credentials_token(scope=self.oauth.scope)
                self.token = self.oauth_token.access_token
            return self.oauth_token.access_token
        if self.token:
            return self.token
        if self.oauth is not None:
            self.oauth_token = self.oauth.request_client_credentials_token(scope=self.oauth.scope)
            self.token = self.oauth_token.access_token
            return self.oauth_token.access_token
        raise TokenError('No OAuth token configured for OsuApiClient.')

    async def aensure_token(self) -> str:
        if self.oauth_token is not None and not self.oauth_token.is_expired():
            return self.oauth_token.access_token
        if self.token and self.oauth is None:
            return self.token
        if self.oauth is not None:
            self.oauth_token = await self.oauth.arequest_client_credentials_token(scope=self.oauth.scope)
            self.token = self.oauth_token.access_token
            return self.oauth_token.access_token
        raise TokenError('No OAuth token configured for OsuApiClient.')

    def _build_url(self, path: str, **query: Any) -> str:
        clean_query = {k: v for k, v in query.items() if v is not None}
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        if clean_query:
            url += '?' + urlencode(clean_query)
        return url

    def _handle_http_error(self, exc: HTTPError, path: str):
        retry_after = exc.headers.get('Retry-After') if exc.headers else None
        retry_after_value = float(retry_after) if retry_after else None
        if exc.code == 429:
            raise RateLimitError(f'osu! API rate limited request for {path}', retry_after=retry_after_value) from exc
        if exc.code == 401 and self.oauth is not None:
            self.oauth_token = None
            self.token = None
        raise OsuApiError(f'osu! API returned HTTP {exc.code} for {path}') from exc

    def _sleep_for_attempt(self, attempt: int, retry_after: float | None = None):
        delay = retry_after if retry_after is not None else self.retry_backoff * (2 ** attempt)
        time.sleep(delay)

    async def _asleep_for_attempt(self, attempt: int, retry_after: float | None = None):
        delay = retry_after if retry_after is not None else self.retry_backoff * (2 ** attempt)
        await asyncio.sleep(delay)

    def _get(self, path: str, **query: Any) -> Dict[str, Any] | list[Any]:
        url = self._build_url(path, **query)
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            req = Request(url, headers={
                'Authorization': f'Bearer {self.ensure_token()}',
                'Accept': 'application/json',
                'User-Agent': self.user_agent,
            })
            try:
                with urlopen(req, timeout=self.timeout) as response:
                    return json.loads(response.read().decode('utf-8'))
            except HTTPError as exc:
                last_exc = exc
                if exc.code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                    retry_after = exc.headers.get('Retry-After') if exc.headers else None
                    self._sleep_for_attempt(attempt, float(retry_after) if retry_after else None)
                    if exc.code == 401:
                        self.oauth_token = None
                        self.token = None
                    continue
                self._handle_http_error(exc, path)
            except URLError as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    self._sleep_for_attempt(attempt)
                    continue
                raise OsuApiError(f'osu! API request failed for {path}: {exc.reason}') from exc
        if last_exc is not None:
            raise OsuApiError(f'osu! API request failed for {path}: {last_exc}')
        raise OsuApiError(f'osu! API request failed for {path}: unknown error')

    async def _aget(self, path: str, **query: Any) -> Dict[str, Any] | list[Any]:
        if aiohttp is None:  # pragma: no cover - optional dependency
            return await asyncio.to_thread(self._get, path, **query)
        url = self._build_url(path, **query)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            headers = {
                'Authorization': f'Bearer {await self.aensure_token()}',
                'Accept': 'application/json',
                'User-Agent': self.user_agent,
            }
            try:
                async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                    async with session.get(url) as response:
                        if response.status in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                            retry_after = response.headers.get('Retry-After')
                            await self._asleep_for_attempt(attempt, float(retry_after) if retry_after else None)
                            continue
                        if response.status == 401 and self.oauth is not None:
                            self.oauth_token = None
                            self.token = None
                        if response.status >= 400:
                            if response.status == 429:
                                raise RateLimitError(f'osu! API rate limited request for {path}', retry_after=float(response.headers.get('Retry-After') or 0) or None)
                            raise OsuApiError(f'osu! API returned HTTP {response.status} for {path}')
                        return await response.json()
            except (aiohttp.ClientError, asyncio.TimeoutError, RateLimitError, OsuApiError) as exc:
                last_exc = exc
                if attempt < self.max_retries and not isinstance(exc, RateLimitError):
                    await self._asleep_for_attempt(attempt)
                    continue
                raise
        if last_exc is not None:
            raise OsuApiError(f'osu! API request failed for {path}: {last_exc}')
        raise OsuApiError(f'osu! API request failed for {path}: unknown error')

    def get_user(self, user: str | int, mode: Optional[str] = None) -> Dict[str, Any]:
        return self._get(f'users/{user}/{mode}' if mode else f'users/{user}')

    async def aget_user(self, user: str | int, mode: Optional[str] = None) -> Dict[str, Any]:
        return await self._aget(f'users/{user}/{mode}' if mode else f'users/{user}')

    def get_user_scores(self, user_id: int | str, score_type: str, *, mode: str = 'osu', include_fails: Optional[bool] = None, limit: int = 5, offset: Optional[int] = None) -> Dict[str, Any] | list[Any]:
        return self._get(
            f'users/{user_id}/scores/{score_type}',
            mode=mode,
            include_fails=1 if include_fails else (0 if include_fails is not None else None),
            limit=limit,
            offset=offset,
        )

    async def aget_user_scores(self, user_id: int | str, score_type: str, *, mode: str = 'osu', include_fails: Optional[bool] = None, limit: int = 5, offset: Optional[int] = None) -> Dict[str, Any] | list[Any]:
        return await self._aget(
            f'users/{user_id}/scores/{score_type}',
            mode=mode,
            include_fails=1 if include_fails else (0 if include_fails is not None else None),
            limit=limit,
            offset=offset,
        )

    def get_recent_scores(self, user_id: int | str, mode: str = 'osu', include_fails: bool = True, limit: int = 5) -> Dict[str, Any] | list[Any]:
        return self.get_user_scores(user_id, 'recent', mode=mode, include_fails=include_fails, limit=limit)

    async def aget_recent_scores(self, user_id: int | str, mode: str = 'osu', include_fails: bool = True, limit: int = 5) -> Dict[str, Any] | list[Any]:
        return await self.aget_user_scores(user_id, 'recent', mode=mode, include_fails=include_fails, limit=limit)

    def get_best_scores(self, user_id: int | str, mode: str = 'osu', limit: int = 5, offset: Optional[int] = None) -> Dict[str, Any] | list[Any]:
        return self.get_user_scores(user_id, 'best', mode=mode, limit=limit, offset=offset)

    async def aget_best_scores(self, user_id: int | str, mode: str = 'osu', limit: int = 5, offset: Optional[int] = None) -> Dict[str, Any] | list[Any]:
        return await self.aget_user_scores(user_id, 'best', mode=mode, limit=limit, offset=offset)

    def get_first_scores(self, user_id: int | str, mode: str = 'osu', limit: int = 5, offset: Optional[int] = None) -> Dict[str, Any] | list[Any]:
        return self.get_user_scores(user_id, 'firsts', mode=mode, limit=limit, offset=offset)

    def get_beatmap(self, beatmap_id: int) -> Dict[str, Any]:
        return self._get(f'beatmaps/{beatmap_id}')

    async def aget_beatmap(self, beatmap_id: int) -> Dict[str, Any]:
        return await self._aget(f'beatmaps/{beatmap_id}')

    def get_beatmapset(self, beatmapset_id: int) -> Dict[str, Any]:
        return self._get(f'beatmapsets/{beatmapset_id}')

    async def aget_beatmapset(self, beatmapset_id: int) -> Dict[str, Any]:
        return await self._aget(f'beatmapsets/{beatmapset_id}')

    def get_score_lazer(self, score_id: int, *, mode: str = 'osu') -> Dict[str, Any]:
        return self._get(f'scores/{mode}/{score_id}')

    def lookup_user(self, user: str | int, *, mode: str = 'osu') -> Dict[str, Any]:
        return self.get_user(user=user, mode=mode)

    async def alookup_user(self, user: str | int, *, mode: str = 'osu') -> Dict[str, Any]:
        return await self.aget_user(user=user, mode=mode)

    def _first_score(self, payload: Dict[str, Any] | list[Any]) -> Dict[str, Any] | None:
        if isinstance(payload, list):
            return payload[0] if payload else None
        data = payload.get('scores') if isinstance(payload, dict) else None
        if isinstance(data, list):
            return data[0] if data else None
        return None

    def get_recent_score(self, user_id: int | str, mode: str = 'osu', include_fails: bool = True) -> Dict[str, Any] | None:
        return self._first_score(self.get_recent_scores(user_id=user_id, mode=mode, include_fails=include_fails, limit=1))

    async def aget_recent_score(self, user_id: int | str, mode: str = 'osu', include_fails: bool = True) -> Dict[str, Any] | None:
        payload = await self.aget_recent_scores(user_id=user_id, mode=mode, include_fails=include_fails, limit=1)
        return self._first_score(payload)

    def get_best_score(self, user_id: int | str, mode: str = 'osu') -> Dict[str, Any] | None:
        return self._first_score(self.get_best_scores(user_id=user_id, mode=mode, limit=1))

    async def aget_best_score(self, user_id: int | str, mode: str = 'osu') -> Dict[str, Any] | None:
        payload = await self.aget_best_scores(user_id=user_id, mode=mode, limit=1)
        return self._first_score(payload)
