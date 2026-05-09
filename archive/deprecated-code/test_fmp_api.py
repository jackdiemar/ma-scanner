"""
FMP API Endpoint Tester
Tests all endpoints to see what data is actually returned
"""

import requests
import json
from secure_config import get_env

API_KEY = get_env("FMP_API_KEY")
BASE_URL = "https://financialmodelingprep.com/stable"

# Test ticker
TICKER = "AGNC"

print("=" * 80)
print("FMP API ENDPOINT DIAGNOSTIC TEST")
print("=" * 80)

# Test 1: Quote
print(f"\n1. Testing Quote Endpoint:")
print(f"   URL: {BASE_URL}/quote?symbol={TICKER}")
try:
    response = requests.get(f"{BASE_URL}/quote?symbol={TICKER}", timeout=10)
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Response: {json.dumps(data, indent=2)[:500]}")
    print(f"   Keys available: {list(data[0].keys()) if data and len(data) > 0 else 'No data'}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 2: Ratios TTM
print(f"\n2. Testing Ratios TTM Endpoint:")
print(f"   URL: {BASE_URL}/ratios-ttm?symbol={TICKER}")
try:
    response = requests.get(f"{BASE_URL}/ratios-ttm?symbol={TICKER}", timeout=10)
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Response: {json.dumps(data, indent=2)[:500]}")
    if data and len(data) > 0:
        print(f"   Keys available: {list(data[0].keys())}")
        # Check for book value fields
        book_value_keys = [k for k in data[0].keys() if 'book' in k.lower()]
        debt_keys = [k for k in data[0].keys() if 'debt' in k.lower()]
        print(f"   Book value keys: {book_value_keys}")
        print(f"   Debt keys: {debt_keys}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 3: Dividends Calendar
print(f"\n3. Testing Dividends Calendar Endpoint:")
print(f"   URL: {BASE_URL}/dividends-calendar?from=2025-01-01&to=2026-01-21")
try:
    response = requests.get(f"{BASE_URL}/dividends-calendar?from=2025-01-01&to=2026-01-21", timeout=10)
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Total records: {len(data) if isinstance(data, list) else 'Not a list'}")
    
    # Find AGNC in the data
    agnc_dividends = [d for d in data if d.get('symbol') == TICKER] if isinstance(data, list) else []
    print(f"   AGNC records found: {len(agnc_dividends)}")
    if agnc_dividends:
        print(f"   Sample AGNC dividend: {json.dumps(agnc_dividends[0], indent=2)}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 4: Insider Trading Statistics
print(f"\n4. Testing Insider Trading Statistics Endpoint:")
print(f"   URL: {BASE_URL}/insider-trading/statistics?symbol={TICKER}")
try:
    response = requests.get(f"{BASE_URL}/insider-trading/statistics?symbol={TICKER}", timeout=10)
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Response: {json.dumps(data, indent=2)[:500]}")
    if data:
        print(f"   Keys available: {list(data[0].keys()) if isinstance(data, list) and len(data) > 0 else list(data.keys()) if isinstance(data, dict) else 'No keys'}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 5: Try with API key parameter
print(f"\n5. Testing Quote with API key parameter:")
print(f"   URL: {BASE_URL}/quote?symbol={TICKER}&apikey={API_KEY}")
try:
    response = requests.get(f"{BASE_URL}/quote?symbol={TICKER}&apikey={API_KEY}", timeout=10)
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Response: {json.dumps(data, indent=2)[:500]}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 6: Try the old v3 endpoint structure
print(f"\n6. Testing OLD API v3 endpoint structure:")
print(f"   URL: https://financialmodelingprep.com/api/v3/quote/{TICKER}?apikey={API_KEY}")
try:
    response = requests.get(f"https://financialmodelingprep.com/api/v3/quote/{TICKER}?apikey={API_KEY}", timeout=10)
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Response: {json.dumps(data, indent=2)[:500]}")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
