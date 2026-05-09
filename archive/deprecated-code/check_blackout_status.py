#!/usr/bin/env python3
"""
Check fiscal year ends using yfinance to identify stocks NOT in blackout
Checks FULL watchlist from PRODUCTION_SCANNER
"""

import yfinance as yf
from datetime import datetime
import calendar

# Full watchlist from your scanner
FULL_WATCHLIST = [
    # Gene Therapy & Cell Therapy
    'EDIT', 'CRSP', 'NTLA', 'BEAM', 'VERV', 'BLUE', 'FATE', 'SANA', 'CRBU',
    'LYEL', 'BCYC', 'ARCT', 'MRUS', 'CGEM', 'SNGX', 'ABUS', 'QURE', 'RLAY',
    
    # Oncology
    'RARE', 'EYPT', 'CRNX', 'ETNB', 'KURA', 'ARVN', 'IMCR', 'CGEM', 'ARVN', 'ORIC',
    'SDGR', 'TGTX', 'MNOV', 'CGON', 'KYMR', 'RCUS', 'RVPH', 'SMMT', 'DTIL', 'RXRX',
    'CGON', 'MGTX', 'KNSA', 'PRAX', 'ACRV', 'PGEN', 'RLAY', 'ARQT', 'ARVN', 'FHTX',
    
    # Rare Disease
    'IONS', 'SRPT', 'BMRN', 'ALNY', 'VRTX', 'UTHR', 'TBPH', 'MORF', 'AGIO', 'INZY',
    'KRYS', 'IMVT', 'KDNY', 'CGON', 'PTGX', 'REPL', 'VNDA', 'TVTX', 'DTIL', 'APLS',
    
    # Immunology
    'VKTX', 'VIGL', 'BCYC', 'KYMR', 'JANX', 'ALPN', 'ARQT', 'RGNX', 'PRAX', 'CARA',
    'ANIK', 'IMCR', 'CGON', 'RCUS', 'MGTX', 'ARVN', 'KNSA', 'PGEN', 'FHTX', 'CMPS',
    
    # CNS & Neurology  
    'SAGE', 'BIIB', 'ACAD', 'PRAX', 'RGNX', 'ITCI', 'JAZZ', 'AXSM', 'CRNX', 'ALKS',
    'SUPN', 'AVDL', 'DNLI', 'SRPT', 'TGTX', 'IONS', 'ARVN', 'VNDA', 'CARA', 'XENE',
    
    # Recent IPOs & High Growth
    'CARTX', 'RVMD', 'RXRX', 'LYEL', 'CGEM', 'RLAY', 'MORF', 'DTIL', 'GMAB', 'GRPH',
    'IMVT', 'KDNY', 'VNDA', 'BCYC', 'CGON', 'SMMT', 'ETNB', 'ARQT', 'PGEN', 'FHTX',
    
    # Vaccines & Infectious Disease
    'MRNA', 'BNTX', 'NVAX', 'GILD', 'VIR', 'VRTX', 'REGN', 'ABBV', 'GLPG', 'BGNE',
    
    # Cardiovascular
    'MDGL', 'CYTK', 'MRNS', 'ARWR', 'IONS', 'VERV', 'NTLA', 'VERV', 'AKRO', 'KRYS',
    
    # Metabolic & Endocrine
    'VKTX', 'KRYS', 'AKRO', 'MDGL', 'CYTK', 'IONS', 'MORF', 'TVTX', 'REPL', 'VNDA',
    
    # Additional High-Potential
    'IMMP', 'ACLX', 'ALLO', 'CLDX', 'DMAC', 'FULC', 'HUMA', 'KALA', 'MRTX', 'NRIX',
    'OCUL', 'PBYI', 'PLRX', 'QURE', 'RVNC', 'SBBP', 'TARA', 'VERA', 'XNCR', 'YMAB'
]

# Remove duplicates
SYMBOLS = list(set(FULL_WATCHLIST))

