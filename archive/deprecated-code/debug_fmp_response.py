#!/usr/bin/env python3
"""
Debug FMP insider API - see actual response structure
"""

import requests
import json
from secure_config import get_env

FMP_API_KEY = get_env("FMP_API_KEY")

print("="*70)
print("DEBUG: FMP INSIDER API RESPONSE")
print("="*70)

# Try different endpoints
endpoints = [
    ("Latest insider (all)", f"https://financialmodelingprep.com/stable/insider-trading/latest?page=0&limit=5&apikey={FMP_API_KEY}"),
    ("Search (AAPL)", f"https://financialmodelingprep.com/stable/insider-trading/search?symbol=AAPL&page=0&limit=5&apikey={FMP_API_KEY}"),
    ("Search (no symbol)", f"https://financialmodelingprep.com/stable/insider-trading/search?page=0&limit=5&apikey={FMP_API_KEY}"),
]

for name, url in endpoints:
    print(f"\n{'='*70}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"{'='*70}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                print(f"✓ Got {len(data)} records")
                print("\nFirst record structure:")
                print(json.dumps(data[0], indent=2))
                
                print("\nAvailable fields:")
                print(", ".join(data[0].keys()))
                
            elif isinstance(data, dict):
                print("Response is dict (error?):")
                print(json.dumps(data, indent=2))
            else:
                print(f"Empty response or wrong format: {type(data)}")
        else:
            print(f"✗ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"✗ Error: {e}")

print("\n" + "="*70)
print("RECOMMENDATION")
print("="*70)
print("\nBased on the response structure above:")
print("1. Check which endpoint returns data")
print("2. Note the exact field names")
print("3. Update scanner to use correct fields")
