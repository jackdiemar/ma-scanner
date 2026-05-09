#!/usr/bin/env python3
"""
Analyze top BUY signals for investment potential
Filter by market cap and insider % for real opportunities
"""

import json

with open('scan_v10_20260106_080138.json', 'r') as f:
    data = json.load(f)

results = data['results']

# Get BUY signals (85+)
buy_signals = [(ticker, info) for ticker, info in results.items() 
               if info['score'] >= 85]

# Sort by score
buy_signals.sort(key=lambda x: x[1]['score'], reverse=True)

print("="*80)
print("TOP BUY SIGNALS - INVESTMENT ANALYSIS")
print("="*80)

print("\nFiltering for REAL opportunities:")
print("  ✓ Market cap: $200M - $5B (sweet spot)")
print("  ✓ Insider: 0.5% - 3% (distress, not panic)")
print("  ✓ Runway: 3-8Q (urgent but not desperate)")
print("  ✓ Score: 85-105pts")

print("\n" + "="*80)
print("ANALYSIS")
print("="*80)

investable = []

for ticker, info in buy_signals:
    score = info['score']
    mcap = info.get('market_cap', 0)
    runway = info.get('runway', 0)
    insider = info.get('c_level_sale_value', 0)
    
    # Calculate insider %
    if mcap > 0 and insider > 0:
        insider_pct = (insider / (mcap * 1_000_000)) * 100
    else:
        insider_pct = 0
    
    print(f"\n{ticker}: {score:.0f}pts")
    print(f"  Market Cap: ${mcap:.0f}M")
    print(f"  Runway: {runway:.1f}Q" if runway else "  Runway: N/A")
    print(f"  Insider: ${insider/1_000_000:.2f}M ({insider_pct:.2f}%)")
    
    # Investment filter
    good_size = 200 <= mcap <= 5000
    good_insider = 0.5 <= insider_pct <= 3.0
    good_runway = 3 <= runway <= 8 if runway else False
    
    print(f"  Size: {'✓' if good_size else '✗'} {'(too small)' if mcap < 200 else '(too large)' if mcap > 5000 else ''}")
    print(f"  Insider: {'✓' if good_insider else '✗'} {'(too low)' if insider_pct < 0.5 else '(panic mode)' if insider_pct > 3 else ''}")
    print(f"  Runway: {'✓' if good_runway else '✗'} {'(too tight)' if runway and runway < 3 else '(too long)' if runway and runway > 8 else '(missing)'}")
    
    # Top 3 signals
    top_signals = sorted(info['signals'], key=lambda x: x.get('pts', 0), reverse=True)[:3]
    print(f"  Top signals:")
    for sig in top_signals:
        print(f"    • {sig['type']} ({sig['pts']}pts)")
    
    if good_size and good_insider and good_runway:
        print(f"  ⭐ INVESTABLE")
        investable.append((ticker, score, mcap, insider_pct, runway))
    elif good_size and (good_insider or good_runway):
        print(f"  🔸 MAYBE - Check deeper")
        investable.append((ticker, score, mcap, insider_pct, runway))
    else:
        print(f"  ❌ PASS")

# Also check WATCH tier for hidden gems
watch_signals = [(ticker, info) for ticker, info in results.items() 
                 if 75 <= info['score'] < 85]

print("\n" + "="*80)
print("WATCH SIGNALS (75-84pts) - HIDDEN GEMS?")
print("="*80)

for ticker, info in sorted(watch_signals, key=lambda x: x[1]['score'], reverse=True)[:10]:
    score = info['score']
    mcap = info.get('market_cap', 0)
    runway = info.get('runway', 0)
    insider = info.get('c_level_sale_value', 0)
    
    if mcap > 0 and insider > 0:
        insider_pct = (insider / (mcap * 1_000_000)) * 100
    else:
        insider_pct = 0
    
    # Only show if good size
    if 500 <= mcap <= 5000:
        print(f"\n{ticker}: {score:.0f}pts - ${mcap:.0f}M cap")
        print(f"  Insider: {insider_pct:.2f}%, Runway: {runway:.1f}Q" if runway else f"  Insider: {insider_pct:.2f}%")
        
        if 0.3 <= insider_pct <= 2.0 and (3 <= runway <= 8 if runway else True):
            print(f"  🔸 INTERESTING - Lower score but good profile")
            investable.append((ticker, score, mcap, insider_pct, runway))

# Summary
print("\n" + "="*80)
print("INVESTMENT RECOMMENDATIONS")
print("="*80)

if investable:
    print(f"\nFound {len(investable)} investable opportunities:")
    print("\nTicker  Score  Market Cap  Insider%  Runway  Rating")
    print("-" * 60)
    
    for ticker, score, mcap, insider_pct, runway in sorted(investable, key=lambda x: x[1], reverse=True):
        rating = "⭐⭐⭐" if score >= 90 else "⭐⭐" if score >= 85 else "⭐"
        runway_str = f"{runway:.1f}Q" if runway else "N/A"
        print(f"{ticker:6}  {score:3.0f}   ${mcap:7.0f}M    {insider_pct:5.2f}%   {runway_str:5}  {rating}")
    
    print("\n⭐⭐⭐ = Strong buy")
    print("⭐⭐  = Good opportunity")
    print("⭐   = Worth researching")
else:
    print("\n⚠️  No stocks passed investment filters")
    print("Current scan may be too early/late in M&A cycle")
    print("Or market conditions don't support distressed buyouts")