def get_fiscal_year_end(ticker):
    """Get fiscal year end month from yfinance - VERIFIED METHOD"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Use the verified field from yfinance
        if 'lastFiscalYearEnd' in info and info['lastFiscalYearEnd']:
            fiscal_timestamp = info['lastFiscalYearEnd']
            fiscal_date = datetime.fromtimestamp(fiscal_timestamp)
            return fiscal_date.month
        
        return None
    except Exception as e:
        return None

def is_in_blackout(fiscal_month, current_month):
    """
    Determine if stock is currently in blackout period
    Blackout = 6 weeks before + 2 days after earnings
    Approximation: Fiscal year end month + next month = blackout
    """
    # Blackout months (current month - 1 through current month + 1)
    # For Dec fiscal year: Nov, Dec, Jan = blackout
    # For Mar fiscal year: Feb, Mar, Apr = blackout
    
    # Calculate blackout range
    blackout_start = (fiscal_month - 1) % 12
    if blackout_start == 0:
        blackout_start = 12
    blackout_end = (fiscal_month + 1) % 12
    if blackout_end == 0:
        blackout_end = 12
    
    # Check if current month is in blackout
    if blackout_start < blackout_end:
        return blackout_start <= current_month <= blackout_end
    else:  # Wraps around year end
        return current_month >= blackout_start or current_month <= blackout_end

print("="*80)
print("FISCAL YEAR END ANALYSIS - BLACKOUT DETECTION")
print("="*80)
print()

current_month = datetime.now().month
current_month_name = calendar.month_name[current_month]

print(f"Current Month: {current_month_name} ({current_month})")
print(f"Total stocks to check: {len(SYMBOLS)}")
print(f"Checking which stocks are NOT in blackout period...")
print()

fiscal_data = []

for i, ticker in enumerate(SYMBOLS, 1):
    print(f"[{i}/{len(SYMBOLS)}] {ticker}...", end=' ', flush=True)
    
    fiscal_month = get_fiscal_year_end(ticker)
    
    if fiscal_month:
        fiscal_month_name = calendar.month_name[fiscal_month]
        in_blackout = is_in_blackout(fiscal_month, current_month)
        
        status = "🔴 BLACKOUT" if in_blackout else "🟢 OPEN"
        
        print(f"Fiscal YE: {fiscal_month_name} - {status}")
        
        fiscal_data.append({
            'ticker': ticker,
            'fiscal_month': fiscal_month,
            'fiscal_month_name': fiscal_month_name,
            'in_blackout': in_blackout
        })
    else:
        print(f"⚠️  Could not determine")

print()
print("="*80)
print("SUMMARY")
print("="*80)

# Group by fiscal year end
from collections import defaultdict
by_fiscal_month = defaultdict(list)

for item in fiscal_data:
    by_fiscal_month[item['fiscal_month_name']].append(item)

print("\nStocks by Fiscal Year End:")
for month_name in sorted(by_fiscal_month.keys(), key=lambda x: list(calendar.month_name).index(x)):
    stocks = by_fiscal_month[month_name]
    print(f"\n{month_name} ({len(stocks)} stocks):")
    for s in stocks:
        status = "🔴 BLACKOUT" if s['in_blackout'] else "🟢 TRADEABLE"
        print(f"  {status} {s['ticker']}")

# Count open vs blackout
open_stocks = [s for s in fiscal_data if not s['in_blackout']]
blackout_stocks = [s for s in fiscal_data if s['in_blackout']]

print(f"\n{'='*80}")
print(f"TRADEABLE NOW (NOT in blackout): {len(open_stocks)} stocks")
if open_stocks:
    print(f"Symbols: {', '.join([s['ticker'] for s in open_stocks])}")

print(f"\nIN BLACKOUT: {len(blackout_stocks)} stocks")
if blackout_stocks:
    print(f"Symbols: {', '.join([s['ticker'] for s in blackout_stocks])}")

print(f"\n{'='*80}")
print("\nRECOMMENDATION:")
if open_stocks:
    print(f"✓ Focus scanner on the {len(open_stocks)} tradeable stocks")
    print(f"✓ These should show insider activity (if any is happening)")
else:
    print("⚠ All stocks appear to be in blackout period")
    print("⚠ Wait until mid-February for better insider data")

print("="*80)
