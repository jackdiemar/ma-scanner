#!/usr/bin/env python3
"""
SEC FILING DETECTOR - ENHANCED VERSION
Shows ALL Form 4s, not just C-level, to diagnose the issue
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

print("="*70)
print("SEC FILING DETECTOR - ENHANCED")
print("="*70)

ticker = input("\nEnter ticker (e.g., AAPL): ").strip().upper()

session = requests.Session()
session.headers.update({
    'User-Agent': 'Research research@example.com',
    'Host': 'www.sec.gov'
})

# Get CIK
print(f"\n🔍 Getting CIK for {ticker}...")
url = "https://www.sec.gov/files/company_tickers.json"
r = session.get(url, timeout=10)
time.sleep(0.2)

cik = None
if r.status_code == 200:
    for entry in r.json().values():
        if entry['ticker'].upper() == ticker:
            cik = str(entry['cik_str']).zfill(10)
            print(f"✅ CIK: {cik}")
            break

if not cik:
    print(f"❌ No CIK found")
    exit(1)

# Get Form 4s
print(f"\n🔍 Fetching ALL Form 4 filings (last 90 days)...")
url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&dateb=&owner=include&count=100"
print(f"URL: {url}\n")

r = session.get(url, timeout=10)
time.sleep(0.2)

soup = BeautifulSoup(r.content, 'html.parser')
table = soup.find('table', {'class': 'tableFile2'})

if not table:
    print("❌ No table found")
    print("\nDumping HTML to see what's wrong:")
    print(r.text[:2000])
    exit(1)

print("✅ Found table\n")
print("="*70)
print("ALL FORM 4 FILINGS (last 90 days):")
print("="*70)

ninety_days = datetime.now() - timedelta(days=90)
thirty_days = datetime.now() - timedelta(days=30)

all_count = 0
thirty_count = 0
c_level_count = 0

c_level_titles = ['ceo', 'cfo', 'coo', 'chief', 'president', 'director', 'officer', 'exec']

for i, row in enumerate(table.find_all('tr')[1:]):
    cols = row.find_all('td')
    if len(cols) < 4:
        continue
    
    try:
        date_str = cols[3].text.strip()
        filing_date = datetime.strptime(date_str, '%Y-%m-%d')
        
        if filing_date < ninety_days:
            break
        
        all_count += 1
        
        insider = cols[2].get_text(strip=True)
        link_elem = cols[1].find('a')
        link = 'https://www.sec.gov' + link_elem['href'] if link_elem else ''
        
        is_c_level = any(title in insider.lower() for title in c_level_titles)
        is_recent = filing_date >= thirty_days
        
        if is_recent:
            thirty_count += 1
            if is_c_level:
                c_level_count += 1
        
        # Show first 20 filings
        if i < 20:
            status = ""
            if is_c_level:
                status += "👔 C-LEVEL"
            if is_recent:
                status += " 🆕 RECENT" if status else "🆕 RECENT"
            
            print(f"{date_str} | {insider[:60]}")
            if status:
                print(f"           {status}")
            print(f"           {link}\n")
    
    except Exception as e:
        print(f"Error parsing row: {e}")
        continue

print("="*70)
print(f"\n📊 SUMMARY:")
print(f"   Total Form 4s (90 days): {all_count}")
print(f"   Recent Form 4s (30 days): {thirty_count}")
print(f"   C-Level Form 4s (30 days): {c_level_count}")

print("\n" + "="*70)
print("DIAGNOSIS:")
print("="*70)

if all_count == 0:
    print("❌ NO FORM 4 FILINGS AT ALL IN 90 DAYS")
    print("   This is VERY unusual for most stocks")
    print("   Possible causes:")
    print("   1. SEC.gov HTML structure changed")
    print("   2. No filings exist (rare)")
    print("   3. Parsing error")
elif c_level_count == 0:
    print(f"⚠️  Found {all_count} Form 4s but NONE from C-level")
    print("   Possible causes:")
    print("   1. C-level title detection too strict")
    print("   2. No C-level insiders filed recently")
    print("   3. All filings from non-executive insiders")
else:
    print(f"✅ FOUND {c_level_count} C-LEVEL FILINGS!")
    print(f"   Scanner SHOULD detect these")
    print(f"   If scanner shows 0, there's a bug")

print("="*70)
