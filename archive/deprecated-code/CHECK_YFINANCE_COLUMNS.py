#!/usr/bin/env python3
"""
Check ALL columns in yfinance insider transactions
We need to see if it includes insider names and titles
"""

import yfinance as yf
import pandas as pd

print("="*70)
print("YFINANCE INSIDER DATA - COMPLETE ANALYSIS")
print("="*70)
print()

stock = yf.Ticker('FOLD')
insider_txns = stock.insider_transactions

if insider_txns is not None and not insider_txns.empty:
    print(f"✓ Found {len(insider_txns)} transactions")
    print()
    
    print("AVAILABLE COLUMNS:")
    print("-" * 70)
    for col in insider_txns.columns:
        print(f"  - {col}")
    
    print()
    print("="*70)
    print("FULL DATA (first 5 transactions):")
    print("="*70)
    print()
    
    # Show all columns for first 5 rows
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', 50)
    
    print(insider_txns.head(5).to_string())
    
    print()
    print("="*70)
    print("LOOKING FOR CEO SALE (77,926 shares on Dec 15-17):")
    print("="*70)
    
    # Filter for the CEO transaction
    ceo_sale = insider_txns[
        (insider_txns['Shares'] == 77926) | 
        (insider_txns['Value'] > 800000) & (insider_txns['Value'] < 900000)
    ]
    
    if not ceo_sale.empty:
        print("\n✓ FOUND IT!")
        print()
        print(ceo_sale.to_string())
        
        print()
        print("="*70)
        print("KEY FIELDS:")
        print("="*70)
        
        for col in ceo_sale.columns:
            val = ceo_sale.iloc[0][col]
            print(f"{col}: {val}")
        
        # Check if we have insider name/title
        if 'Insider Trading' in ceo_sale.columns:
            print("\n✓ Has 'Insider Trading' column")
        if 'Text' in ceo_sale.columns:
            print("✓ Has 'Text' column (might contain name)")
        if 'URL' in ceo_sale.columns:
            print("✓ Has 'URL' column (link to SEC filing)")
    else:
        print("\n✗ Could not find specific CEO transaction")
        print("Showing transactions around that value:")
        high_value = insider_txns[insider_txns['Value'] > 500000]
        print(high_value.head(10))
    
else:
    print("✗ No insider transaction data")

print()
print("="*70)
print("CONCLUSION:")
print("="*70)

if 'Text' in insider_txns.columns or 'Insider Trading' in insider_txns.columns:
    print("\n✅ yfinance DOES include insider info!")
    print("We can extract names/titles from the available columns")
else:
    print("\n⚠️  yfinance might not have detailed insider info")
    print("We may need to cross-reference with SEC using the URL")
