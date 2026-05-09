#!/usr/bin/env python3
"""
DEBUG: Why isn't FOLD showing up with insider data?
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

print("="*70)
print("DEBUGGING: FOLD INSIDER DATA IN SCANNER")
print("="*70)
print()

ticker = 'FOLD'
stock = yf.Ticker(ticker)

# Get insider transactions
insider_txns = stock.insider_transactions

if insider_txns is None or insider_txns.empty:
    print("✗ NO INSIDER DATA FROM YFINANCE")
    print("This is the problem - yfinance returns empty")
else:
    print(f"✓ Found {len(insider_txns)} transactions")
    
    # Filter to last 30 days
    cutoff_date = datetime.now() - timedelta(days=30)
    
    if 'Start Date' in insider_txns.columns:
        print(f"\n✓ Has 'Start Date' column")
        insider_txns['Start Date'] = pd.to_datetime(insider_txns['Start Date'])
        recent_txns = insider_txns[insider_txns['Start Date'] >= cutoff_date]
        
        print(f"✓ {len(recent_txns)} transactions in last 30 days")
        
        if recent_txns.empty:
            print("\n✗ ALL TRANSACTIONS ARE OLDER THAN 30 DAYS")
            print("\nMost recent transaction:")
            print(insider_txns.head(1))
        else:
            print("\n✓ Recent transactions found:")
            print(recent_txns[['Shares', 'Value', 'Insider', 'Position', 'Start Date']].head())
            
            # Check for C-level
            c_level_titles = ['chief executive', 'ceo', 'chief financial', 'cfo', 'president', 'chairman']
            
            for idx, row in recent_txns.iterrows():
                position = str(row.get('Position', '')).lower()
                is_c_level = any(title in position for title in c_level_titles)
                
                if is_c_level:
                    print(f"\n✓ FOUND C-LEVEL:")
                    print(f"  Insider: {row.get('Insider')}")
                    print(f"  Position: {row.get('Position')}")
                    print(f"  Value: ${row.get('Value'):,.0f}")
                    print(f"  Date: {row.get('Start Date')}")
    else:
        print("\n✗ NO 'Start Date' column")
        print("Available columns:", insider_txns.columns.tolist())

print()
print("="*70)
print("CONCLUSION:")
print("="*70)

if insider_txns is None or insider_txns.empty:
    print("\nProblem: yfinance returns NO insider data")
    print("Possible reasons:")
    print("  - FOLD was delisted after acquisition")
    print("  - yfinance doesn't have historical insider data after acquisition")
    print("  - Need to exclude acquired companies")
else:
    print("\nData exists but may be filtered out by date range")
    print("Solution: Increase lookback window for acquired companies")
