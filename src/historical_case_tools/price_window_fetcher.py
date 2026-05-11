#!/usr/bin/env python3
"""
price_window_fetcher.py

Fetch adjusted close price windows for historical case verification.

Usage:
    python src/historical_case_tools/price_window_fetcher.py --ticker IMGO --observation-date 2022-11-21
    python src/historical_case_tools/price_window_fetcher.py --batch data/historical_cases/cases_partial.csv
    python src/historical_case_tools/price_window_fetcher.py --batch data/historical_cases/cases_seed.csv --tickers IMGO GNCA SRRA FLXN
"""

import argparse
import csv
import shutil
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

try:
    import yfinance as yf
except ImportError:  # pragma: no cover
    yf = None


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / 'data' / 'historical_cases' / 'price_windows.csv'

PRICE_WINDOW_FIELDS = [
    'case_id',
    'ticker',
    'observation_date',
    'price_before_signal',
    'price_30d_after',
    'price_90d_after',
    'max_drawdown_after_signal',
    'price_source',
    'adjusted_close_used',
    'data_start_date',
    'data_end_date',
    'missing_data_flag',
    'fallback_needed',
    'notes',
    'created_at',
]

MISSING_VALUES = {'', 'VERIFY_REQUIRED', 'UNKNOWN', 'NA', 'N/A', 'NULL', 'None'}


@dataclass
class CaseInput:
    case_id: str
    ticker: str
    observation_date: str


def parse_date(value: str, field_name: str) -> date:
    if value in MISSING_VALUES:
        raise ValueError(f'missing {field_name}')
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError as exc:
        raise ValueError(f'invalid {field_name}: {value} (expected YYYY-MM-DD)') from exc


def created_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def format_price(value: Optional[float]) -> str:
    if value is None:
        return ''
    return f'{value:.4f}'


def format_bool(value: bool) -> str:
    return 'TRUE' if value else 'FALSE'


def fallback_for_ticker(ticker: str) -> str:
    delisted_sources = {
        'IMGO': 'manual delisted ticker source; Stooq historical price lookup; Nasdaq historical data',
        'GNCA': 'manual delisted ticker source; Stooq historical price lookup; Nasdaq historical data',
        'SRRA': 'manual delisted ticker source; Stooq historical price lookup; Nasdaq historical data',
        'FLXN': 'manual delisted ticker source; Stooq historical price lookup; Nasdaq historical data',
    }
    return delisted_sources.get(
        ticker.upper(),
        'Stooq historical price lookup; Nasdaq historical data; Alpha Vantage',
    )


