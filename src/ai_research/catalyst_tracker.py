"""
catalyst_tracker.py — Upcoming catalyst intelligence for MA Scanner universe.

Four data sources (all non-fatal — errors return empty results):
  1. FMP stable/earnings-calendar    — earnings dates (FMP API key required)
  2. SEC EDGAR EFTS full-text search — PDUFA/FDA action dates in 8-K filings (public, no key)
  3. ClinicalTrials.gov API v2       — Phase 3 primary completion dates (public, no key)
  4. Static 2026 conference calendar — ASCO, ASH, ADA, ESMO, ACR, AASLD, SITC, IDWeek

Usage:
  from ai_research.catalyst_tracker import build_catalyst_summary, get_catalyst_context_for_ticker
  summary = build_catalyst_summary(
      universe_tickers={'VRTX', 'MRNA', 'NUVL'},
      company_names={'VRTX': 'Vertex Pharmaceuticals', ...},
      fmp_api_key='...',
      days_ahead=45,
  )
  context = get_catalyst_context_for_ticker('VRTX', summary)  # inject into LLM prompt

Research use only. No investment advice. No trade recommendations.
"""
from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
import urllib.parse
from datetime import datetime, date, timezone, timedelta
from pathlib import Path
from typing import Any

_HERE   = Path(__file__).resolve().parent
_SRCDIR = _HERE.parent
REPO    = _SRCDIR.parent

CATALYST_CACHE_DIR = REPO / 'data' / 'ai_research' / 'catalyst_cache'
FETCH_TIMEOUT = 15

FMP_BASE           = 'https://financialmodelingprep.com'
EDGAR_EFTS_BASE    = 'https://efts.sec.gov/LATEST/search-index'
CLINICALTRIALS_BASE = 'https://clinicaltrials.gov/api/v2/studies'


# ── Priority tiers ────────────────────────────────────────────────────────────

def _priority(days_until: int) -> str:
    if days_until <= 7:   return 'P0_IMMINENT'
    if days_until <= 21:  return 'P1_NEAR_TERM'
    if days_until <= 60:  return 'P2_UPCOMING'
    return 'P3_HORIZON'


# ── 2026 major biotech / pharma conference calendar ───────────────────────────

CONFERENCES_2026 = [
    {
        'name':  'ASCO Annual Meeting 2026',
        'start': '2026-06-01', 'end': '2026-06-04',
        'areas': ['oncology', 'cancer', 'adc', 'tumor', 'immunotherapy', 'checkpoint'],
        'note':  'Largest oncology meeting. Abstract release ~May 16. Major price moves on abstract day.',
    },
    {
        'name':  'ADA Scientific Sessions 2026',
        'start': '2026-06-21', 'end': '2026-06-24',
        'areas': ['diabetes', 'metabolic', 'obesity', 'glp', 'insulin', 'endocrine', 'nash'],
        'note':  'Key for GLP-1/obesity names. Late-breaking trials presented here.',
    },
    {
        'name':  'ESC Congress 2026',
        'start': '2026-08-28', 'end': '2026-09-01',
        'areas': ['cardiovascular', 'heart', 'heart failure', 'atrial fibrillation', 'cardiac'],
        'note':  'Primary cardiology readout venue. Hot outcomes trial data.',
    },
    {
        'name':  'ESMO Congress 2026',
        'start': '2026-09-12', 'end': '2026-09-16',
        'areas': ['oncology', 'cancer', 'immunotherapy', 'targeted therapy', 'adc'],
        'note':  'Second major oncology meeting. European readouts, Phase 3 updates.',
    },
    {
        'name':  'IDWeek 2026',
        'start': '2026-10-15', 'end': '2026-10-19',
        'areas': ['infectious', 'antiviral', 'antibiotic', 'hiv', 'rsv', 'influenza', 'bacterial'],
        'note':  'Key venue for antiviral and antibacterial readouts.',
    },
    {
        'name':  'SITC Annual Meeting 2026',
        'start': '2026-11-06', 'end': '2026-11-08',
        'areas': ['immunotherapy', 'checkpoint', 'car-t', 'car t', 'tumor immunology'],
        'note':  'Immuno-oncology focused. CAR-T and checkpoint combination data.',
    },
    {
        'name':  'ACR Convergence 2026',
        'start': '2026-11-14', 'end': '2026-11-19',
        'areas': ['rheumatology', 'autoimmune', 'lupus', 'ra', 'inflammation', 'jak', 'il-17'],
        'note':  'Key for autoimmune/inflammation pipeline readouts.',
    },
    {
        'name':  'AASLD Liver Meeting 2026',
        'start': '2026-11-15', 'end': '2026-11-18',
        'areas': ['liver', 'hepatology', 'nash', 'nafld', 'cirrhosis', 'fibrosis', 'hepatitis'],
        'note':  'Key NASH/liver disease readouts. High M&A target overlap.',
    },
    {
        'name':  'ASH Annual Meeting 2026',
        'start': '2026-12-05', 'end': '2026-12-08',
        'areas': ['hematology', 'blood', 'leukemia', 'lymphoma', 'myeloma', 'sickle', 'aml', 'cll'],
        'note':  'Largest hematology meeting. Cell therapy and rare blood disease pivotal data.',
    },
]


