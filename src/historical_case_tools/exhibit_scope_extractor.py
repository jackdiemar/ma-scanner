#!/usr/bin/env python3
"""
exhibit_scope_extractor.py

Given SEC filing text or an exhibit document, identifies ROFR / ROFN / ROFO /
option rights and classifies their scope for Historical Process Intelligence
rofr_scope field population.

Scope taxonomy:
  WHOLE_COMPANY     — rights apply to acquisition of entire company
  ASSET_SPECIFIC    — rights apply to a specific identified asset/program bundle
  PROGRAM_SPECIFIC  — rights apply to a single named compound or program
  TERRITORY_SPECIFIC — rights apply only within a defined geography
  UNKNOWN           — insufficient text evidence to classify

Output:
  scope_type, rights_holder, affected_asset, company_wide_or_asset_specific,
  excerpt, confidence (0–1), calibration_warning

Usage:
    python3 exhibit_scope_extractor.py --file /path/to/exhibit.txt
    python3 exhibit_scope_extractor.py --text "...right of first refusal..."
    python3 exhibit_scope_extractor.py --edgar-url https://www.sec.gov/Archives/...
    python3 exhibit_scope_extractor.py --file exhibit.txt --output json
"""

import argparse
import json
import re
import sys
import urllib.request
from typing import Optional


# ─── Rights type patterns ─────────────────────────────────────────────────────

RIGHTS_PATTERNS: dict[str, list[str]] = {
    'ROFR': [
        r'right\s+of\s+first\s+refusal',
        r'first[\s-]refusal\s+right',
        r'refusal\s+right\s+to\s+(?:purchase|acquire)',
        r'right\s+to\s+match\s+(?:any\s+)?(?:offer|bid)',
    ],
    'ROFN': [
        r'right\s+of\s+first\s+negotiation',
        r'first[\s-]negotiation\s+right',
        r'exclusive\s+(?:right|period)\s+to\s+negotiate',
        r'negotiate\s+(?:exclusively|in\s+good\s+faith)\s+(?:with|for)',
    ],
    'ROFO': [
        r'right\s+of\s+first\s+offer',
        r'first[\s-]offer\s+right',
        r'right\s+to\s+make\s+(?:the\s+)?first\s+offer',
    ],
    'OPTION_TO_ACQUIRE': [
        r'option\s+to\s+(?:acquire|purchase|buy)(?:\s+(?:all|the))?',
        r'exclusive\s+option\s+(?:to\s+)?(?:acquire|purchase)',
        r'option\s+(?:agreement\s+)?to\s+acquire\s+(?:the\s+)?(?:company|business)',
    ],
    'CHANGE_OF_CONTROL_CONSENT': [
        r'change\s+of\s+control\s+(?:consent|approval|notification\s+right)',
        r'consent\s+(?:to|for|prior\s+to)\s+(?:any\s+)?change\s+of\s+control',
        r'change\s+in\s+control\s+(?:provision|restriction|covenant)',
    ],
    'CO_DEVELOPMENT_OPTION': [
        r'option\s+to\s+co[\s-]develop',
        r'co[\s-]promotion\s+option',
        r'opt[\s-]in\s+(?:right|option)',
        r'option\s+to\s+participate\s+in',
    ],
}

# ─── Scope indicator patterns ─────────────────────────────────────────────────

WHOLE_COMPANY_PATTERNS: list[str] = [
    r'entire\s+(?:company|enterprise|business|entity)',
    r'all\s+(?:of\s+the\s+)?(?:outstanding\s+)?(?:shares|equity|capital\s+stock|assets)',
    r'acquisition\s+of\s+(?:the\s+)?(?:company|licensor|licensee)',
    r'merger\s+(?:or\s+)?(?:acquisition\s+)?of\s+(?:the\s+)?(?:company|party)',
    r'acquir(?:e|ing|ed)\s+(?:the\s+)?(?:company|licensor|licensee|party)',
    r'change\s+of\s+control\s+of\s+(?:the\s+)?(?:company|licensor|licensee)',
    r'purchase\s+of\s+all\s+(?:or\s+substantially\s+all)',
    r'tender\s+offer\s+for\s+(?:all\s+(?:or\s+substantially\s+all))',
    r'acquisition\s+of\s+(?:a\s+)?(?:majority|controlling)\s+(?:interest|stake)',
    r'(?:any\s+)?(?:proposed\s+)?(?:change\s+in|transfer\s+of)\s+control',
    r'consolidation\s+with\s+(?:the\s+)?(?:company|licensor)',
    r'sale\s+of\s+(?:all\s+or\s+substantially\s+all)',
]

