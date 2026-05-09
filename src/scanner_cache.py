"""
scanner_cache.py — Simple file-based cache with 24h TTL for scanner API responses.

Keys are MD5 hashes of the call arguments. Values are stored as JSON with a
timestamp. Thread-safe for concurrent reads and writes via atomic file replace.

Usage:
    from scanner_cache import cache_get, cache_set, make_key

    ck = make_key('fmp', 'quote', 'MRNA')
    val = cache_get(ck)
    if val is None:
        val = fetch_from_api()
        cache_set(ck, val)
"""

import hashlib
import json
import os
import tempfile
import time
from typing import Any, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(REPO_ROOT, 'data', 'cache')
DEFAULT_TTL = 86_400        # 24 hours — all FMP + SEC + ClinicalTrials data
DOC_TTL     = 86_400 * 3   # 72 hours for SEC filing text (changes very rarely)


def make_key(*parts: Any) -> str:
    """Build a stable cache key from any number of arguments."""
    raw = '|'.join(str(p) for p in parts)
    return hashlib.md5(raw.encode()).hexdigest()


def _path(key: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f'{key}.json')


def cache_get(key: str, ttl: int = DEFAULT_TTL) -> Optional[Any]:
    """Return cached value if it exists and is within TTL, else None."""
    try:
        p = _path(key)
        if not os.path.exists(p):
            return None
        with open(p) as f:
            entry = json.load(f)
        if time.time() - entry['ts'] > ttl:
            return None
        return entry['val']
    except Exception:
        return None


def cache_set(key: str, value: Any) -> None:
    """Write value to cache atomically (temp file + rename avoids partial reads)."""
    try:
        p = _path(key)
        payload = json.dumps({'ts': time.time(), 'val': value}, default=str)
        # Atomic write: write to temp file in same dir, then rename
        fd, tmp = tempfile.mkstemp(dir=CACHE_DIR, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(payload)
            os.replace(tmp, p)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
    except Exception:
        pass  # Cache failures are always silent


def cache_clear(older_than_days: int = 2) -> int:
    """Remove stale cache entries. Returns count of files removed."""
    cutoff = time.time() - older_than_days * 86_400
    removed = 0
    try:
        for fname in os.listdir(CACHE_DIR):
            if not fname.endswith('.json'):
                continue
            p = os.path.join(CACHE_DIR, fname)
            try:
                if os.path.getmtime(p) < cutoff:
                    os.remove(p)
                    removed += 1
            except OSError:
                pass
    except Exception:
        pass
    return removed