# ── Utilities ─────────────────────────────────────────────────────────────────

def _http_get_json(url: str, params: dict | None = None, timeout: int = FETCH_TIMEOUT) -> Any:
    try:
        if params:
            url = url + '?' + urllib.parse.urlencode(params)
        ctx = ssl.create_default_context()
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'MA-Scanner/1.0 research@blackstarlightcapital.com'},
        )
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return json.loads(r.read().decode('utf-8', errors='replace'))
    except Exception:
        return None


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    s = s.strip()
    for fmt in ('%Y-%m-%d', '%Y-%m', '%m/%d/%Y', '%B %d, %Y', '%b %d, %Y',
                '%B %Y', '%b %Y'):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    return None


def _days_until(d: date) -> int:
    return (d - _today()).days


def _cache_path(name: str) -> Path:
    CATALYST_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CATALYST_CACHE_DIR / f'{name}_{_today().isoformat()}.json'


def _load_cache(name: str) -> Any:
    p = _cache_path(name)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return None


def _save_cache(name: str, data: Any) -> None:
    try:
        _cache_path(name).write_text(json.dumps(data, indent=2, default=str), encoding='utf-8')
    except Exception:
        pass


def _name_tokens(name: str) -> list[str]:
    """Tokenize company name for fuzzy matching against EDGAR entity names."""
    name = re.sub(r'\b(inc|corp|ltd|llc|plc|sa|nv|ag|therapeutics|pharmaceuticals|biosciences?|biotech|sciences?)\b\.?',
                  '', name, flags=re.IGNORECASE).strip()
    return [t.lower() for t in name.split() if len(t) >= 3]


# ── 1. Earnings calendar ──────────────────────────────────────────────────────

def fetch_earnings_catalysts(
    universe_tickers: set[str],
    fmp_api_key: str,
    days_ahead: int = 45,
) -> list[dict]:
    """Upcoming earnings dates for universe tickers from FMP stable/earnings-calendar."""
    if not fmp_api_key:
        return []

    cached = _load_cache('earnings')
    raw = cached
    if raw is None:
        today_str = _today().isoformat()
        end_str   = (_today() + timedelta(days=days_ahead)).isoformat()
        raw = _http_get_json(
            f'{FMP_BASE}/stable/earnings-calendar',
            params={'apikey': fmp_api_key, 'from': today_str, 'to': end_str, 'limit': 2000},
        ) or []
        _save_cache('earnings', raw)

    universe_upper = {t.upper() for t in universe_tickers}
    catalysts: list[dict] = []
    for item in (raw or []):
        sym = str(item.get('symbol', '')).upper()
        if sym not in universe_upper:
            continue
        d = _parse_date(item.get('date'))
        if not d:
            continue
        du = _days_until(d)
        if du < 0 or du > days_ahead:
            continue
        eps_est = item.get('epsEstimated')
        rev_est = item.get('revenueEstimated')
        desc_parts = ['Earnings report']
        if eps_est is not None:
            desc_parts.append(f'EPS est. ${eps_est:+.2f}')
        if rev_est is not None:
            desc_parts.append(f'Rev est. ${rev_est / 1e6:.0f}M')
        catalysts.append({
            'ticker':        sym,
            'catalyst_type': 'EARNINGS',
            'date':          d.isoformat(),
            'days_until':    du,
            'priority':      _priority(du),
            'description':   ' | '.join(desc_parts),
            'source':        'FMP earnings-calendar',
            'source_url':    '',
            'confidence':    'HIGH',
        })
    return sorted(catalysts, key=lambda x: x['days_until'])


