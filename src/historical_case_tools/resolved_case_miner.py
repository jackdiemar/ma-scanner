#!/usr/bin/env python3
"""
resolved_case_miner.py

Generate CANDIDATE rows for resolved historical biotech/pharma special situations.

This starts from historical outcomes, then writes backward-looking process-signal
search tasks. It does not verify evidence, assign PARTIAL/VERIFIED status, or
mark anything calibration-ready.

Usage:
    python src/historical_case_tools/resolved_case_miner.py
"""

import argparse
import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / 'data' / 'historical_cases'
DEFAULT_COLLECTION_TARGETS = HISTORICAL_DIR / 'collection_targets.csv'
DEFAULT_CASES_SEED = HISTORICAL_DIR / 'cases_seed.csv'
DEFAULT_OUTPUT = HISTORICAL_DIR / 'resolved_case_candidates.csv'
DEFAULT_REPORT = HISTORICAL_DIR / 'resolved_case_mining_report.md'
DEFAULT_SOURCE_QUERIES = HISTORICAL_DIR / 'historical_source_queries.md'

YEARS = range(2015, 2025)

OUTPUT_FIELDS = [
    'candidate_id',
    'ticker',
    'company_name',
    'likely_outcome_type',
    'likely_outcome_year',
    'outcome_source_hint',
    'outcome_edgar_query',
    'prior_process_signal_query',
    'prior_13d_query',
    'prior_rofr_exhibit_query',
    'proxy_or_s4_query',
    'verification_status',
    'priority',
    'reason_for_inclusion',
    'notes',
]

OUTCOME_TYPES = [
    'ACQUIRED',
    'FAILED_REVIEW',
    'WIND_DOWN',
    'BANKRUPTCY',
    'REVERSE_MERGER',
    'ASSET_SALE',
    'CAPITAL_RAISE_AFTER_PROCESS',
    'ACTIVIST_NO_DEAL',
]

OUTCOME_FORMS = {
    'ACQUIRED': '8-K,DEFM14A,DEF 14A,SC TO-T,SC TO-I',
    'FAILED_REVIEW': '8-K',
    'WIND_DOWN': '8-K',
    'BANKRUPTCY': '8-K',
    'REVERSE_MERGER': '8-K,S-4,424B3,DEFM14A,DEF 14A',
    'ASSET_SALE': '8-K',
    'CAPITAL_RAISE_AFTER_PROCESS': '8-K,S-3,424B5',
    'ACTIVIST_NO_DEAL': 'SC 13D,SC 13D/A,DEF 14A',
}

OUTCOME_PHRASES = {
    'ACQUIRED': '"agreement and plan of merger" "per share"',
    'FAILED_REVIEW': '"strategic alternatives" "restructuring"',
    'WIND_DOWN': '"wind down" "cease operations"',
    'BANKRUPTCY': '"chapter 11" "voluntary petition"',
    'REVERSE_MERGER': '"reverse merger" "strategic alternatives"',
    'ASSET_SALE': '"asset purchase agreement" "sale"',
    'CAPITAL_RAISE_AFTER_PROCESS': '"strategic alternatives" "registered direct offering"',
    'ACTIVIST_NO_DEAL': '"Item 4" "strategic alternatives"',
}

VERIFYING_FILING = {
    'ACQUIRED': '8-K merger agreement, then DEFM14A/DEF 14A background section',
    'FAILED_REVIEW': '8-K strategic alternatives announcement and later 8-K/10-Q outcome',
    'WIND_DOWN': '8-K wind-down, liquidation, or dissolution announcement',
    'BANKRUPTCY': '8-K bankruptcy/restructuring announcement',
    'REVERSE_MERGER': '8-K reverse merger agreement, S-4/424B3, or proxy',
    'ASSET_SALE': '8-K asset purchase agreement',
    'CAPITAL_RAISE_AFTER_PROCESS': '8-K/S-3/424B5 financing after prior process 8-K',
    'ACTIVIST_NO_DEAL': 'SC 13D/13D/A Item 4 plus later no-deal outcome check',
}

