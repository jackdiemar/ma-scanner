"""
investment_gate.py — AI investment gate: takes a research case, runs LLM, returns decision.

In dry-run mode: returns a placeholder dict without calling the API.
In live mode: calls LLMClient, parses JSON, validates schema.
No transaction recommendations and no broker APIs.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

_HERE   = Path(__file__).resolve().parent
_SRCDIR = _HERE.parent
REPO    = _SRCDIR.parent

# Ensure src/ is on sys.path for direct script execution
if str(_SRCDIR) not in sys.path:
    sys.path.insert(0, str(_SRCDIR))

CACHE_DIR = REPO / 'data' / 'ai_research' / 'cache'


# ── Fingerprint cache ─────────────────────────────────────────────────────────

def _case_fingerprint(case: dict) -> str:
    """SHA-256 of the fields that uniquely identify a case signal. Rotates daily."""
    key = '|'.join([
        str(case.get('ticker', '')),
        str(case.get('filing_date', '')),
        str(case.get('filing_type', '')),
        str(case.get('trigger_phrase', '')),
        str(case.get('source_excerpt', ''))[:200],
    ])
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _cache_path() -> Path:
    return CACHE_DIR / f'gate_cache_{date.today().isoformat()}.json'


def _load_gate_cache() -> dict:
    p = _cache_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _save_gate_cache(cache: dict) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path().write_text(json.dumps(cache, indent=2, default=str), encoding='utf-8')
    except OSError:
        pass  # never fail the gate for a cache write error


def cache_status(case: dict) -> tuple[str, str]:
    """Return (fingerprint, hit|miss) for a case without writing cache files."""
    fingerprint = _case_fingerprint(case)
    cache = _load_gate_cache()
    return fingerprint, 'hit' if fingerprint in cache else 'miss'


# ── Schema defaults ───────────────────────────────────────────────────────────

_VALID_CLASSIFICATIONS = frozenset({
    'PRE_PROCESS_OPPORTUNITY',
    'REAL_STRATEGIC_REVIEW',
    'ALREADY_ANNOUNCED_DEAL',
    'GENERIC_PARTNERSHIP_LANGUAGE',
    'ASSET_SPECIFIC_ONLY',
    'FALSE_POSITIVE',
    'WATCH_ONLY',
    'DISCARD',
    'NEEDS_HUMAN_REVIEW',
})

_VALID_RESEARCH_ACTIONS = frozenset({
    'ESCALATE',
    'WATCH',
    'WAIT_FOR_PRICE',
    'DISCARD',
    'NEEDS_HUMAN_REVIEW',
})

_VALID_EVIDENCE_STRENGTH = frozenset({'HIGH', 'MEDIUM', 'LOW'})
_VALID_PRICED_IN         = frozenset({'NOT_PRICED_IN', 'PARTLY_REPRICED', 'LIKELY_PRICED_IN', 'UNKNOWN'})
_VALID_TIME_SENSITIVITY  = frozenset({'HIGH', 'MEDIUM', 'LOW'})


def _dry_run_decision(ticker: str, note: str = 'DRY_RUN') -> dict:
    return {
        'ticker':                  ticker,
        'classification':          'NEEDS_HUMAN_REVIEW',
        'research_action':         'NEEDS_HUMAN_REVIEW',
        'confidence':              0.0,
        'investability_score':     0,
        'evidence_strength':       'LOW',
        'priced_in_assessment':    'UNKNOWN',
        'time_sensitivity':        'LOW',
        'why_interesting':         [],
        'why_not':                 [],
        'key_evidence':            [],
        'missing_information':     [],
        'next_research_steps':     [],
        'human_review_questions':  [],
        'note':                    note,
        'ran_at':                  datetime.now(timezone.utc).isoformat(),
    }


_REQUIRED_DECISION_FIELDS = frozenset(
    k for k in _dry_run_decision('SCHEMA_CHECK').keys()
    if k != 'note'
)


def validate_decision_schema(decision: dict) -> list[str]:
    """Return schema validation errors for a gate decision dict."""
    errors: list[str] = []
    missing = sorted(_REQUIRED_DECISION_FIELDS - set(decision.keys()))
    if missing:
        errors.append(f'Missing fields: {", ".join(missing)}')
    if not isinstance(decision.get('why_interesting', []), list):
        errors.append('why_interesting must be a list')
    if not isinstance(decision.get('why_not', []), list):
        errors.append('why_not must be a list')
    if not isinstance(decision.get('key_evidence', []), list):
        errors.append('key_evidence must be a list')
    if not isinstance(decision.get('missing_information', []), list):
        errors.append('missing_information must be a list')
    if not isinstance(decision.get('next_research_steps', []), list):
        errors.append('next_research_steps must be a list')
    if not isinstance(decision.get('human_review_questions', []), list):
        errors.append('human_review_questions must be a list')
    return errors


def _parse_llm_response(raw: str, ticker: str) -> dict:
    """
    Parse and validate the LLM JSON response.
    Returns a validated dict. Falls back to a partial dict with errors noted.
    """
    raw = raw.strip()

    # Strip markdown fences if model produces them despite instructions
    if raw.startswith('```'):
        lines = raw.splitlines()
        # Drop first and last fence lines
        inner = []
        fence_seen = False
        for line in lines:
            if line.startswith('```'):
                if not fence_seen:
                    fence_seen = True
                    continue
                else:
                    break
            inner.append(line)
        raw = '\n'.join(inner).strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            **_dry_run_decision(ticker, note='PARSE_ERROR'),
            'parse_error': f'JSON decode failed: {exc}',
            'raw_response_excerpt': raw[:500],
        }

    if not isinstance(data, dict):
        return {
            **_dry_run_decision(ticker, note='PARSE_ERROR'),
            'parse_error': 'LLM response was not a JSON object.',
        }

    # Validate and coerce fields
    errors: list[str] = []

    classification = str(data.get('classification', '')).strip().upper()
    if classification not in _VALID_CLASSIFICATIONS:
        errors.append(f'Invalid classification: {classification!r}')
        classification = 'NEEDS_HUMAN_REVIEW'

    research_action = str(data.get('research_action', '')).strip().upper()
    if research_action not in _VALID_RESEARCH_ACTIONS:
        errors.append(f'Invalid research_action: {research_action!r}')
        research_action = 'NEEDS_HUMAN_REVIEW'

    try:
        confidence = float(data.get('confidence', 0.0))
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.0

    try:
        investability_score = int(data.get('investability_score', 0))
        investability_score = max(0, min(100, investability_score))
    except (TypeError, ValueError):
        investability_score = 0

    evidence_strength = str(data.get('evidence_strength', 'LOW')).strip().upper()
    if evidence_strength not in _VALID_EVIDENCE_STRENGTH:
        evidence_strength = 'LOW'

    priced_in = str(data.get('priced_in_assessment', 'UNKNOWN')).strip().upper()
    if priced_in not in _VALID_PRICED_IN:
        priced_in = 'UNKNOWN'

    time_sensitivity = str(data.get('time_sensitivity', 'LOW')).strip().upper()
    if time_sensitivity not in _VALID_TIME_SENSITIVITY:
        time_sensitivity = 'LOW'

    def _list_of_str(key: str) -> list[str]:
        val = data.get(key, [])
        if isinstance(val, list):
            return [str(v) for v in val if v]
        return []

    result = {
        'ticker':                  ticker,
        'classification':          classification,
        'research_action':         research_action,
        'confidence':              confidence,
        'investability_score':     investability_score,
        'evidence_strength':       evidence_strength,
        'priced_in_assessment':    priced_in,
        'time_sensitivity':        time_sensitivity,
        'why_interesting':         _list_of_str('why_interesting'),
        'why_not':                 _list_of_str('why_not'),
        'key_evidence':            _list_of_str('key_evidence'),
        'missing_information':     _list_of_str('missing_information'),
        'next_research_steps':     _list_of_str('next_research_steps'),
        'human_review_questions':  _list_of_str('human_review_questions'),
        'ran_at':                  datetime.now(timezone.utc).isoformat(),
    }

    if errors:
        result['validation_errors'] = errors

    return result


# ── Public API ────────────────────────────────────────────────────────────────

def run_gate(
    case: dict,
    client=None,
    dry_run: bool | None = None,
) -> dict:
    """
    Run the investment gate on a research case dict.

    Args:
        case:    Research case dict (output of research_case_builder).
        client:  LLMClient instance. If None, one is created from config.
        dry_run: Override dry_run config. If None, uses client config.

    Returns:
        Decision dict matching the gate output schema.
        Never raises — errors are captured in the returned dict.
    """
    ticker = str(case.get('ticker', 'UNKNOWN')).strip()

    # Lazy-load client if not provided
    if client is None:
        from ai_research.llm_client import LLMClient
        client = LLMClient()

    # Determine dry_run: explicit arg > client config
    if dry_run is None:
        dry_run = client.config.dry_run

    if dry_run:
        print(f'  [DRY-RUN] Gate skipped for {ticker} (dry_run=true).')
        return _dry_run_decision(ticker, note='DRY_RUN')

    # Fingerprint cache — skip LLM if same case signal was processed today
    fingerprint = _case_fingerprint(case)
    cache = _load_gate_cache()
    if fingerprint in cache:
        cached = dict(cache[fingerprint])
        cached['note'] = f'CACHE_HIT (fingerprint={fingerprint})'
        print(f'  [CACHE] {ticker}: returning cached decision (fingerprint={fingerprint})')
        return cached

    if not client.available:
        print(f'  [SKIP] AI not available for {ticker}: {client.status_message}')
        return _dry_run_decision(ticker, note=f'AI_UNAVAILABLE: {client.status_message}')

    from ai_research.prompts import build_investment_gate_prompt
    prompt = build_investment_gate_prompt(case)

    try:
        raw = client.complete(prompt)
    except RuntimeError as exc:
        print(f'  [ERROR] LLM call failed for {ticker}: {exc}', file=sys.stderr)
        return {
            **_dry_run_decision(ticker, note=f'LLM_ERROR: {exc}'),
        }
    except Exception as exc:
        print(f'  [ERROR] Unexpected error for {ticker}: {exc}', file=sys.stderr)
        return {
            **_dry_run_decision(ticker, note=f'UNEXPECTED_ERROR: {exc}'),
        }

    decision = _parse_llm_response(raw, ticker)
    decision['fingerprint'] = fingerprint
    cache[fingerprint] = decision
    _save_gate_cache(cache)
    print(
        f'  [GATE] {ticker} → {decision["classification"]} | '
        f'action={decision["research_action"]} | '
        f'confidence={decision["confidence"]:.2f} | '
        f'score={decision["investability_score"]}'
    )
    return decision