# ── 2. PDUFA / FDA action dates via EDGAR EFTS ───────────────────────────────

def fetch_pdufa_catalysts(
    universe_tickers: set[str],
    company_names: dict[str, str],
    days_ahead: int = 120,
) -> list[dict]:
    """
    Search SEC EDGAR full-text for PDUFA date mentions in recent 8-K filings.
    Public EDGAR EFTS endpoint — no API key needed.
    Matches EDGAR entity names to universe tickers by company name tokens.
    """
    cached = _load_cache('pdufa')
    raw_hits = cached
    if raw_hits is None:
        from_dt = (_today() - timedelta(days=180)).isoformat()
        to_dt   = _today().isoformat()
        params  = {
            'q':         '"PDUFA date" OR "PDUFA action date" OR "prescription drug user fee act date"',
            'forms':     '8-K',
            'dateRange': 'custom',
            'startdt':   from_dt,
            'enddt':     to_dt,
        }
        data = _http_get_json(EDGAR_EFTS_BASE, params=params) or {}
        raw_hits = []
        if isinstance(data, dict):
            raw_hits = data.get('hits', {}).get('hits', []) or []
        _save_cache('pdufa', raw_hits)

    # Build token→ticker reverse map
    token_to_ticker: dict[str, str] = {}
    for ticker, name in (company_names or {}).items():
        if not name:
            continue
        for tok in _name_tokens(name):
            token_to_ticker.setdefault(tok, ticker.upper())

    universe_upper = {t.upper() for t in universe_tickers}
    catalysts: list[dict] = []
    seen: set[str] = set()

    for hit in (raw_hits or []):
        if not isinstance(hit, dict):
            continue
        src         = hit.get('_source', {}) or {}
        entity_name = str(src.get('entity_name', '') or '').lower().strip()
        period      = str(src.get('period_of_report', '') or '')
        form_type   = str(src.get('form_type', '') or '')

        # Match entity name tokens to a universe ticker
        matched_ticker: str | None = None
        entity_tokens = _name_tokens(entity_name)
        for tok in entity_tokens:
            cand = token_to_ticker.get(tok)
            if cand and cand in universe_upper:
                matched_ticker = cand
                break

        if not matched_ticker:
            continue

        key = f'{matched_ticker}_{period}'
        if key in seen:
            continue
        seen.add(key)

        # Use filing period as a proxy date (real PDUFA date requires parsing filing text)
        proxy_dt = _parse_date(period)
        du = _days_until(proxy_dt) if proxy_dt else 0
        if du < -60 or du > days_ahead:
            continue

        catalysts.append({
            'ticker':        matched_ticker,
            'catalyst_type': 'PDUFA',
            'date':          proxy_dt.isoformat() if proxy_dt else 'TBD',
            'days_until':    du,
            'priority':      _priority(max(du, 0)),
            'description':   f'PDUFA/FDA action date mentioned in recent {form_type} filing — read source for exact date',
            'source':        'SEC EDGAR EFTS full-text search',
            'source_url':    (
                f'https://efts.sec.gov/LATEST/search-index?q=%22PDUFA%22'
                f'&forms=8-K&entity={urllib.parse.quote(entity_name)}'
            ),
            'confidence':    'MEDIUM',
            'raw_entity':    entity_name,
            'note':          'Date shown is filing period — read 8-K for exact PDUFA action date.',
        })

    return sorted(catalysts, key=lambda x: x['days_until'])


# ── 3. Phase 3 trial readouts via ClinicalTrials.gov ─────────────────────────