ASSET_SPECIFIC_PATTERNS: list[str] = [
    r'collaboration\s+(?:product|compound|molecule|asset|program)',
    r'licensed\s+(?:product|compound|molecule|asset)',
    r'(?:the\s+)?(?:specified|applicable|relevant|defined)\s+(?:product|compound|asset)',
    r'with\s+respect\s+to\s+(?:the\s+)?(?:licensed|collaboration|specified)\s+(?:product|compound|asset)',
    r'relating\s+to\s+(?:the\s+)?(?:collaboration|licensed|specified)\s+(?:product|compound)',
    r'(?:only\s+)?applies\s+to\s+(?:the\s+)?(?:licensed|collaboration)',
    r'(?:with\s+respect\s+to|solely\s+for|limited\s+to)\s+(?:the\s+)?(?:program|asset)',
    r'(?:the\s+)?(?:co-developed|joint)\s+(?:product|program|compound)',
]

PROGRAM_NAME_PATTERNS: list[str] = [
    r'\b[A-Z]{2,5}-\d{3,5}(?:/[A-Z])?(?:\b|$)',   # e.g. HARP-3521, MK-7110, GS-5734
    r'\b(?:rusfertide|bomedemstat|momelotinib|eptinezumab|lenabasum|fostamatinib)\b',
    r'(?:the\s+)?(?:compound|molecule|product)\s+(?:known\s+as\s+)?[A-Z]{2,5}-\d{3,5}',
    r'(?:program|compound)\s+referred\s+to\s+as\s+[A-Z]',
]

TERRITORY_PATTERNS: list[str] = [
    r'(?:the\s+)?(?:licensed\s+)?territory',
    r'(?:geographic(?:al)?\s+)?(?:territory|region|area|market)',
    r'outside\s+(?:the\s+)?(?:United\s+States|U\.S\.|North\s+America)',
    r'within\s+(?:the\s+)?(?:United\s+States|U\.S\.|European\s+Union|Asia(?:-Pacific)?|China)',
    r'field\s+of\s+use\s+(?:in|within|limited\s+to)',
    r'exclusive\s+(?:license|rights)\s+in\s+(?:the\s+)?(?:territory|territories)',
    r'jurisdiction(?:s)?\s+(?:listed|set\s+forth)',
]

# ─── Counterparty extraction ──────────────────────────────────────────────────

COUNTERPARTY_PATTERNS: list[str] = [
    r'(?:granted?\s+to|held\s+by|exercisable\s+by|in\s+favor\s+of)\s+([A-Z][A-Za-z\s,\.&]+(?:Inc\.|LLC|Corp\.|Ltd\.|plc|GmbH|AG|SA|NV|BV|AB|AS|Oy)?)',
    r'([A-Z][A-Za-z\s,\.&]+(?:Inc\.|LLC|Corp\.|Ltd\.|plc|GmbH|AG|SA)?)\s+shall\s+have\s+(?:a\s+)?(?:right|option)',
    r'([A-Z][A-Za-z\s,\.&]+(?:Inc\.|LLC|Corp\.|Ltd\.|plc|GmbH|AG|SA)?)\s+(?:has|have|will\s+have)\s+(?:an?\s+)?(?:right|option)',
    r'(?:grant(?:ing|ed)?|provid(?:ing|ed)?)\s+([A-Z][A-Za-z\s,\.&]+(?:Inc\.|LLC|Corp\.|Ltd\.|plc|GmbH|AG|SA)?)\s+(?:an?\s+)?(?:right|option|ROFR|ROFN)',
]

