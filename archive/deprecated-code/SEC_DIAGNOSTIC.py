#!/usr/bin/env python3
"""
SEC DIAGNOSTIC TEST
Tests if SEC.gov is accessible and Form 4 parsing works
"""

import requests
from bs4 import BeautifulSoup
import time

def test_sec_connection():
    """Test if we can connect to SEC.gov"""
    print("="*70)
    print("SEC.GOV CONNECTION TEST")
    print("="*70)
    print()
    
    try:
        print("Testing SEC.gov accessibility...")
        
        # Test 1: Basic connection
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Research/1.0; +research@example.com)',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.sec.gov'
        })
        
        r = session.get('https://www.sec.gov', timeout=10)
        
        if r.status_code == 200:
            print("✓ SEC.gov is accessible")
        else:
            print(f"✗ SEC.gov returned status code: {r.status_code}")
            return False
        
        time.sleep(0.5)
        
        # Test 2: Company tickers endpoint
        print("\nTesting company tickers endpoint...")
        r = session.get('https://www.sec.gov/files/company_tickers.json', timeout=10)
        
        if r.status_code == 200:
            print("✓ Company tickers endpoint works")
            data = r.json()
            print(f"  Found {len(data)} companies")
        else:
            print(f"✗ Tickers endpoint returned: {r.status_code}")
            return False
        
        time.sleep(0.5)
        
        # Test 3: Get CIK for Apple
        print("\nTesting CIK lookup for AAPL...")
        cik = None
        for entry in data.values():
            if entry['ticker'].upper() == 'AAPL':
                cik = str(entry['cik_str']).zfill(10)
                print(f"✓ Found CIK for AAPL: {cik}")
                break
        
        if not cik:
            print("✗ Could not find AAPL in ticker list")
            return False
        
        time.sleep(0.5)
        
        # Test 4: Get Form 4 filings for Apple
        print("\nTesting Form 4 filings for AAPL...")
        url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&dateb=&owner=include&count=40"
        r = session.get(url, timeout=10)
        
        if r.status_code == 200:
            print("✓ Form 4 endpoint accessible")
        else:
            print(f"✗ Form 4 endpoint returned: {r.status_code}")
            return False
        
        # Test 5: Parse the response
        print("\nParsing Form 4 filings...")
        soup = BeautifulSoup(r.content, 'html.parser')
        table = soup.find('table', {'class': 'tableFile2'})
        
        if not table:
            print("✗ Could not find filings table")
            print("Page content preview:")
            print(r.text[:500])
            return False
        
        print("✓ Found filings table")
        
        # Count rows
        rows = table.find_all('tr')[1:]  # Skip header
        print(f"  Found {len(rows)} Form 4 filings")
        
        if len(rows) == 0:
            print("  ⚠️  No Form 4 filings found (this could be normal during blackout periods)")
        else:
            # Show first 3 filings
            print("\n  Recent filings:")
            for i, row in enumerate(rows[:3]):
                cols = row.find_all('td')
                if len(cols) >= 4:
                    date = cols[3].text.strip()
                    insider = cols[2].text.strip()[:50]
                    print(f"    {i+1}. {date} - {insider}")
        
        print()
        print("="*70)
        print("✓ ALL TESTS PASSED - SEC.GOV IS WORKING")
        print("="*70)
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Network error: {e}")
        print("\nPossible issues:")
        print("  - No internet connection")
        print("  - SEC.gov is blocking your IP")
        print("  - VPN required")
        print("  - Firewall blocking")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_biotech_stock(ticker):
    """Test SEC filings for a specific biotech stock"""
    print()
    print("="*70)
    print(f"TESTING BIOTECH STOCK: {ticker}")
    print("="*70)
    print()
    
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Research/1.0; +research@example.com)',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.sec.gov'
        })
        
        # Get CIK
        print(f"Looking up CIK for {ticker}...")
        r = session.get('https://www.sec.gov/files/company_tickers.json', timeout=10)
        data = r.json()
        
        cik = None
        for entry in data.values():
            if entry['ticker'].upper() == ticker.upper():
                cik = str(entry['cik_str']).zfill(10)
                print(f"✓ Found CIK: {cik}")
                break
        
        if not cik:
            print(f"✗ Could not find {ticker} in SEC database")
            return False
        
        time.sleep(0.5)
        
        # Get Form 4s
        print(f"\nFetching Form 4 filings...")
        url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&dateb=&owner=include&count=40"
        r = session.get(url, timeout=10)
        
        soup = BeautifulSoup(r.content, 'html.parser')
        table = soup.find('table', {'class': 'tableFile2'})
        
        if not table:
            print("✗ No filings table found")
            return False
        
        rows = table.find_all('tr')[1:]
        print(f"✓ Found {len(rows)} total Form 4 filings")
        
        if len(rows) == 0:
            print(f"\n⚠️  {ticker} has NO Form 4 filings in SEC database")
            print("This could mean:")
            print("  - Very small company with no insider trading")
            print("  - Blackout period (no trading allowed)")
            print("  - Company is very new")
            return True
        
        # Analyze filings
        print(f"\nRecent filings for {ticker}:")
        c_level_count = 0
        
        for i, row in enumerate(rows[:10]):
            cols = row.find_all('td')
            if len(cols) >= 4:
                date = cols[3].text.strip()
                insider = cols[2].text.strip()
                
                is_c_level = any(title in insider.lower() for title in [
                    'ceo', 'chief executive', 'cfo', 'chief financial',
                    'coo', 'chief operating', 'president', 'chairman',
                    'chief medical', 'cmo', 'chief scientific', 'cso'
                ])
                
                if is_c_level:
                    c_level_count += 1
                    marker = "🔴 C-LEVEL"
                else:
                    marker = "○"
                
                print(f"  {marker} {date} - {insider[:60]}")
        
        print(f"\n📊 Summary:")
        print(f"  Total filings: {len(rows)}")
        print(f"  C-level filings: {c_level_count}")
        
        if c_level_count > 0:
            print(f"  ✓ {ticker} has C-level insider activity!")
        else:
            print(f"  ⚠️  {ticker} has no C-level filings (only regular insiders)")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing {ticker}: {e}")
        return False

if __name__ == '__main__':
    # Run basic SEC test
    if test_sec_connection():
        print()
        
        # Test some biotech stocks
        biotechs = ['FOLD', 'RARE', 'VKTX', 'SANA', 'IONS']
        
        print("\n" + "="*70)
        print("TESTING BIOTECH STOCKS")
        print("="*70)
        
        for ticker in biotechs:
            test_biotech_stock(ticker)
            time.sleep(1)
        
        print()
        print("="*70)
        print("DIAGNOSTIC COMPLETE")
        print("="*70)
        print()
        print("If you see 0 filings for all stocks:")
        print("  → Either SEC.gov is blocking you")
        print("  → Or it's blackout period (late December)")
        print()
        print("If you see filings but scanner shows 0:")
        print("  → Bug in scanner code (we'll fix)")
    else:
        print("\n⚠️  Cannot proceed - SEC.gov is not accessible")
        print("\nTroubleshooting:")
        print("  1. Check internet connection")
        print("  2. Try with VPN")
        print("  3. Wait 30 minutes and try again")
