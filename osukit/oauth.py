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

import json
import time
from dataclasses import dataclass
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .errors import TokenError

try: # pragma: no cover - optional dependency
    import aiohttp
except Exception: # pragma: no cover - optional dependency
    aiohttp = None


class OAuthToken:
    def __init__(self, access_token: str, expires_at: float | None = None, *, expires_in: int | None = None, acquired_at: float | None = None, token_type: str = 'Bearer', scope: str | None = None):
        self.access_token = access_token
        if expires_at is None:
            base = time.time() if acquired_at is None else acquired_at
            expires_at = base + float(expires_in or 3600)
        self.expires_at = float(expires_at)
        self.token_type = token_type
        self.scope = scope

    def is_expired(self, leeway_seconds: int = 30, *, skew_seconds: int | None = None) -> bool:
        if skew_seconds is not None:
            leeway_seconds = skew_seconds
        return time.time() >= (self.expires_at - leeway_seconds)


class OsuOAuthClient:
    def __init__(
        self,
        *,
        client_id: int | str,
        client_secret: str,
        scope: str = 'public',
        token_url: str = 'https://osu.ppy.sh/oauth/token',
        timeout: int = 15,
        user_agent: str = 'osukit/1.4.0',
    ):
        self.client_id = str(client_id)
        self.client_secret = client_secret
        self.scope = scope
        self.token_url = token_url
        self.timeout = timeout
        self.user_agent = user_agent

    def _decode_token_payload(self, payload: dict[str, Any], *, scope: str | None = None) -> OAuthToken:
        access_token = payload.get('access_token')
        if not access_token:
            raise TokenError('OAuth response did not contain an access token.')
        expires_in = int(payload.get('expires_in', 3600) or 3600)
        return OAuthToken(
            access_token=str(access_token),
            expires_at=time.time() + expires_in,
            token_type=str(payload.get('token_type', 'Bearer')),
            scope=payload.get('scope') or scope,
        )

    def request_client_credentials_token(self, *, scope: Optional[str] = None) -> OAuthToken:
        body = json.dumps({
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials',
            'scope': scope or self.scope,
        }).encode('utf-8')
        req = Request(self.token_url, data=body, method='POST', headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': self.user_agent,
        })
        try:
            with urlopen(req, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode('utf-8'))
        except HTTPError as exc:
            raise TokenError(f'Failed to request OAuth token: HTTP {exc.code}') from exc
        except URLError as exc:
            raise TokenError(f'Failed to request OAuth token: {exc.reason}') from exc
        return self._decode_token_payload(payload, scope=scope)

    async def arequest_client_credentials_token(self, *, scope: Optional[str] = None) -> OAuthToken:
        if aiohttp is None: # pragma: no cover - fallback path
            import asyncio
            return await asyncio.to_thread(self.request_client_credentials_token, scope=scope)
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout), headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': self.user_agent,
        }) as session:
            async with session.post(self.token_url, json={
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials',
                'scope': scope or self.scope,
            }) as response:
                if response.status >= 400:
                    raise TokenError(f'Failed to request OAuth token: HTTP {response.status}')
                payload = await response.json()
        return self._decode_token_payload(payload, scope=scope)