CATEGORY_MAP = {
    'COMPLETED_DEAL': 'ACQUIRED',
    'FAILED_REVIEW': 'FAILED_REVIEW',
    'BANKRUPTCY': 'BANKRUPTCY',
    'WIND_DOWN': 'WIND_DOWN',
    'ASSET_SALE': 'ASSET_SALE',
    'CAPITAL_RAISE': 'CAPITAL_RAISE_AFTER_PROCESS',
    'CAPITAL_RAISE_AFTER_PROCESS': 'CAPITAL_RAISE_AFTER_PROCESS',
    'ACTIVIST_NO_DEAL': 'ACTIVIST_NO_DEAL',
    'REVERSE_MERGER': 'REVERSE_MERGER',
    'MERGER_EQUALS': 'REVERSE_MERGER',
}

SKIP_TERMS = {
    'exclude',
    'wrong sector',
    'not applicable',
    'not pure biotech',
    'spac vehicle',
    'hagerty',
    'no wrong sector',
}


@dataclass(frozen=True)
class Seed:
    ticker: str
    company_name: str
    likely_outcome_type: str
    likely_outcome_year: str
    outcome_source_hint: str
    priority: str
    notes: str = ''


CURATED_SEEDS = [
    Seed('NPSP', 'NPS Pharmaceuticals, Inc.', 'ACQUIRED', '2015', 'Shire acquisition; verify with 8-K merger agreement and proxy.', 'HIGH'),
    Seed('PCYC', 'Pharmacyclics, Inc.', 'ACQUIRED', '2015', 'AbbVie acquisition; verify with 8-K merger agreement and proxy.', 'HIGH'),
    Seed('ZSPH', 'ZS Pharma, Inc.', 'ACQUIRED', '2015', 'AstraZeneca acquisition; verify with 8-K merger agreement and proxy.', 'HIGH'),
    Seed('RLYP', 'Relypsa, Inc.', 'ACQUIRED', '2016', 'Galenica acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('ANAC', 'Anacor Pharmaceuticals, Inc.', 'ACQUIRED', '2016', 'Pfizer acquisition; verify with 8-K merger agreement and proxy.', 'HIGH'),
    Seed('MDVN', 'Medivation, Inc.', 'ACQUIRED', '2016', 'Pfizer acquisition; verify with 8-K merger agreement and proxy.', 'HIGH'),
    Seed('CPXX', 'Celator Pharmaceuticals, Inc.', 'ACQUIRED', '2016', 'Jazz acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('TBRA', 'Tobira Therapeutics, Inc.', 'ACQUIRED', '2016', 'Allergan acquisition; verify with 8-K merger agreement and proxy.', 'HIGH'),
    Seed('VTAE', 'Vitae Pharmaceuticals, Inc.', 'ACQUIRED', '2016', 'Allergan acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('ARIA', 'ARIAD Pharmaceuticals, Inc.', 'ACQUIRED', '2017', 'Takeda acquisition; verify with 8-K merger agreement and proxy.', 'HIGH'),
    Seed('CLCD', 'CoLucid Pharmaceuticals, Inc.', 'ACQUIRED', '2017', 'Eli Lilly acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('DMTX', 'Dimension Therapeutics, Inc.', 'ACQUIRED', '2017', 'Ultragenyx acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('KITE', 'Kite Pharma, Inc.', 'ACQUIRED', '2017', 'Gilead acquisition; verify with 8-K merger agreement and proxy background.', 'HIGH'),
    Seed('JUNO', 'Juno Therapeutics, Inc.', 'ACQUIRED', '2018', 'Celgene acquisition; verify with 8-K merger agreement and DEFM14A.', 'HIGH'),
    Seed('AVXS', 'AveXis, Inc.', 'ACQUIRED', '2018', 'Novartis acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('BIVV', 'Bioverativ Inc.', 'ACQUIRED', '2018', 'Sanofi acquisition; verify with 8-K merger agreement and proxy.', 'HIGH'),
    Seed('CASC', 'Cascadian Therapeutics, Inc.', 'ACQUIRED', '2018', 'Seattle Genetics acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('LOXO', 'Loxo Oncology, Inc.', 'ACQUIRED', '2019', 'Eli Lilly acquisition; verify with 8-K merger agreement and proxy.', 'HIGH'),
    Seed('ARRY', 'Array BioPharma Inc.', 'ACQUIRED', '2019', 'Pfizer acquisition; verify with 8-K merger agreement and proxy.', 'HIGH'),
    Seed('RXDX', 'Ignyta, Inc.', 'ACQUIRED', '2018', 'Roche acquisition; verify with merger 8-K and tender offer filings.', 'HIGH'),
    Seed('TSRO', 'TESARO, Inc.', 'ACQUIRED', '2019', 'GSK acquisition; verify with merger 8-K and proxy/tender filings.', 'HIGH'),
    Seed('NITE', 'Nightstar Therapeutics plc', 'ACQUIRED', '2019', 'Biogen acquisition; verify with 8-K/6-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('CMTA', 'Clementia Pharmaceuticals Inc.', 'ACQUIRED', '2019', 'Ipsen acquisition; verify with 8-K/6-K transaction filings.', 'HIGH'),
    Seed('BOLD', 'Audentes Therapeutics, Inc.', 'ACQUIRED', '2020', 'Astellas acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('FTSV', 'Forty Seven, Inc.', 'ACQUIRED', '2020', 'Gilead acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('PRNB', 'Principia Biopharma Inc.', 'ACQUIRED', '2020', 'Sanofi acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('PRVL', 'Prevail Therapeutics Inc.', 'ACQUIRED', '2020', 'Eli Lilly acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('MNTA', 'Momenta Pharmaceuticals, Inc.', 'ACQUIRED', '2020', 'Johnson & Johnson acquisition; verify with 8-K merger agreement and proxy.', 'HIGH'),
    Seed('FOLD', 'Amicus Therapeutics, Inc.', 'FAILED_REVIEW', '2022', 'Strategic review / transaction-rumor false-positive candidate; verify before use.', 'LOW'),
    Seed('ONCE', 'Spark Therapeutics, Inc.', 'ACQUIRED', '2019', 'Roche acquisition; verify with merger 8-K and proxy.', 'HIGH'),
    Seed('MYOK', 'MyoKardia, Inc.', 'ACQUIRED', '2020', 'Bristol Myers Squibb acquisition; verify with 8-K and proxy/tender filings.', 'HIGH'),
    Seed('FPRX', 'Five Prime Therapeutics, Inc.', 'ACQUIRED', '2021', 'Amgen acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('VIE', 'Viela Bio, Inc.', 'ACQUIRED', '2021', 'Horizon acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('GWPH', 'GW Pharmaceuticals plc', 'ACQUIRED', '2021', 'Jazz acquisition; verify with 8-K/6-K transaction filings and proxy/circular.', 'HIGH'),
    Seed('FMTX', 'Forma Therapeutics Holdings, Inc.', 'ACQUIRED', '2022', 'Novo Nordisk acquisition; verify with 8-K merger agreement.', 'HIGH'),
    Seed('SYNH', 'Syneos Health, Inc.', 'ACQUIRED', '2023', 'Life-sciences services acquisition; adjacent target, verify industry fit.', 'LOW'),
    Seed('RARE', 'Ultragenyx Pharmaceutical Inc.', 'ACTIVIST_NO_DEAL', '2023', 'Potential 13D/no-deal calibration target; verify Item 4 and later outcome.', 'LOW'),
    Seed('TPTX', 'Turning Point Therapeutics, Inc.', 'ACQUIRED', '2022', 'Bristol Myers Squibb acquisition; verify with 8-K merger agreement.', 'HIGH'),
    Seed('CCXI', 'ChemoCentryx, Inc.', 'ACQUIRED', '2022', 'Amgen acquisition; verify with merger 8-K and proxy.', 'HIGH'),
    Seed('GBT', 'Global Blood Therapeutics, Inc.', 'ACQUIRED', '2022', 'Pfizer acquisition; verify with 8-K merger agreement and proxy.', 'HIGH'),
    Seed('BHVN', 'Biohaven Pharmaceutical Holding Company Ltd.', 'ACQUIRED', '2022', 'Pfizer acquisition of Biohaven operating company; verify with 8-K/6-K and proxy filings.', 'HIGH'),
    Seed('CINC', 'CinCor Pharma, Inc.', 'ACQUIRED', '2023', 'AstraZeneca acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('RXDX', 'Prometheus Biosciences, Inc.', 'ACQUIRED', '2023', 'Merck acquisition; verify with 8-K merger agreement and proxy/tender filings.', 'HIGH'),
    Seed('BLU', 'BELLUS Health Inc.', 'ACQUIRED', '2023', 'GSK acquisition; verify with 8-K/6-K transaction filings and circular.', 'HIGH'),
    Seed('DICE', 'DICE Therapeutics, Inc.', 'ACQUIRED', '2023', 'Eli Lilly acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('ISEE', 'IVERIC bio, Inc.', 'ACQUIRED', '2023', 'Astellas acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('HZNP', 'Horizon Therapeutics plc', 'ACQUIRED', '2023', 'Amgen acquisition; verify with transaction filings and proxy/circular.', 'MED'),
    Seed('SGEN', 'Seagen Inc.', 'ACQUIRED', '2023', 'Pfizer acquisition; verify with 8-K merger agreement and proxy.', 'MED'),
    Seed('MOR', 'MorphoSys AG', 'ACQUIRED', '2024', 'Novartis acquisition; foreign issuer, verify available 6-K/transaction filings.', 'MED'),
    Seed('KNSA', 'Kiniksa Pharmaceuticals, Ltd.', 'ASSET_SALE', '2021', 'Program or asset transaction candidate; verify with 8-K asset sale agreement.', 'LOW'),
    Seed('DRNA', 'Dicerna Pharmaceuticals, Inc.', 'ACQUIRED', '2021', 'Novo Nordisk acquisition; verify with merger 8-K and proxy.', 'HIGH'),
    Seed('XLRN', 'Acceleron Pharma Inc.', 'ACQUIRED', '2021', 'Merck acquisition; verify with merger 8-K and tender offer filings.', 'HIGH'),
    Seed('TRIL', 'Trillium Therapeutics Inc.', 'ACQUIRED', '2021', 'Pfizer acquisition; verify with transaction 8-K/6-K and circular.', 'HIGH'),
    Seed('BPMC', 'Blueprint Medicines Corporation', 'ASSET_SALE', '2024', 'Asset sale / royalty transaction candidate; verify with 8-K agreement before use.', 'LOW'),
    Seed('MRTX', 'Mirati Therapeutics, Inc.', 'ACQUIRED', '2024', 'Bristol Myers Squibb acquisition; verify with merger 8-K and proxy.', 'HIGH'),
    Seed('CERE', 'Cerevel Therapeutics Holdings, Inc.', 'ACQUIRED', '2024', 'AbbVie acquisition; verify with merger 8-K and proxy.', 'HIGH'),
    Seed('KRTX', 'Karuna Therapeutics, Inc.', 'ACQUIRED', '2024', 'Bristol Myers Squibb acquisition; verify with 8-K merger agreement and proxy.', 'HIGH'),
    Seed('ALPN', 'Alpine Immune Sciences, Inc.', 'ACQUIRED', '2024', 'Vertex acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('CBAY', 'CymaBay Therapeutics, Inc.', 'ACQUIRED', '2024', 'Gilead acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('FUSN', 'Fusion Pharmaceuticals Inc.', 'ACQUIRED', '2024', 'AstraZeneca acquisition; verify with 8-K/6-K transaction filings.', 'HIGH'),
    Seed('AMAM', 'Ambrx Biopharma Inc.', 'ACQUIRED', '2024', 'Johnson & Johnson acquisition; verify with 8-K/6-K transaction filings.', 'HIGH'),
    Seed('DCPH', 'Deciphera Pharmaceuticals, Inc.', 'ACQUIRED', '2024', 'ONO acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('MORF', 'Morphic Holding, Inc.', 'ACQUIRED', '2024', 'Eli Lilly acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('LBPH', 'Longboard Pharmaceuticals, Inc.', 'ACQUIRED', '2024', 'Lundbeck acquisition; verify with 8-K merger agreement and tender offer filings.', 'HIGH'),
    Seed('IMTX', 'Immatics N.V.', 'CAPITAL_RAISE_AFTER_PROCESS', '2023', 'Financing-after-process candidate only; verify prior process signal first.', 'LOW'),
    Seed('AKBA', 'Akebia Therapeutics, Inc.', 'ACTIVIST_NO_DEAL', '2022', 'Potential 13D/no-deal candidate; verify Item 4 and no-deal window.', 'LOW'),
    Seed('RUBY', 'Rubius Therapeutics, Inc.', 'WIND_DOWN', '2023', 'Wind-down/restructuring candidate after pipeline failure; verify with 8-K.', 'HIGH'),
    Seed('LCTX', 'Lineage Cell Therapeutics, Inc.', 'ACTIVIST_NO_DEAL', '2021', 'Potential activist/no-deal target; verify SC 13D Item 4.', 'LOW'),
    Seed('ZYNE', 'Zynerba Pharmaceuticals, Inc.', 'ACQUIRED', '2023', 'Harmony acquisition; verify with 8-K merger agreement and tender filings.', 'HIGH'),
    Seed('TCRR', 'TCR2 Therapeutics Inc.', 'REVERSE_MERGER', '2023', 'Allogene/TCR2 stock transaction candidate; verify structure with S-4/proxy.', 'MED'),
    Seed('RETA', 'Reata Pharmaceuticals, Inc.', 'ACQUIRED', '2023', 'Biogen acquisition; verify with 8-K merger agreement and proxy.', 'HIGH'),
    Seed('SLGC', 'SomaLogic, Inc.', 'REVERSE_MERGER', '2024', 'Life-sciences diagnostics merger candidate; verify with proxy/S-4.', 'LOW'),
    Seed('RCUS', 'Arcus Biosciences, Inc.', 'ACTIVIST_NO_DEAL', '2023', 'Potential 13D/no-deal or collaboration-rights target; verify filings first.', 'LOW'),
    Seed('PRQR', 'ProQR Therapeutics N.V.', 'FAILED_REVIEW', '2022', 'Strategic pivot / failed process candidate; verify 6-K/8-K language.', 'LOW'),
    Seed('QURE', 'uniQure N.V.', 'FAILED_REVIEW', '2023', 'Strategic review / asset sale candidate; verify 6-K/8-K process language.', 'LOW'),
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def edgar_query(company: str, ticker: str, phrase: str, forms: str, year: str) -> str:
    start, end = year_bounds(year)
    query = f'{ticker} "{company}" {phrase}'
    return (
        'https://efts.sec.gov/LATEST/search-index?'
        f'q={quote_plus(query)}&forms={quote_plus(forms)}&dateRange=custom&startdt={start}&enddt={end}'
    )


def year_bounds(year: str) -> tuple[str, str]:
    clean = ''.join(ch for ch in str(year) if ch.isdigit())
    if len(clean) >= 4:
        event_year = int(clean[:4])
        return f'{event_year}-01-01', f'{event_year}-12-31'
    return '2015-01-01', '2024-12-31'


def prior_bounds(year: str) -> str:
    clean = ''.join(ch for ch in str(year) if ch.isdigit())
    if len(clean) < 4:
        return '2015-01-01', '2024-12-31'
    event_year = int(clean[:4])
    start_year = max(2015, event_year - 3)
    return f'{start_year}-01-01', f'{event_year}-12-31'


def prior_query(company: str, ticker: str, phrase: str, forms: str, year: str) -> str:
    start, end = prior_bounds(year)
    query = f'{ticker} "{company}" {phrase}'
    return (
        'https://efts.sec.gov/LATEST/search-index?'
        f'q={quote_plus(query)}&forms={quote_plus(forms)}&dateRange=custom&startdt={start}&enddt={end}'
    )


def normalize_outcome(category: str, source_hint: str) -> str:
    category = (category or '').strip().upper()
    source_hint_l = (source_hint or '').lower()
    if category == 'BANKRUPTCY' and any(term in source_hint_l for term in ('wind-down', 'wind down', 'liquidation')):
        return 'WIND_DOWN'
    return CATEGORY_MAP.get(category, '')


def normalize_priority(priority: str, outcome_type: str, source_hint: str) -> str:
    priority = (priority or '').strip().upper()
    hint = (source_hint or '').lower()
    if any(term in hint for term in ('possible', 'check current status', 'as of 2025', 'governance')):
        return 'LOW'
    if priority in {'HIGH', 'MED', 'LOW'}:
        return priority
    if outcome_type in {'ACQUIRED', 'WIND_DOWN', 'BANKRUPTCY'}:
        return 'HIGH'
    if outcome_type in {'REVERSE_MERGER', 'ASSET_SALE', 'FAILED_REVIEW'}:
        return 'MED'
    return 'LOW'


def should_skip(row: dict[str, str]) -> bool:
    text = ' '.join(str(value) for value in row.values()).lower()
    if any(term in text for term in SKIP_TERMS):
        return True
    ticker = (row.get('ticker') or '').strip()
    company = (row.get('company') or row.get('company_name') or '').strip()
    return not ticker or not company


def seed_from_collection(row: dict[str, str]) -> Seed | None:
    if should_skip(row):
        return None
    outcome = normalize_outcome(row.get('category', ''), row.get('source_hint', ''))
    if outcome not in OUTCOME_TYPES:
        return None
    return Seed(
        ticker=(row.get('ticker') or '').strip().upper(),
        company_name=(row.get('company') or '').strip(),
        likely_outcome_type=outcome,
        likely_outcome_year=(row.get('likely_event_year') or '').strip(),
        outcome_source_hint=(row.get('source_hint') or '').strip(),
        priority=normalize_priority(row.get('priority', ''), outcome, row.get('source_hint', '')),
        notes=(row.get('notes') or '').strip(),
    )


def seed_from_cases(row: dict[str, str]) -> Seed | None:
    if should_skip({'ticker': row.get('ticker'), 'company': row.get('company'), 'notes': row.get('notes', '')}):
        return None
    outcome = (row.get('corporate_outcome') or row.get('outcome') or '').strip().upper()
    if outcome == 'ACQUIRED':
        mapped = 'ACQUIRED'
    elif outcome in {'BANKRUPT', 'BANKRUPTCY'}:
        mapped = 'BANKRUPTCY'
    elif outcome in {'WIND_DOWN', 'LIQUIDATION'}:
        mapped = 'WIND_DOWN'
    elif 'REVERSE' in (row.get('notes') or '').upper():
        mapped = 'REVERSE_MERGER'
    elif outcome in {'REVIEW_ABANDONED', 'ONGOING'}:
        mapped = 'FAILED_REVIEW'
    else:
        mapped = normalize_outcome(row.get('event_type', ''), row.get('notes', ''))
    if mapped not in OUTCOME_TYPES:
        return None

    year = (row.get('deal_date') or row.get('source_filing_date') or row.get('observation_date') or '').strip()[:4]
    return Seed(
        ticker=(row.get('ticker') or '').strip().upper(),
        company_name=(row.get('company') or '').strip(),
        likely_outcome_type=mapped,
        likely_outcome_year=year,
        outcome_source_hint=f"Existing cases_seed row {row.get('case_id', '')}; verify from primary filing before use.",
        priority='HIGH' if row.get('data_quality') == 'PARTIAL' else 'MED',
        notes='Imported from cases_seed.csv as CANDIDATE only; do not promote without source_evidence and price windows.',
    )


def build_row(seed: Seed, index: int) -> dict[str, str]:
    outcome_phrase = OUTCOME_PHRASES[seed.likely_outcome_type]
    outcome_forms = OUTCOME_FORMS[seed.likely_outcome_type]
    candidate_id = f'RHC-{index:04d}-{seed.likely_outcome_type}-{seed.ticker}'
    return {
        'candidate_id': candidate_id,
        'ticker': seed.ticker,
        'company_name': seed.company_name,
        'likely_outcome_type': seed.likely_outcome_type,
        'likely_outcome_year': seed.likely_outcome_year,
        'outcome_source_hint': seed.outcome_source_hint,
        'outcome_edgar_query': edgar_query(seed.company_name, seed.ticker, outcome_phrase, outcome_forms, seed.likely_outcome_year),
        'prior_process_signal_query': prior_query(seed.company_name, seed.ticker, '"strategic alternatives" OR "financial advisor" OR "review of strategic alternatives"', '8-K,10-Q,10-K', seed.likely_outcome_year),
        'prior_13d_query': prior_query(seed.company_name, seed.ticker, '"Item 4" OR "strategic alternatives" OR "maximize shareholder value"', 'SC 13D,SC 13D/A', seed.likely_outcome_year),
        'prior_rofr_exhibit_query': prior_query(seed.company_name, seed.ticker, '"right of first refusal" OR "right of first negotiation" OR "option to acquire"', '8-K,10-K,10-Q,EX-10', seed.likely_outcome_year),
        'proxy_or_s4_query': prior_query(seed.company_name, seed.ticker, '"background of the merger" OR "reasons for the merger" OR "S-4"', 'DEFM14A,DEF 14A,S-4,424B3', seed.likely_outcome_year),
        'verification_status': 'CANDIDATE',
        'priority': seed.priority,
        'reason_for_inclusion': f'Likely resolved historical {seed.likely_outcome_type} outcome; mine backward for pre-outcome process signals.',
        'notes': seed.notes or 'Candidate only. Outcome and prior process evidence require primary-source verification.',
    }


def collect_seeds(collection_targets: Path, cases_seed: Path) -> list[Seed]:
    seeds: list[Seed] = []
    for row in read_csv(collection_targets):
        seed = seed_from_collection(row)
        if seed:
            seeds.append(seed)
    for row in read_csv(cases_seed):
        seed = seed_from_cases(row)
        if seed:
            seeds.append(seed)
    seeds.extend(CURATED_SEEDS)

    deduped: dict[tuple[str, str, str], Seed] = {}
    priority_rank = {'HIGH': 3, 'MED': 2, 'LOW': 1}
    for seed in seeds:
        key = (seed.ticker, seed.likely_outcome_type, seed.likely_outcome_year)
        existing = deduped.get(key)
        if existing is None or priority_rank.get(seed.priority, 0) > priority_rank.get(existing.priority, 0):
            deduped[key] = seed
    return sorted(
        deduped.values(),
        key=lambda seed: (
            {'HIGH': 0, 'MED': 1, 'LOW': 2}.get(seed.priority, 9),
            OUTCOME_TYPES.index(seed.likely_outcome_type),
            seed.likely_outcome_year,
            seed.ticker,
        ),
    )


def markdown_table(rows: list[dict[str, str]], columns: list[str]) -> str:
    lines = [
        '| ' + ' | '.join(columns) + ' |',
        '| ' + ' | '.join(['---'] * len(columns)) + ' |',
    ]
    for row in rows:
        lines.append('| ' + ' | '.join(str(row.get(column, '')) for column in columns) + ' |')
    return '\n'.join(lines)


def write_report(path: Path, rows: list[dict[str, str]]) -> None:
    by_outcome = Counter(row['likely_outcome_type'] for row in rows)
    by_priority = Counter(row['priority'] for row in rows)
    top_rows = [
        {
            'candidate_id': row['candidate_id'],
            'ticker': row['ticker'],
            'company_name': row['company_name'],
            'outcome': row['likely_outcome_type'],
            'year': row['likely_outcome_year'],
            'priority': row['priority'],
            'verifying_filing': VERIFYING_FILING[row['likely_outcome_type']],
        }
        for row in rows[:50]
    ]
    count_rows = [{'likely_outcome_type': outcome, 'count': by_outcome.get(outcome, 0)} for outcome in OUTCOME_TYPES]
    priority_rows = [{'priority': priority, 'count': by_priority.get(priority, 0)} for priority in ['HIGH', 'MED', 'LOW']]

    path.write_text(f"""# Resolved Historical Case Mining Report

Generated by `src/historical_case_tools/resolved_case_miner.py`.

## Summary

- Resolved historical candidates generated: {len(rows)}
- All rows are `CANDIDATE`.
- No rows are `PARTIAL`, `VERIFIED`, or `CALIBRATION_ELIGIBLE`.
- Rows are outcome-first: the first verification step is the resolved outcome filing, then prior process-signal search.
- 13F is not used as process evidence. It is secondary only for holder identification in later activist research.

## Count By Outcome Type

{markdown_table(count_rows, ['likely_outcome_type', 'count'])}

## Count By Priority

{markdown_table(priority_rows, ['priority', 'count'])}

## Top 50 Historical Cases To Verify First

{markdown_table(top_rows, ['candidate_id', 'ticker', 'company_name', 'outcome', 'year', 'priority', 'verifying_filing'])}

## Blockers

- Direct EDGAR/API mining was not run in this offline pass, so source hints are not verification evidence.
- Some rows imported from prior local target lists include approximate years or secondary-source hints and must be confirmed against primary filings.
- Failed-review and activist-no-deal outcomes require a later no-deal outcome check before they can become usable calibration cases.
- Price windows are still required after outcome and signal dates are verified.
""")


def write_source_queries(path: Path) -> None:
    lines = [
        '# Historical Source Queries',
        '',
        'Generated by `src/historical_case_tools/resolved_case_miner.py`.',
        '',
        'Use these as deterministic EDGAR query templates. They identify resolved outcome filings first, then the miner creates company-specific backward searches.',
        '',
    ]
    for year in YEARS:
        lines.append(f'## {year}')
        lines.append('')
        for outcome in OUTCOME_TYPES:
            start, end = f'{year}-01-01', f'{year}-12-31'
            url = (
                'https://efts.sec.gov/LATEST/search-index?'
                f'q={quote_plus(OUTCOME_PHRASES[outcome])}&forms={quote_plus(OUTCOME_FORMS[outcome])}'
                f'&dateRange=custom&startdt={start}&enddt={end}'
            )
            lines.append(f'- `{outcome}`: {url}')
        lines.append('')
    path.write_text('\n'.join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate resolved historical case candidates.')
    parser.add_argument('--collection-targets', default=str(DEFAULT_COLLECTION_TARGETS))
    parser.add_argument('--cases-seed', default=str(DEFAULT_CASES_SEED))
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT))
    parser.add_argument('--report-output', default=str(DEFAULT_REPORT))
    parser.add_argument('--source-queries-output', default=str(DEFAULT_SOURCE_QUERIES))
    args = parser.parse_args()

    seeds = collect_seeds(Path(args.collection_targets), Path(args.cases_seed))
    rows = [build_row(seed, index) for index, seed in enumerate(seeds, start=1)]

    write_csv(Path(args.output), rows, OUTPUT_FIELDS)
    write_report(Path(args.report_output), rows)
    write_source_queries(Path(args.source_queries_output))

    counts = Counter(row['likely_outcome_type'] for row in rows)
    print(f'Generated {len(rows)} resolved historical candidates -> {args.output}')
    for outcome in OUTCOME_TYPES:
        print(f'{outcome}: {counts.get(outcome, 0)}')
    print(f'Report -> {args.report_output}')
    print(f'Source queries -> {args.source_queries_output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
