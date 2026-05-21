"""
external_source_provider.py — External source/news provider abstraction.

Allows the system to search for news when configured.
Default: disabled. Does not require paid search for normal operation.

Environment variables:
  EXTERNAL_RESEARCH_ENABLED   true/false (default: false)
  NEWS_SEARCH_PROVIDER        disabled | serpapi | google_custom | brave (default: disabled)
  NEWS_SEARCH_MAX_RESULTS     integer (default: 5)
  SERPAPI_API_KEY             required for provider=serpapi
  GOOGLE_SEARCH_API_KEY       required for provider=google_custom
  GOOGLE_SEARCH_ENGINE_ID     required for provider=google_custom
  BRAVE_SEARCH_API_KEY        required for provider=brave
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

EXTERNAL_RESEARCH_ENABLED = os.environ.get('EXTERNAL_RESEARCH_ENABLED', 'false').lower() == 'true'
NEWS_SEARCH_PROVIDER       = os.environ.get('NEWS_SEARCH_PROVIDER', 'disabled').strip().lower()
NEWS_SEARCH_MAX_RESULTS    = int(os.environ.get('NEWS_SEARCH_MAX_RESULTS', '5'))


# ── Status ────────────────────────────────────────────────────────────────────

def get_external_research_status() -> dict:
    """Return current external research configuration."""
    # Re-read env on each call to allow dynamic override
    enabled  = os.environ.get('EXTERNAL_RESEARCH_ENABLED', 'false').lower() == 'true'
    provider = os.environ.get('NEWS_SEARCH_PROVIDER', 'disabled').strip().lower()
    max_res  = int(os.environ.get('NEWS_SEARCH_MAX_RESULTS', '5'))

    # Check for available API keys
    serpapi_key = bool(os.environ.get('SERPAPI_API_KEY', '').strip())
    google_key  = bool(os.environ.get('GOOGLE_SEARCH_API_KEY', '').strip())
    brave_key   = bool(os.environ.get('BRAVE_SEARCH_API_KEY', '').strip())

    return {
        'enabled':           enabled,
        'provider':          provider,
        'max_results':       max_res,
        'status':            'enabled' if enabled else 'disabled',
        'serpapi_key_set':   serpapi_key,
        'google_key_set':    google_key,
        'brave_key_set':     brave_key,
        'available_providers': _get_available_providers(),
    }


def _get_available_providers() -> list[str]:
    """List which providers have API keys configured."""
    providers: list[str] = []
    if os.environ.get('SERPAPI_API_KEY', '').strip():
        providers.append('serpapi')
    if os.environ.get('GOOGLE_SEARCH_API_KEY', '').strip() and os.environ.get('GOOGLE_SEARCH_ENGINE_ID', '').strip():
        providers.append('google_custom')
    if os.environ.get('BRAVE_SEARCH_API_KEY', '').strip():
        providers.append('brave')
    return providers


def _disabled_result(query_type: str, query: str = '') -> dict:
    """Standard disabled result format."""
    return {
        'enabled':    False,
        'status':     'disabled',
        'query_type': query_type,
        'query':      query,
        'results':    [],
        'message':    (
            'External research disabled. '
            'Set EXTERNAL_RESEARCH_ENABLED=true and NEWS_SEARCH_PROVIDER '
            '(serpapi|google_custom|brave) with corresponding API key to enable. '
            'This is required to detect TSRO-type media-reported sale process signals.'
        ),
    }


def _error_result(query_type: str, query: str, error: str) -> dict:
    """Standard error result format."""
    return {
        'enabled':    True,
        'status':     'error',
        'query_type': query_type,
        'query':      query,
        'results':    [],
        'error':      error,
    }


def _success_result(query_type: str, query: str, results: list[dict]) -> dict:
    """Standard success result format."""
    return {
        'enabled':    True,
        'status':     'ok',
        'query_type': query_type,
        'query':      query,
        'results':    results,
        'count':      len(results),
    }


# ── Search functions ──────────────────────────────────────────────────────────

def search_company_deal_status(ticker: str, company_name: str) -> dict:
    """Search for current deal/acquisition status of a company."""
    enabled = os.environ.get('EXTERNAL_RESEARCH_ENABLED', 'false').lower() == 'true'
    if not enabled:
        return _disabled_result('deal_status')

    query = f'"{company_name}" OR "{ticker}" acquisition merger deal strategic alternatives 2024 2025'
    results = _execute_search(query)
    if isinstance(results, str):
        return _error_result('deal_status', query, results)
    return _success_result('deal_status', query, results)


def search_recent_acquisition_news(ticker: str, company_name: str) -> dict:
    """Search for recent acquisition/M&A news about a company."""
    enabled = os.environ.get('EXTERNAL_RESEARCH_ENABLED', 'false').lower() == 'true'
    if not enabled:
        return _disabled_result('acquisition_news')

    query = f'"{company_name}" acquisition takeover buyout bid offer deal'
    results = _execute_search(query)
    if isinstance(results, str):
        return _error_result('acquisition_news', query, results)
    return _success_result('acquisition_news', query, results)


def search_strategic_review_news(ticker: str, company_name: str) -> dict:
    """Search for strategic review / alternatives process news."""
    enabled = os.environ.get('EXTERNAL_RESEARCH_ENABLED', 'false').lower() == 'true'
    if not enabled:
        return _disabled_result('strategic_review')

    query = f'"{company_name}" "strategic alternatives" OR "strategic review" OR "sale process" OR "exploring sale"'
    results = _execute_search(query)
    if isinstance(results, str):
        return _error_result('strategic_review', query, results)
    return _success_result('strategic_review', query, results)


def search_completed_deal_background(ticker: str, company_name: str) -> dict:
    """Search for background on a completed or rumored acquisition."""
    enabled = os.environ.get('EXTERNAL_RESEARCH_ENABLED', 'false').lower() == 'true'
    if not enabled:
        return _disabled_result('completed_deal_background')

    query = f'"{company_name}" {ticker} acquired merger completed deal background'
    results = _execute_search(query)
    if isinstance(results, str):
        return _error_result('completed_deal_background', query, results)
    return _success_result('completed_deal_background', query, results)


# ── Provider implementations ──────────────────────────────────────────────────

def _execute_search(query: str) -> list[dict] | str:
    """
    Execute a search using the configured provider.
    Returns list of result dicts or error string.
    """
    provider = os.environ.get('NEWS_SEARCH_PROVIDER', 'disabled').strip().lower()
    max_results = int(os.environ.get('NEWS_SEARCH_MAX_RESULTS', '5'))

    if provider == 'serpapi':
        return _serpapi_search(query, max_results)
    elif provider == 'google_custom':
        return _google_custom_search(query, max_results)
    elif provider == 'brave':
        return _brave_search(query, max_results)
    else:
        return []  # Unknown provider — return empty


def _serpapi_search(query: str, max_results: int) -> list[dict] | str:
    """
    SerpAPI implementation.
    Only active if SERPAPI_API_KEY is set.
    """
    api_key = os.environ.get('SERPAPI_API_KEY', '').strip()
    if not api_key:
        return 'SERPAPI_API_KEY not set'

    try:
        params = {
            'q':       query,
            'api_key': api_key,
            'engine':  'google',
            'num':     str(max_results),
            'hl':      'en',
            'gl':      'us',
            'tbm':     'nws',  # News search
        }
        url = 'https://serpapi.com/search?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={'User-Agent': 'ma-scanner-research/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        raw_results = data.get('news_results', data.get('organic_results', []))
        return [
            {
                'title':   r.get('title', ''),
                'snippet': r.get('snippet', ''),
                'url':     r.get('link', ''),
                'date':    r.get('date', ''),
                'source':  r.get('source', ''),
            }
            for r in raw_results[:max_results]
        ]
    except Exception as exc:
        return f'SerpAPI error: {exc}'


def _google_custom_search(query: str, max_results: int) -> list[dict] | str:
    """
    Google Custom Search API implementation.
    Requires GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID.
    """
    api_key   = os.environ.get('GOOGLE_SEARCH_API_KEY', '').strip()
    engine_id = os.environ.get('GOOGLE_SEARCH_ENGINE_ID', '').strip()

    if not api_key:
        return 'GOOGLE_SEARCH_API_KEY not set'
    if not engine_id:
        return 'GOOGLE_SEARCH_ENGINE_ID not set'

    try:
        params = {
            'q':   query,
            'key': api_key,
            'cx':  engine_id,
            'num': str(min(max_results, 10)),
        }
        url = 'https://www.googleapis.com/customsearch/v1?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={'User-Agent': 'ma-scanner-research/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        items = data.get('items', [])
        return [
            {
                'title':   item.get('title', ''),
                'snippet': item.get('snippet', ''),
                'url':     item.get('link', ''),
                'date':    item.get('pagemap', {}).get('metatags', [{}])[0].get('article:published_time', ''),
                'source':  item.get('displayLink', ''),
            }
            for item in items[:max_results]
        ]
    except Exception as exc:
        return f'Google Custom Search error: {exc}'


def _brave_search(query: str, max_results: int) -> list[dict] | str:
    """
    Brave Search API implementation.
    Requires BRAVE_SEARCH_API_KEY.
    """
    api_key = os.environ.get('BRAVE_SEARCH_API_KEY', '').strip()
    if not api_key:
        return 'BRAVE_SEARCH_API_KEY not set'

    try:
        params = {
            'q':     query,
            'count': str(min(max_results, 20)),
        }
        url = 'https://api.search.brave.com/res/v1/news/search?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url,
            headers={
                'Accept':           'application/json',
                'Accept-Encoding':  'gzip',
                'X-Subscription-Token': api_key,
                'User-Agent':       'ma-scanner-research/1.0',
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        results = data.get('results', [])
        return [
            {
                'title':   r.get('title', ''),
                'snippet': r.get('description', ''),
                'url':     r.get('url', ''),
                'date':    r.get('age', ''),
                'source':  r.get('meta_url', {}).get('netloc', ''),
            }
            for r in results[:max_results]
        ]
    except Exception as exc:
        return f'Brave Search error: {exc}'


# ── Formatting helpers ────────────────────────────────────────────────────────

def format_source_for_prompt(source: dict) -> str:
    """Format a single search result for inclusion in LLM prompt."""
    title   = str(source.get('title', '') or '').strip()
    snippet = str(source.get('snippet', '') or '').strip()
    url     = str(source.get('url', '') or '').strip()
    date    = str(source.get('date', '') or '').strip()
    src     = str(source.get('source', '') or '').strip()

    parts: list[str] = []
    if title:
        parts.append(f'  Title: {title}')
    if src and date:
        parts.append(f'  Source: {src} ({date})')
    elif src:
        parts.append(f'  Source: {src}')
    elif date:
        parts.append(f'  Date: {date}')
    if snippet:
        parts.append(f'  Summary: {snippet[:300]}')
    if url:
        parts.append(f'  URL: {url}')

    return '\n'.join(parts)


def format_external_research_for_prompt(research_results: list[dict]) -> str:
    """Format all external research results for LLM prompt context."""
    if not research_results:
        status = get_external_research_status()
        if not status['enabled']:
            return (
                'EXTERNAL RESEARCH: Disabled.\n'
                'EDGAR-only workflow cannot detect TSRO-type media-reported sale process signals.\n'
                'To enable: set EXTERNAL_RESEARCH_ENABLED=true and NEWS_SEARCH_PROVIDER with API key.'
            )
        return 'EXTERNAL RESEARCH: No results returned.'

    lines: list[str] = ['EXTERNAL RESEARCH RESULTS:']

    for res in research_results:
        q_type  = res.get('query_type', '')
        status  = res.get('status', '')
        results = res.get('results', [])
        query   = res.get('query', '')

        if status == 'disabled':
            lines.append(f'  [{q_type}]: Disabled — {res.get("message", "")[:150]}')
            continue
        if status == 'error':
            lines.append(f'  [{q_type}]: Error — {res.get("error", "")}')
            continue

        lines.append(f'  [{q_type}] ({len(results)} results for: {query[:80]})')
        for i, source in enumerate(results[:3], 1):
            lines.append(f'  Result {i}:')
            lines.append(format_source_for_prompt(source))
        lines.append('')

    return '\n'.join(lines)
