#!/usr/bin/env python3
"""
Test KALA market cap calculation
"""

import yfinance as yf

ticker = yf.Ticker("KALA")
info = ticker.info

print("="*70)
print("KALA MARKET CAP DEBUG")
print("="*70)

print(f"\nWhat yfinance gives us:")
print(f"  marketCap: ${info.get('marketCap', 0):,}")
print(f"  sharesOutstanding: {info.get('sharesOutstanding', 0):,}")
print(f"  floatShares: {info.get('floatShares', 0):,}")

# Get current price
hist = ticker.history(period='1d')
if not hist.empty:
    current_price = hist['Close'].iloc[-1]
    print(f"  currentPrice: ${current_price:.2f}")
    
    # Calculate market cap
    shares = info.get('sharesOutstanding', 0)
    if shares > 0:
        calculated_mcap = current_price * shares
        print(f"\nCalculated Market Cap:")
        print(f"  ${current_price:.2f} × {shares:,} shares = ${calculated_mcap:,.0f}")
        print(f"  = ${calculated_mcap/1_000_000:.2f}M")
        
        # Compare
        reported_mcap = info.get('marketCap', 0)
        print(f"\nComparison:")
        print(f"  Reported (yfinance): ${reported_mcap/1_000_000:.2f}M")
        print(f"  Calculated: ${calculated_mcap/1_000_000:.2f}M")
        print(f"  Difference: ${(calculated_mcap - reported_mcap)/1_000_000:.2f}M")
        
        if abs(calculated_mcap - reported_mcap) > 1_000_000:
            print(f"\n⚠️  BIG DISCREPANCY - yfinance data is WRONG")
            print(f"  Use calculated: ${calculated_mcap/1_000_000:.2f}M")
    else:
        print("\n✗ No shares outstanding data")
else:
    print("\n✗ No price data")

print("\n" + "="*70)
print("RECOMMENDATION")
print("="*70)
print("\nScanner should:")
print("  1. Get current price from hist['Close']")
print("  2. Get sharesOutstanding from info")
print("  3. Calculate: mcap = price * shares")
print("  4. Only use info['marketCap'] as fallback")