def fetch_trial_catalysts(
    universe_tickers: set[str],
    company_names: dict[str, str],
    days_ahead: int = 180,
) -> list[dict]:
    """
    Find Phase 3 trials with upcoming primary completion dates from ClinicalTrials.gov API v2.
    Matches lead sponsor names to universe tickers.
    Public API — no key needed.
    """
    cached = _load_cache('trials')
    trial_list = cached
    if trial_list is None:
        params = {
            'filter.phase':         'PHASE3',
            'filter.overallStatus': 'ACTIVE_NOT_RECRUITING',
            'query.cond':           (
                'cancer OR rare disease OR autoimmune OR cardiovascular '
                'OR neurological OR metabolic OR hematology OR liver OR infectious'
            ),
            'fields': (
                'NCTId,OfficialTitle,BriefTitle,PrimaryCompletionDate,'
                'LeadSponsorName,OverallStatus,Phase'
            ),
            'pageSize': '200',
            'sort':     '@relevance',
        }
        data = _http_get_json(CLINICALTRIALS_BASE, params=params) or {}
        trial_list = []
        if isinstance(data, dict):
            for study in (data.get('studies') or []):
                proto     = study.get('protocolSection', {}) or {}
                status_m  = proto.get('statusModule', {}) or {}
                id_m      = proto.get('identificationModule', {}) or {}
                sponsor_m = proto.get('sponsorCollaboratorsModule', {}) or {}
                design_m  = proto.get('designModule', {}) or {}
                completion_struct = status_m.get('primaryCompletionDateStruct', {}) or {}
                trial_list.append({
                    'nct_id':     id_m.get('nctId', ''),
                    'title':      id_m.get('briefTitle', '') or id_m.get('officialTitle', ''),
                    'sponsor':    (sponsor_m.get('leadSponsor', {}) or {}).get('name', ''),
                    'status':     status_m.get('overallStatus', ''),
                    'completion': completion_struct.get('date', ''),
                    'phase':      ', '.join(design_m.get('phases', []) or []),
                })
        _save_cache('trials', trial_list)

    # Build token→ticker reverse map
    token_to_ticker: dict[str, str] = {}
    for ticker, name in (company_names or {}).items():
        if not name:
            continue
        for tok in _name_tokens(name):
            token_to_ticker.setdefault(tok, ticker.upper())

    universe_upper = {t.upper() for t in universe_tickers}
    catalysts: list[dict] = []
    seen: set[str] = set()

    for trial in (trial_list or []):
        sponsor   = str(trial.get('sponsor', '') or '').lower().strip()
        nct       = str(trial.get('nct_id', '') or '')
        title     = str(trial.get('title', '') or '')[:140]
        comp_str  = trial.get('completion', '')
        comp_dt   = _parse_date(comp_str)
        if not comp_dt:
            continue
        du = _days_until(comp_dt)
        if du < -30 or du > days_ahead:
            continue

        matched_ticker: str | None = None
        sponsor_tokens = _name_tokens(sponsor)
        for tok in sponsor_tokens:
            cand = token_to_ticker.get(tok)
            if cand and cand in universe_upper:
                matched_ticker = cand
                break

        if not matched_ticker:
            continue

        key = f'{matched_ticker}_{nct}'
        if key in seen:
            continue
        seen.add(key)

        catalysts.append({
            'ticker':        matched_ticker,
            'catalyst_type': 'PHASE3_READOUT',
            'date':          comp_dt.isoformat(),
            'days_until':    du,
            'priority':      _priority(max(du, 0)),
            'description':   f'Phase 3 primary completion — {title}',
            'source':        f'ClinicalTrials.gov {nct}',
            'source_url':    f'https://clinicaltrials.gov/study/{nct}' if nct else '',
            'confidence':    'MEDIUM',
            'nct_id':        nct,
        })

    return sorted(catalysts, key=lambda x: x['days_until'])


# ── 4. Conference calendar ────────────────────────────────────────────────────

def fetch_conference_catalysts(
    universe_tickers: set[str],
    company_profiles: dict[str, str] | None = None,
    days_ahead: int = 180,
) -> list[dict]:
    """
    Return upcoming major biotech/pharma conferences from the static 2026 calendar.
    Optionally match tickers by therapeutic area keyword overlap with company profile text.
    """
    today = _today()
    catalysts: list[dict] = []
    profiles = company_profiles or {}

    for conf in CONFERENCES_2026:
        start_dt = _parse_date(conf['start'])
        if not start_dt:
            continue
        du = _days_until(start_dt)
        if du < -3 or du > days_ahead:
            continue

        areas_lower = [a.lower() for a in conf.get('areas', [])]
        matched: list[str] = []
        for ticker in universe_tickers:
            prof = profiles.get(ticker.upper(), '').lower()
            if prof and any(area in prof for area in areas_lower):
                matched.append(ticker.upper())

        catalysts.append({
            'ticker':           None,
            'catalyst_type':    'CONFERENCE',
            'name':             conf['name'],
            'date':             conf['start'],
            'end_date':         conf.get('end', conf['start']),
            'days_until':       du,
            'priority':         _priority(max(du, 0)),
            'description':      conf.get('note', ''),
            'therapeutic_areas': conf.get('areas', []),
            'matched_tickers':  matched,
            'source':           'static 2026 conference calendar',
            'source_url':       '',
            'confidence':       'HIGH',
        })

    return sorted(catalysts, key=lambda x: x['days_until'])


