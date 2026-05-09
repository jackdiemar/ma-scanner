#!/usr/bin/env python3
"""
Test FMP Quote API Endpoint
Verifies the /stable/quote endpoint works and returns market cap
"""

import requests
import json
from secure_config import get_env

FMP_API_KEY = get_env("FMP_API_KEY")

def test_quote(symbol):
    """Test FMP quote endpoint"""
    url = "https://financialmodelingprep.com/stable/quote"
    params = {
        'symbol': symbol,
        'apikey': FMP_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data and len(data) > 0:
            quote = data[0]
            print(f"\n✅ {symbol} Quote Data:")
            print(f"  Price: ${quote.get('price', 'N/A')}")
            print(f"  Market Cap: ${quote.get('marketCap', 0):,.0f}")
            print(f"  Volume: {quote.get('volume', 0):,}")
            print(f"  Change: {quote.get('change', 0):.2f} ({quote.get('changePercentage', 0):.2f}%)")
            print(f"  Day Range: ${quote.get('dayLow', 'N/A')} - ${quote.get('dayHigh', 'N/A')}")
            
            # Calculate market cap in millions for comparison
            mcap_M = quote.get('marketCap', 0) / 1_000_000
            print(f"  Market Cap (M): ${mcap_M:.1f}M")
            
            return True
        else:
            print(f"❌ No data returned for {symbol}")
            return False
            
    except Exception as e:
        print(f"❌ Error fetching {symbol}: {e}")
        return False

if __name__ == '__main__':
    print("="*60)
    print("FMP QUOTE API TEST")
    print("="*60)
    
    # Test with a few biotech stocks from the scanner
    test_symbols = ['QURE', 'KALA', 'APLS', 'AAPL']  # Mix of biotech + Apple for reference
    
    success_count = 0
    for symbol in test_symbols:
        if test_quote(symbol):
            success_count += 1
    
    print("\n" + "="*60)
    print(f"RESULTS: {success_count}/{len(test_symbols)} successful")
    print("="*60)
    
    if success_count == len(test_symbols):
        print("✅ FMP Quote API is working perfectly!")
        print("   V10.4 scanner will use this for market cap & price")
    else:
        print("⚠️  Some quotes failed - scanner will fallback to yfinance")