def read_cases(path: Path, tickers: Optional[set[str]] = None) -> list[CaseInput]:
    cases: list[CaseInput] = []
    with path.open(newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = (row.get('ticker') or '').strip().upper()
            if not ticker:
                continue
            if tickers and ticker not in tickers:
                continue
            cases.append(CaseInput(
                case_id=(row.get('case_id') or '').strip(),
                ticker=ticker,
                observation_date=(row.get('observation_date') or '').strip(),
            ))
    return cases


def existing_keys(path: Path) -> set[tuple[str, str, str]]:
    if not path.exists():
        return set()
    with path.open(newline='') as f:
        reader = csv.DictReader(f)
        return {
            (
                (row.get('case_id') or '').strip(),
                (row.get('ticker') or '').strip().upper(),
                (row.get('observation_date') or '').strip(),
            )
            for row in reader
        }


def backup_existing(path: Path) -> Optional[Path]:
    if not path.exists():
        return None
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = path.with_name(f'{path.stem}.backup_{stamp}{path.suffix}')
    shutil.copy2(path, backup_path)
    return backup_path


def fetch_adjusted_history(ticker: str, obs_date: date):
    if yf is None:
        raise RuntimeError('yfinance is not installed')

    start = obs_date - timedelta(days=14)
    end = obs_date + timedelta(days=100)
    data = yf.download(
        ticker,
        start=start.isoformat(),
        end=(end + timedelta(days=8)).isoformat(),
        auto_adjust=False,
        progress=False,
        actions=False,
        threads=False,
    )
    if data is None or data.empty:
        return [], False

    adjusted_close_used = False
    if getattr(data.columns, 'nlevels', 1) > 1:
        level_values = [set(data.columns.get_level_values(i)) for i in range(data.columns.nlevels)]
        for price_column in ('Adj Close', 'Close'):
            for level, values in enumerate(level_values):
                if price_column in values:
                    data = data.xs(price_column, axis=1, level=level)
                    adjusted_close_used = price_column == 'Adj Close'
                    break
            else:
                continue
            break
        else:
            return [], False
        series = data[ticker] if ticker in data.columns else data.iloc[:, 0]
    else:
        column = 'Adj Close' if 'Adj Close' in data.columns else 'Close'
        adjusted_close_used = column == 'Adj Close'
        series = data[column]

    rows = []
    for idx, value in series.dropna().items():
        trade_date = idx.date() if hasattr(idx, 'date') else idx
        rows.append((trade_date, float(value)))
    return rows, adjusted_close_used


def price_on_or_after(rows: list[tuple[date, float]], target: date) -> Optional[tuple[date, float]]:
    for trade_date, price in rows:
        if trade_date >= target:
            return trade_date, price
    return None


def price_before(rows: list[tuple[date, float]], target: date) -> Optional[tuple[date, float]]:
    prior = [row for row in rows if row[0] < target]
    return prior[-1] if prior else None


def build_missing_row(case: CaseInput, fallback_needed: str, notes: str) -> dict[str, str]:
    return {
        'case_id': case.case_id,
        'ticker': case.ticker,
        'observation_date': case.observation_date,
        'price_before_signal': '',
        'price_30d_after': '',
        'price_90d_after': '',
        'max_drawdown_after_signal': '',
        'price_source': 'yfinance',
        'adjusted_close_used': 'FALSE',
        'data_start_date': '',
        'data_end_date': '',
        'missing_data_flag': 'TRUE',
        'fallback_needed': fallback_needed,
        'notes': notes,
        'created_at': created_at(),
    }


def calculate_price_window(case: CaseInput) -> dict[str, str]:
    try:
        obs_date = parse_date(case.observation_date, 'observation_date')
    except ValueError as exc:
        return build_missing_row(
            case,
            'EDGAR observation_date confirmation required before price lookup',
            str(exc),
        )

    try:
        rows, adjusted_close_used = fetch_adjusted_history(case.ticker, obs_date)
    except Exception as exc:
        return build_missing_row(
            case,
            fallback_for_ticker(case.ticker),
            f'yfinance error: {exc}',
        )

    if not rows:
        return build_missing_row(
            case,
            fallback_for_ticker(case.ticker),
            'yfinance returned no adjusted close history for requested window',
        )

    before = price_before(rows, obs_date)
    after_30 = price_on_or_after(rows, obs_date + timedelta(days=30))
    after_90 = price_on_or_after(rows, obs_date + timedelta(days=90))

    if before is None or after_30 is None or after_90 is None:
        return build_missing_row(
            case,
            fallback_for_ticker(case.ticker),
            'yfinance returned incomplete adjusted close history for required window',
        )

    drawdown_end = after_90[0]
    window_rows = [row for row in rows if obs_date <= row[0] <= drawdown_end]
    if not window_rows:
        return build_missing_row(
            case,
            fallback_for_ticker(case.ticker),
            'no trading days found between observation_date and 90-day window end',
        )

    min_after = min(price for _, price in window_rows)
    max_drawdown = (min_after - before[1]) / before[1]

    return {
        'case_id': case.case_id,
        'ticker': case.ticker,
        'observation_date': case.observation_date,
        'price_before_signal': format_price(before[1]),
        'price_30d_after': format_price(after_30[1]),
        'price_90d_after': format_price(after_90[1]),
        'max_drawdown_after_signal': format_price(max_drawdown),
        'price_source': 'yfinance',
        'adjusted_close_used': format_bool(adjusted_close_used),
        'data_start_date': rows[0][0].isoformat(),
        'data_end_date': rows[-1][0].isoformat(),
        'missing_data_flag': 'FALSE',
        'fallback_needed': '',
        'notes': (
            f'before={before[0].isoformat()}; '
            f'30d={after_30[0].isoformat()}; '
            f'90d={after_90[0].isoformat()}'
        ),
        'created_at': created_at(),
    }


def write_rows(path: Path, rows: list[dict[str, str]], dry_run: bool) -> Optional[Path]:
    if dry_run or not rows:
        return None

    path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = backup_existing(path)
    write_header = not path.exists()
    with path.open('a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=PRICE_WINDOW_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)
    return backup_path


def print_rows(rows: list[dict[str, str]]) -> None:
    writer = csv.DictWriter(sys.stdout, fieldnames=PRICE_WINDOW_FIELDS)
    writer.writeheader()
    writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Fetch adjusted close price windows for historical case verification.'
    )
    parser.add_argument('--ticker', help='Ticker for one-off lookup')
    parser.add_argument('--observation-date', help='Observation date for one-off lookup, YYYY-MM-DD')
    parser.add_argument('--case-id', default='', help='case_id for one-off lookup')
    parser.add_argument('--batch', help='CSV file with case_id, ticker, observation_date columns')
    parser.add_argument('--tickers', nargs='*', help='Optional ticker filter for --batch')
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT), help='Output CSV path')
    parser.add_argument('--dry-run', action='store_true', help='Print rows without writing CSV')
    args = parser.parse_args()

    output_path = Path(args.output)
    ticker_filter = {t.upper() for t in args.tickers} if args.tickers else None

    if args.batch:
        cases = read_cases(Path(args.batch), ticker_filter)
    elif args.ticker:
        cases = [CaseInput(
            case_id=args.case_id,
            ticker=args.ticker.upper(),
            observation_date=args.observation_date or '',
        )]
    else:
        parser.error('provide --ticker and --observation-date, or --batch')

    if not cases:
        print('No matching cases found.', file=sys.stderr)
        return 1

    keys = existing_keys(output_path)
    duplicate_keys = [
        (case.case_id, case.ticker, case.observation_date)
        for case in cases
        if (case.case_id, case.ticker, case.observation_date) in keys
    ]
    if duplicate_keys and not args.dry_run:
        print('Refusing to append duplicate price window rows:', file=sys.stderr)
        for key in duplicate_keys:
            print(f'  case_id={key[0]} ticker={key[1]} observation_date={key[2]}', file=sys.stderr)
        print('Run with --dry-run to inspect, or manually back up/edit price_windows.csv.', file=sys.stderr)
        return 1

    rows = [calculate_price_window(case) for case in cases]
    print_rows(rows)

    backup_path = write_rows(output_path, rows, args.dry_run)
    if args.dry_run:
        print(f'DRY RUN: no rows written to {output_path}', file=sys.stderr)
    else:
        if backup_path:
            print(f'Backup written: {backup_path}', file=sys.stderr)
        print(f'Rows appended: {len(rows)} -> {output_path}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