# ── Main summary builder ──────────────────────────────────────────────────────

def build_catalyst_summary(
    universe_tickers: set[str],
    company_names: dict[str, str] | None = None,
    company_profiles: dict[str, str] | None = None,
    fmp_api_key: str = '',
    days_ahead: int = 45,
) -> dict:
    """
    Unified catalyst summary for the scanner universe.

    Args:
        universe_tickers:  Set of ticker symbols to monitor.
        company_names:     ticker → company name (for EDGAR / ClinicalTrials matching).
        company_profiles:  ticker → business description text (for conference matching).
        fmp_api_key:       FMP API key (earnings calendar only; other sources are public).
        days_ahead:        Primary look-ahead window in days.

    Returns:
        {
            'generated_at': str,
            'days_ahead': int,
            'catalysts': list[dict],      # per-ticker events sorted by days_until
            'by_ticker': dict,            # ticker → [catalysts]
            'conferences': list[dict],    # upcoming conferences (not ticker-specific)
            'stats': dict,
        }
    """
    tickers  = {t.upper() for t in (universe_tickers or [])}
    _names   = company_names or {}
    _profs   = company_profiles or {}

    earnings = fetch_earnings_catalysts(tickers, fmp_api_key, days_ahead=days_ahead)
    pdufa    = fetch_pdufa_catalysts(tickers, _names, days_ahead=days_ahead + 60)
    trials   = fetch_trial_catalysts(tickers, _names, days_ahead=days_ahead + 90)
    confs    = fetch_conference_catalysts(tickers, _profs, days_ahead=days_ahead + 120)

    ticker_cats = earnings + pdufa + trials
    ticker_cats.sort(key=lambda x: (x['days_until'], x['ticker'] or ''))

    by_ticker: dict[str, list] = {}
    for cat in ticker_cats:
        t = cat.get('ticker') or ''
        if t:
            by_ticker.setdefault(t, []).append(cat)

    stats = {
        'total_ticker_catalysts': len(ticker_cats),
        'earnings_count':         len(earnings),
        'pdufa_count':            len(pdufa),
        'trial_count':            len(trials),
        'conference_count':       len(confs),
        'tickers_with_catalysts': len(by_ticker),
        'imminent_p0':   sum(1 for c in ticker_cats if c['priority'] == 'P0_IMMINENT'),
        'near_term_p1':  sum(1 for c in ticker_cats if c['priority'] == 'P1_NEAR_TERM'),
    }

    return {
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        'days_ahead':   days_ahead,
        'catalysts':    ticker_cats,
        'by_ticker':    by_ticker,
        'conferences':  confs,
        'stats':        stats,
    }


# ── Per-case prompt context helper ────────────────────────────────────────────

def get_catalyst_context_for_ticker(
    ticker: str,
    catalyst_summary: dict | None,
) -> str:
    """
    Return a compact catalyst context string for injection into per-case LLM prompts.
    Includes any upcoming earnings, PDUFA, or Phase 3 readout dates for the ticker.
    """
    if not catalyst_summary:
        return ''
    by_ticker = catalyst_summary.get('by_ticker', {})
    cats = by_ticker.get(ticker.upper(), [])
    if not cats:
        return ''

    lines = [f'UPCOMING CATALYSTS FOR {ticker.upper()}:']
    for c in cats[:4]:
        ctype = c.get('catalyst_type', '')
        du    = c.get('days_until', '?')
        dt    = c.get('date', '')
        desc  = c.get('description', '')
        conf  = c.get('confidence', '')
        lines.append(f'  [{ctype}] {dt} ({du} days) [{conf}] — {desc}')

    lines += [
        '',
        'CATALYST ANALYSIS REQUIRED:',
        '  - Does this upcoming event materially change the urgency of this case?',
        '  - A PDUFA within 30 days for an active strategic process = P0 priority.',
        '  - Earnings within 14 days with open WATCH case = check for guidance signals.',
        '  - Phase 3 readout = potential catalyst for M&A interest (positive or negative).',
    ]
    return '\n'.join(lines)
