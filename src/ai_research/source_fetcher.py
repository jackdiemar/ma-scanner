"""
source_fetcher.py — Fetch and cache SEC EDGAR filing text for AI research cases.

Fetches raw text from source_url (SEC EDGAR or news) and caches under
data/ai_research/source_cache/<url_hash>.txt

SEC user-agent requirement: company name + contact email per EDGAR access rules.
Cache policy: once fetched per URL, never re-fetched unless force=True.

No auto-trading. No broker APIs. No transaction recommendation language.
"""
from __future__ import annotations

import hashlib
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_HERE   = Path(__file__).resolve().parent
_SRCDIR = _HERE.parent
REPO    = _SRCDIR.parent

SOURCE_CACHE_DIR = REPO / 'data' / 'ai_research' / 'source_cache'

SEC_USER_AGENT = 'MA-Scanner Research Bot research@blackstarlightcapital.com'
FETCH_TIMEOUT  = 30  # seconds — single timeout value for urllib


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:24]


def _cache_path(url: str) -> Path:
    return SOURCE_CACHE_DIR / f'{_url_hash(url)}.txt'


def _load_cached(url: str) -> str | None:
    p = _cache_path(url)
    if not p.exists():
        return None
    try:
        return p.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return None


def _save_cached(url: str, text: str) -> None:
    try:
        SOURCE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(url).write_text(text, encoding='utf-8')
    except OSError:
        pass  # never fail a research run for a cache write error


def _is_sec_url(url: str) -> bool:
    return 'sec.gov' in url or 'edgar' in url.lower()


def _fetch_url(url: str) -> tuple[str, str | None]:
    """
    HTTP GET url. Returns (text, error).
    Uses SEC-compliant user-agent for EDGAR URLs.
    """
    headers: dict[str, str] = {}
    if _is_sec_url(url):
        headers['User-Agent'] = SEC_USER_AGENT
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            raw      = resp.read()
            ct       = resp.headers.get('Content-Type', '')
            charset  = 'utf-8'
            if 'charset=' in ct:
                charset = ct.split('charset=')[-1].split(';')[0].strip() or 'utf-8'
            return raw.decode(charset, errors='replace'), None
    except urllib.error.HTTPError as exc:
        return '', f'HTTP {exc.code}: {exc.reason}'
    except Exception as exc:
        return '', str(exc)


def fetch_filing_text(url: str, force: bool = False) -> dict[str, Any]:
    """
    Fetch and cache the text of a filing URL.

    Args:
        url:   Source URL from scanner case.
        force: If True, bypass cache and re-fetch.

    Returns dict:
        text          — full text of the filing (may be empty on error)
        fetched_at    — ISO timestamp of fetch (None if from cache)
        source_url    — the URL fetched
        cached        — True if returned from disk cache
        error         — error string if fetch failed, else None
    """
    if not url or not url.strip():
        return {
            'text': '', 'fetched_at': None, 'source_url': url,
            'cached': False, 'error': 'No source URL provided.',
        }

    if not force:
        cached = _load_cached(url)
        if cached is not None:
            return {
                'text': cached, 'fetched_at': None, 'source_url': url,
                'cached': True, 'error': None,
            }

    text, error = _fetch_url(url)
    fetched_at  = datetime.now(timezone.utc).isoformat()

    if error:
        return {
            'text': '', 'fetched_at': fetched_at, 'source_url': url,
            'cached': False, 'error': error,
        }
    if text:
        _save_cached(url, text)
    return {
        'text': text, 'fetched_at': fetched_at, 'source_url': url,
        'cached': False, 'error': None,
    }


def fetch_sec_filing_text_for_case(case: dict, force: bool = False) -> dict[str, Any]:
    """Convenience wrapper: fetch the filing text for a research case by source_url."""
    url = str(case.get('source_url', '')).strip()
    return fetch_filing_text(url, force=force)
