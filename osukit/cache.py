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

import time
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expires_at: float

    def is_expired(self) -> bool:
        return time.time() >= self.expires_at


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: int = 300, max_size: int = 1024):
        self.ttl_seconds = max(1, int(ttl_seconds))
        self.max_size = max(1, int(max_size))
        self._store: dict[str, CacheEntry[T]] = {}

    def _evict(self) -> None:
        expired = [k for k, v in self._store.items() if v.is_expired()]
        for key in expired:
            self._store.pop(key, None)
        while len(self._store) > self.max_size:
            oldest_key = min(self._store, key=lambda k: self._store[k].expires_at)
            self._store.pop(oldest_key, None)

    def get(self, key: str) -> Optional[T]:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            self._store.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: T, *, ttl_seconds: int | None = None) -> T:
        ttl = self.ttl_seconds if ttl_seconds is None else max(1, int(ttl_seconds))
        self._store[key] = CacheEntry(value=value, expires_at=time.time() + ttl)
        self._evict()
        return value

    def clear(self) -> None:
        self._store.clear()
