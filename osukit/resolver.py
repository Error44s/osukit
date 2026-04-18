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

import hashlib
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try: # pragma: no cover - optional dependency
    import aiohttp
except Exception: # pragma: no cover - optional dependency
    aiohttp = None

from .api import Beatmap
from .errors import BeatmapResolveError, MissingBeatmapError


class BeatmapResolver:
    """Resolve .osu files from local cache, raw content, or beatmap IDs.

    This is intentionally lightweight and has no hard dependency on an API client.
    It downloads public beatmap files from osu! and stores them in a cache directory.
    """

    def __init__(self, cache_dir: str | Path | None = None, *, timeout: int = 20, user_agent: str = 'osukit/1.2.0'):
        self.cache_dir = Path(cache_dir or Path.home() / '.cache' / 'osukit_python' / 'beatmaps')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.user_agent = user_agent

    def cache_path_for(self, beatmap_id: int) -> Path:
        return self.cache_dir / f'{int(beatmap_id)}.osu'

    def find_cached(self, beatmap_id: int) -> Optional[Path]:
        path = self.cache_path_for(beatmap_id)
        return path if path.exists() else None

    def save_content(self, *, beatmap_id: Optional[int], content: str) -> Path:
        if beatmap_id is not None:
            path = self.cache_path_for(int(beatmap_id))
        else:
            digest = hashlib.sha1(content.encode('utf-8', errors='replace')).hexdigest()[:16]
            path = self.cache_dir / f'inline-{digest}.osu'
        path.write_text(content, encoding='utf-8')
        return path

    def download_content(self, beatmap_id: int) -> str:
        url = f'https://osu.ppy.sh/osu/{int(beatmap_id)}'
        req = Request(url, headers={'User-Agent': self.user_agent, 'Accept': 'text/plain'})
        try:
            with urlopen(req, timeout=self.timeout) as response:
                return response.read().decode('utf-8', errors='replace')
        except HTTPError as exc:
            raise BeatmapResolveError(f'Failed to download beatmap {beatmap_id}: HTTP {exc.code}') from exc
        except URLError as exc:
            raise BeatmapResolveError(f'Failed to download beatmap {beatmap_id}: {exc.reason}') from exc


    async def adownload_content(self, beatmap_id: int) -> str:
        if aiohttp is None: # pragma: no cover - fallback path
            import asyncio
            return await asyncio.to_thread(self.download_content, beatmap_id)
        url = f'https://osu.ppy.sh/osu/{int(beatmap_id)}'
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout, headers={'User-Agent': self.user_agent, 'Accept': 'text/plain'}) as session:
            async with session.get(url) as response:
                if response.status >= 400:
                    raise BeatmapResolveError(f'Failed to download beatmap {beatmap_id}: HTTP {response.status}')
                return await response.text()

    def get_or_download_path(self, beatmap_id: int, *, force: bool = False) -> Path:
        cached = self.find_cached(beatmap_id)
        if cached is not None and not force:
            return cached
        content = self.download_content(beatmap_id)
        return self.save_content(beatmap_id=beatmap_id, content=content)

    def resolve(
        self,
        *,
        beatmap_id: Optional[int] = None,
        beatmap_path: str | Path | None = None,
        beatmap_content: str | None = None,
        force_download: bool = False,
    ) -> Beatmap:
        if beatmap_content is not None:
            if beatmap_id is not None:
                self.save_content(beatmap_id=beatmap_id, content=beatmap_content)
            return Beatmap(content=beatmap_content)

        if beatmap_path is not None:
            return Beatmap(path=str(beatmap_path))

        if beatmap_id is None:
            raise MissingBeatmapError('A beatmap_id, beatmap_path, or beatmap_content is required.')

        path = self.get_or_download_path(int(beatmap_id), force=force_download)
        return Beatmap(path=str(path))

    async def aget_or_download_path(self, beatmap_id: int, *, force: bool = False) -> Path:
        cached = self.find_cached(beatmap_id)
        if cached is not None and not force:
            return cached
        content = await self.adownload_content(beatmap_id)
        return self.save_content(beatmap_id=beatmap_id, content=content)

    async def aresolve(
        self,
        *,
        beatmap_id: Optional[int] = None,
        beatmap_path: str | Path | None = None,
        beatmap_content: str | None = None,
        force_download: bool = False,
    ) -> Beatmap:
        if beatmap_content is not None:
            if beatmap_id is not None:
                self.save_content(beatmap_id=beatmap_id, content=beatmap_content)
            return Beatmap(content=beatmap_content)
        if beatmap_path is not None:
            return Beatmap(path=str(beatmap_path))
        if beatmap_id is None:
            raise MissingBeatmapError('A beatmap_id, beatmap_path, or beatmap_content is required.')
        path = await self.aget_or_download_path(int(beatmap_id), force=force_download)
        return Beatmap(path=str(path))