# ─── Core extraction functions ────────────────────────────────────────────────

def _search(text: str, patterns: list[str], flags: int = re.IGNORECASE) -> list[dict]:
    """Find all matches for a list of regex patterns. Returns list of match info."""
    results = []
    for pat in patterns:
        for m in re.finditer(pat, text, flags):
            results.append({
                'pattern': pat,
                'match':   m.group(0),
                'start':   m.start(),
            })
    return results


def _context(text: str, position: int, window: int = 250) -> str:
    """Return surrounding context around a text position."""
    start = max(0, position - window // 2)
    end   = min(len(text), position + window // 2)
    return text[start:end].strip()


def _detect_rights(text: str) -> dict[str, list[dict]]:
    """Find all rights types present in the text."""
    found: dict[str, list[dict]] = {}
    for rights_type, patterns in RIGHTS_PATTERNS.items():
        hits = _search(text, patterns)
        if hits:
            found[rights_type] = hits
    return found


def _score_scope(text: str) -> dict[str, int]:
    """Count pattern matches for each scope type."""
    return {
        'WHOLE_COMPANY':     len(_search(text, WHOLE_COMPANY_PATTERNS)),
        'ASSET_SPECIFIC':    len(_search(text, ASSET_SPECIFIC_PATTERNS)),
        'PROGRAM_SPECIFIC':  len(_search(text, PROGRAM_NAME_PATTERNS)),
        'TERRITORY_SPECIFIC': len(_search(text, TERRITORY_PATTERNS)),
    }


def _classify_scope(scores: dict[str, int]) -> tuple[str, float]:
    """
    Classify scope from pattern hit counts.
    Returns (scope_type, confidence 0.0–1.0).
    Confidence is intentionally conservative — manual review is expected.
    """
    total = sum(scores.values())
    if total == 0:
        return 'UNKNOWN', 0.0

    wc = scores['WHOLE_COMPANY']
    as_ = scores['ASSET_SPECIFIC']
    ps = scores['PROGRAM_SPECIFIC']
    ts = scores['TERRITORY_SPECIFIC']

    # WHOLE_COMPANY needs 2+ hits to be confident (avoid false positives
    # from generic "change of control" boilerplate in many agreements)
    if wc >= 2 and wc > as_ and wc > ps:
        conf = min(0.90, 0.50 + 0.10 * wc)
        return 'WHOLE_COMPANY', round(conf, 2)

    # Named compound = strong PROGRAM_SPECIFIC signal
    if ps >= 1 and ps >= as_:
        conf = min(0.85, 0.45 + 0.15 * ps)
        return 'PROGRAM_SPECIFIC', round(conf, 2)

    if as_ >= 2 and as_ > wc:
        conf = min(0.75, 0.40 + 0.10 * as_)
        return 'ASSET_SPECIFIC', round(conf, 2)

    if ts >= 2 and ts > wc and ts > as_:
        conf = min(0.70, 0.35 + 0.10 * ts)
        return 'TERRITORY_SPECIFIC', round(conf, 2)

    # Single hit — not enough to be confident
    if total == 1:
        max_type = max(scores, key=lambda k: scores[k])
        return max_type, 0.25

    # Mixed signals — report most common but flag low confidence
    max_type = max(scores, key=lambda k: scores[k])
    return max_type, 0.35


def _extract_counterparty(text: str) -> Optional[str]:
    """Extract the named rights holder. Returns first plausible match or None."""
    for pat in COUNTERPARTY_PATTERNS:
        m = re.search(pat, text)
        if m:
            name = m.group(1).strip().rstrip(',.;')
            # Filter obvious noise
            if len(name) > 3 and not name.lower().startswith('the '):
                return name
    return None


def _extract_excerpt(text: str, rights_hits: list[dict], max_chars: int = 400) -> str:
    """Extract verbatim context around the first rights match."""
    if not rights_hits:
        return ''
    first = min(rights_hits, key=lambda h: h['start'])
    return _context(text, first['start'], window=max_chars)[:max_chars]


def _calibration_warning(scope_type: str, confidence: float,
                          rights_types: list[str], scores: dict[str, int]) -> str:
    """Build calibration warning for rofr_scope assignment."""
    warnings = []

    if confidence < 0.5:
        warnings.append(
            f'LOW CONFIDENCE ({confidence:.0%}) — scope classification unreliable; '
            'manual review of full exhibit required before assigning rofr_scope'
        )

    if scope_type == 'UNKNOWN':
        warnings.append(
            'Scope UNKNOWN — no relevant patterns found; '
            'check that correct exhibit section was extracted (look for Article/Section with ROFR/ROFN heading)'
        )

    if 'CHANGE_OF_CONTROL_CONSENT' in rights_types and scope_type != 'WHOLE_COMPANY':
        warnings.append(
            'Change-of-control consent detected alongside non-whole-company scope — '
            'verify whether consent clause applies company-wide despite narrower primary rights'
        )

    if scores['WHOLE_COMPANY'] >= 1 and scores['ASSET_SPECIFIC'] >= 1:
        warnings.append(
            'Mixed whole-company and asset-specific signals — '
            'agreement may have tiered rights; read full clause carefully'
        )

    if not warnings:
        return 'NONE'
    return ' | '.join(warnings)


# ─── Public API ───────────────────────────────────────────────────────────────

def extract_scope(text: str, source_hint: str = '') -> dict:
    """
    Main function: classify ROFR/ROFN scope from exhibit or filing text.

    Args:
        text:        Full text of the agreement section or relevant exhibit
        source_hint: URL or filename for attribution in output

    Returns:
        dict with scope_type, rights_holder, affected_asset,
        company_wide_or_asset_specific, excerpt, confidence, calibration_warning
    """
    if not text or len(text.strip()) < 30:
        return {
            'rights_types_found': [],
            'scope_type': 'UNKNOWN',
            'scope_scores': {},
            'confidence': 0.0,
            'rights_holder': None,
            'affected_asset': None,
            'company_wide_or_asset_specific': 'UNKNOWN',
            'excerpt': '',
            'calibration_warning': 'Text too short or empty — nothing to analyze',
            'source': source_hint,
        }

    # 1. Detect rights types
    rights_found = _detect_rights(text)

    if not rights_found:
        return {
            'rights_types_found': [],
            'scope_type': 'UNKNOWN',
            'scope_scores': {},
            'confidence': 0.0,
            'rights_holder': None,
            'affected_asset': None,
            'company_wide_or_asset_specific': 'UNKNOWN',
            'excerpt': '',
            'calibration_warning': (
                'No ROFR/ROFN/ROFO/option rights language detected in text. '
                'Verify that the correct section/exhibit was provided. '
                'ROFR clauses are typically in a dedicated article or section titled '
                '"Right of First Refusal", "Option", or "Change of Control".'
            ),
            'source': source_hint,
        }

    # 2. Score scope
    scores = _score_scope(text)
    scope_type, confidence = _classify_scope(scores)

    # 3. Counterparty
    rights_holder = _extract_counterparty(text)

    # 4. Excerpt — use first rights match
    all_hits = [h for hits in rights_found.values() for h in hits]
    excerpt = _extract_excerpt(text, all_hits)

    # 5. Affected asset label
    if scope_type == 'PROGRAM_SPECIFIC':
        prog_hits = _search(text, PROGRAM_NAME_PATTERNS)
        affected_asset = prog_hits[0]['match'].strip() if prog_hits else 'VERIFY_REQUIRED'
    elif scope_type == 'WHOLE_COMPANY':
        affected_asset = 'WHOLE_COMPANY'
    elif scope_type == 'TERRITORY_SPECIFIC':
        affected_asset = 'TERRITORY — VERIFY_REQUIRED (read territory definition clause)'
    elif scope_type == 'ASSET_SPECIFIC':
        affected_asset = 'ASSET — VERIFY_REQUIRED (confirm specific asset from agreement)'
    else:
        affected_asset = 'VERIFY_REQUIRED'

    # 6. Company-wide label
    cw_label = (
        'COMPANY_WIDE'   if scope_type == 'WHOLE_COMPANY'
        else 'ASSET_SPECIFIC' if scope_type in ('ASSET_SPECIFIC', 'PROGRAM_SPECIFIC', 'TERRITORY_SPECIFIC')
        else 'UNKNOWN'
    )

    return {
        'rights_types_found':          list(rights_found.keys()),
        'scope_type':                  scope_type,
        'scope_scores':                scores,
        'confidence':                  confidence,
        'rights_holder':               rights_holder,
        'affected_asset':              affected_asset,
        'company_wide_or_asset_specific': cw_label,
        'excerpt':                     excerpt,
        'calibration_warning':         _calibration_warning(
                                           scope_type, confidence,
                                           list(rights_found.keys()), scores
                                       ),
        'source':                      source_hint,
    }


def fetch_and_extract(url: str) -> dict:
    """Fetch text from an EDGAR URL and run extraction. Strips HTML tags."""
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'ma-scanner-research/1.0 jackdiemar@example.com'}
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
        # Strip HTML
        text = re.sub(r'<[^>]+>', ' ', raw)
        text = re.sub(r'\s+', ' ', text)
        return extract_scope(text, source_hint=url)
    except Exception as exc:
        return {
            'rights_types_found': [],
            'scope_type': 'UNKNOWN',
            'confidence': 0.0,
            'rights_holder': None,
            'affected_asset': None,
            'company_wide_or_asset_specific': 'UNKNOWN',
            'excerpt': '',
            'calibration_warning': f'Fetch failed: {exc}',
            'source': url,
        }


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Extract ROFR/ROFN scope from SEC filing exhibit text'
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument('--file',       help='Path to local file containing exhibit text')
    src.add_argument('--text',       help='Inline text string to analyze')
    src.add_argument('--edgar-url',  help='Direct EDGAR filing/exhibit URL to fetch and analyze')
    parser.add_argument('--output',  choices=['text', 'json'], default='text')
    args = parser.parse_args()

    if args.file:
        with open(args.file, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
        result = extract_scope(text, source_hint=args.file)
    elif args.text:
        result = extract_scope(args.text, source_hint='<inline>')
    else:
        result = fetch_and_extract(args.edgar_url)

    if args.output == 'json':
        print(json.dumps(result, indent=2))
        return

    # Text output
    print('\nExhibit Scope Extractor')
    print('=' * 50)
    print(f'Rights Found:   {", ".join(result.get("rights_types_found", [])) or "NONE"}')
    print(f'Scope Type:     {result["scope_type"]}')
    print(f'Confidence:     {result.get("confidence", 0):.0%}')
    print(f'Rights Holder:  {result.get("rights_holder") or "NOT DETECTED"}')
    print(f'Affected Asset: {result.get("affected_asset") or "UNKNOWN"}')
    print(f'Company-Wide:   {result.get("company_wide_or_asset_specific", "UNKNOWN")}')

    scores = result.get('scope_scores', {})
    if scores:
        print(f'\nScope Scores:')
        for k, v in scores.items():
            bar = '█' * v
            print(f'  {k:<20} {v:>2}  {bar}')

    if result.get('excerpt'):
        print(f'\nExcerpt (verbatim, ~{len(result["excerpt"])} chars):')
        print(f'  "{result["excerpt"][:400]}"')

    print(f'\nCalibration Warning:')
    for line in result.get('calibration_warning', 'NONE').split(' | '):
        print(f'  ⚠  {line}')

    print(f'\nSource: {result.get("source", "")}')


if __name__ == '__main__':
    main()
