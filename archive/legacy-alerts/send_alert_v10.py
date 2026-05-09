#!/usr/bin/env python3
"""
send_alert.py - V10.3 Email alerts - CLEAN VERSION
Clean summary at top, less cluttered design

Usage: python3 send_alert.py <scan_results.json>
"""

import sys
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from secure_config import get_csv_env, get_env

# Gmail configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = get_env("SMTP_USER")
SMTP_PASSWORD = get_env("SMTP_PASSWORD")

def format_clean_alert(results, scan_date):
    """Format clean email with summary at top"""
    
    high_alerts = []
    medium_alerts = []
    watch_list = []
    distress_signals = []
    
    for ticker, data in results.items():
        score = data.get('score', 0)
        tier = data.get('conviction_tier', 'BELOW_THRESHOLD')
        investment_tier = data.get('investment_tier', 'UNKNOWN')
        distress_tier = data.get('distress_tier', 'NORMAL')
        
        stock_data = {
            'ticker': ticker,
            'score': score,
            'tier': tier,
            'investment_tier': investment_tier,
            'distress_tier': distress_tier,
            'distress_uses': data.get('distress_uses', []),
            'insider_pct': data.get('insider_pct', 0),
            'signals': data.get('signals', [])[:3],  # Only top 3
            'runway': data.get('runway', 0),
            'insider': data.get('c_level_sale_value', 0) / 1_000_000,
            'market_cap': data.get('market_cap', 0)
        }
        
        # Categorize by conviction tier AND investment tier
        # Prioritize HIGH_INVESTMENT stocks
        if investment_tier == 'HIGH_INVESTMENT' or tier == 'HIGH_CONVICTION':
            high_alerts.append(stock_data)
        elif investment_tier == 'MODERATE_INVESTMENT' or tier == 'MEDIUM_CONVICTION':
            medium_alerts.append(stock_data)
        elif tier == 'WATCH' or investment_tier == 'WATCH_INVESTMENT':
            watch_list.append(stock_data)
        
        # Track distress signals separately
        if investment_tier in ['AVOID', 'SPECULATIVE'] or distress_tier in ['EXTREME_DISTRESS', 'DEATH_SPIRAL']:
            distress_signals.append(stock_data)
    
    high_alerts.sort(key=lambda x: x['score'], reverse=True)
    medium_alerts.sort(key=lambda x: x['score'], reverse=True)
    watch_list.sort(key=lambda x: x['score'], reverse=True)
    
    has_alerts = len(high_alerts) > 0 or len(medium_alerts) > 0
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ margin: 0; padding: 0; font-family: -apple-system, sans-serif; background: #0a0a0a; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #fff; }}
            .header {{ background: #1a1a1a; padding: 25px 30px; text-align: center; }}
            .logo {{ font-family: Georgia; font-size: 32px; color: #fff; margin: 0; }}
            .tag {{ font-size: 10px; color: #00ff88; text-transform: uppercase; letter-spacing: 2px; margin-top: 5px; }}
            
            .summary {{ background: #f8f8f8; padding: 25px 30px; border-bottom: 3px solid #e0e0e0; }}
            .summary-title {{ font-size: 18px; font-weight: 700; margin: 0 0 15px 0; }}
            .stats {{ display: flex; gap: 10px; margin-bottom: 15px; }}
            .stat-box {{ flex: 1; background: #fff; padding: 15px; border-radius: 6px; text-align: center; border: 2px solid #e0e0e0; }}
            .stat-box.active {{ border-color: #00ff88; }}
            .stat-num {{ font-size: 28px; font-weight: 700; margin: 0; }}
            .stat-num.high {{ color: #ff3b30; }}
            .stat-num.med {{ color: #ff9500; }}
            .stat-label {{ font-size: 10px; color: #666; text-transform: uppercase; margin-top: 3px; }}
            .summary-text {{ font-size: 13px; color: #555; line-height: 1.5; margin-top: 12px; }}
            
            .content {{ padding: 30px; }}
            .section-title {{ font-size: 16px; font-weight: 700; margin: 0 0 15px 0; padding-bottom: 8px; border-bottom: 2px solid #00ff88; }}
            
            .stock {{ background: #f9f9f9; border-left: 4px solid #e0e0e0; padding: 15px; margin: 0 0 12px 0; border-radius: 4px; }}
            .stock.high {{ border-left-color: #ff3b30; background: #fff5f5; }}
            .stock.med {{ border-left-color: #ff9500; background: #fff9f0; }}
            .stock-head {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
            .ticker {{ font-size: 20px; font-weight: 700; }}
            .score {{ font-size: 24px; font-weight: 700; color: #ff3b30; }}
            .meta {{ display: flex; gap: 15px; font-size: 12px; color: #666; margin-bottom: 10px; }}
            .meta-item strong {{ color: #1a1a1a; }}
            .signals {{ padding-top: 10px; border-top: 1px solid #e0e0e0; }}
            .signal {{ font-size: 12px; color: #555; padding: 4px 0; }}
            .signal::before {{ content: "•"; color: #00ff88; font-weight: bold; margin-right: 6px; }}
            
            .watch {{ background: #f5f5f5; padding: 15px; border-radius: 4px; margin-top: 15px; }}
            .watch-item {{ padding: 10px; background: #fff; border-radius: 4px; margin: 6px 0; display: flex; justify-content: space-between; align-items: center; font-size: 13px; }}
            .watch-ticker {{ font-weight: 600; }}
            .watch-meta {{ font-size: 11px; color: #999; margin-top: 2px; }}
            .watch-score {{ font-size: 16px; font-weight: 700; color: #666; }}
            
            .footer {{ background: #1a1a1a; padding: 25px 30px; text-align: center; }}
            .footer-logo {{ font-family: Georgia; font-size: 22px; color: #fff; margin: 0 0 8px 0; }}
            .footer-text {{ font-size: 11px; color: #999; line-height: 1.5; margin: 6px 0; }}
            
            @media only screen and (max-width: 600px) {{
                .header {{ padding: 20px !important; }}
                .logo {{ font-size: 26px !important; }}
                .summary {{ padding: 20px !important; }}
                .stats {{ flex-direction: column !important; gap: 8px !important; }}
                .stat-box {{ padding: 12px !important; }}
                .content {{ padding: 20px !important; }}
                .stock {{ padding: 12px !important; }}
                .ticker {{ font-size: 18px !important; }}
                .score {{ font-size: 20px !important; }}
                .meta {{ flex-direction: column !important; gap: 6px !important; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">bsc</div>
                <div class="tag">Black Starlight Capital</div>
            </div>
            
            <div class="summary">
                <div class="summary-title">Daily Scan — {scan_date}</div>
                <div class="stats">
                    <div class="stat-box {'active' if len(high_alerts) > 0 else ''}">
                        <div class="stat-num high">{len(high_alerts)}</div>
                        <div class="stat-label">High</div>
                    </div>
                    <div class="stat-box {'active' if len(medium_alerts) > 0 else ''}">
                        <div class="stat-num med">{len(medium_alerts)}</div>
                        <div class="stat-label">Medium</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-num">{len(watch_list)}</div>
                        <div class="stat-label">Watch</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-num">{len(results)}</div>
                        <div class="stat-label">Scanned</div>
                    </div>
                </div>
                <div class="summary-text">
                    {'<strong>🔴 ACTION:</strong> ' + str(len(high_alerts)) + ' high conviction alert' + ('s' if len(high_alerts) != 1 else '') + ' — review immediately' if high_alerts else 
                     '<strong>🟡 INVESTIGATE:</strong> ' + str(len(medium_alerts)) + ' medium alert' + ('s' if len(medium_alerts) != 1 else '') + ' — research recommended' if medium_alerts else
                     '✓ No actionable signals today — ' + str(len(watch_list)) + ' on watch list'}
                    <br><br>
                    <strong>📊 Sector Health:</strong> {len(distress_signals)} extreme distress signal{'s' if len(distress_signals) != 1 else ''} detected
                    {'<br>⚠️ Elevated sector stress - proceed with caution' if len(distress_signals) >= 5 else '<br>✓ Normal sector conditions' if len(distress_signals) <= 2 else '<br>Moderate sector stress'}
                </div>
            </div>
            
            <div class="content">
    """
    
    if high_alerts:
        html += '<div class="section-title">🔴 High Conviction</div>'
        for s in high_alerts:
            # Investment tier badge
            inv_tier = s.get('investment_tier', 'UNKNOWN')
            inv_emoji = '⭐' if inv_tier == 'HIGH_INVESTMENT' else '🔸' if inv_tier == 'MODERATE_INVESTMENT' else '⚠️' if inv_tier == 'SPECULATIVE' else '❌'
            inv_label = inv_tier.replace('_', ' ').title()
            insider_pct = s.get('insider_pct', 0)
            
            html += f"""
            <div class="stock high">
                <div class="stock-head">
                    <div class="ticker">{s['ticker']}</div>
                    <div class="score">{s['score']:.0f}</div>
                </div>
                <div class="meta">
                    <div class="meta-item"><strong>Investment:</strong> {inv_emoji} {inv_label}</div>
                    <div class="meta-item"><strong>Runway:</strong> {s['runway']:.1f}Q</div>
                    <div class="meta-item"><strong>Insider:</strong> ${s['insider']:.1f}M ({insider_pct:.2f}%)</div>
                    <div class="meta-item"><strong>Cap:</strong> ${s['market_cap']:.0f}M</div>
                </div>
                <div class="signals">
            """
            for sig in s['signals'][:3]:
                html += f'<div class="signal">{sig.get("type", "Signal")}: {sig.get("detail", "")}</div>'
            html += '</div></div>'
    
    if medium_alerts:
        html += '<div class="section-title" style="margin-top: 25px;">🟡 Medium Conviction</div>'
        for s in medium_alerts:
            # Investment tier badge
            inv_tier = s.get('investment_tier', 'UNKNOWN')
            inv_emoji = '⭐' if inv_tier == 'HIGH_INVESTMENT' else '🔸' if inv_tier == 'MODERATE_INVESTMENT' else '⚠️' if inv_tier == 'SPECULATIVE' else '❌'
            inv_label = inv_tier.replace('_', ' ').title()
            insider_pct = s.get('insider_pct', 0)
            
            html += f"""
            <div class="stock med">
                <div class="stock-head">
                    <div class="ticker">{s['ticker']}</div>
                    <div class="score">{s['score']:.0f}</div>
                </div>
                <div class="meta">
                    <div class="meta-item"><strong>Investment:</strong> {inv_emoji} {inv_label}</div>
                    <div class="meta-item"><strong>Runway:</strong> {s['runway']:.1f}Q</div>
                    <div class="meta-item"><strong>Insider:</strong> ${s['insider']:.1f}M ({insider_pct:.2f}%)</div>
                    <div class="meta-item"><strong>Cap:</strong> ${s['market_cap']:.0f}M</div>
                </div>
                <div class="signals">
            """
            for sig in s['signals'][:3]:
                html += f'<div class="signal">{sig.get("type", "Signal")}: {sig.get("detail", "")}</div>'
            html += '</div></div>'
    
    if watch_list and not has_alerts:
        html += '<div class="section-title">⚪ Watch List (Top 5)</div><div class="watch">'
        for s in watch_list[:5]:
            html += f"""
            <div class="watch-item">
                <div>
                    <div class="watch-ticker">{s['ticker']}</div>
                    <div class="watch-meta">{s['runway']:.1f}Q · ${s['insider']:.1f}M insider</div>
                </div>
                <div class="watch-score">{s['score']:.0f}</div>
            </div>
            """
        html += '</div>'
    
    # Add distress signals section
    if distress_signals:
        html += f'<div class="section-title" style="margin-top: 30px; color: #ff4444;">🚨 Distress Signals ({len(distress_signals)}) - DO NOT INVEST</div>'
        html += '<div style="background: #fff5f5; border: 2px solid #ffdddd; border-radius: 8px; padding: 15px; margin-bottom: 20px;">'
        html += '<div style="font-size: 12px; color: #666; margin-bottom: 12px;"><strong>⚠️ Bankruptcy Risk</strong> — Use for sector health tracking, not investment</div>'
        
        for s in distress_signals[:5]:
            distress_emoji = '💀' if s['distress_tier'] == 'DEATH_SPIRAL' else '🚨'
            html += f"""
            <div style="background: white; border: 1px solid #ffdddd; border-radius: 6px; padding: 12px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <div style="font-size: 16px; font-weight: 700;">{distress_emoji} {s['ticker']}</div>
                    <div style="font-size: 14px; color: #999;">{s['score']:.0f}pts</div>
                </div>
                <div style="font-size: 11px; color: #666; margin-bottom: 6px;">
                    <strong>Insider:</strong> {s['insider_pct']:.2f}% | <strong>Cap:</strong> ${s['market_cap']:.0f}M
                </div>
                <div style="font-size: 11px; color: #666;">
                    <strong>Uses:</strong> {', '.join(s['distress_uses'][:2])}
                </div>
            </div>
            """
        html += '</div>'
    
    html += """
            </div>
            <div class="footer">
                <div class="footer-logo">bsc</div>
                <div class="footer-text">Black Starlight Capital · M&A Intelligence</div>
                <div class="footer-text" style="margin-top: 10px; font-size: 9px; color: #666;">
                    🔴 HIGH (85+) · 🟡 MEDIUM (80-84) · ⚪ WATCH (75-79) · 🚨 DISTRESS (avoid)
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html, has_alerts, len(high_alerts), len(medium_alerts)

def send_email(to_email, subject, html_body):
    """Send email via Gmail"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_USERNAME
        msg['To'] = to_email
        
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"✓ Email sent to {to_email}")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 send_alert.py <scan_results.json>")
        sys.exit(1)
    
    scan_file = sys.argv[1]
    alert_emails = get_csv_env("SMTP_RECIPIENTS")
    
    try:
        with open(scan_file, 'r') as f:
            scan_data = json.load(f)
    except Exception as e:
        print(f"Error loading file: {e}")
        sys.exit(1)
    
    results = scan_data.get('results', {})
    scan_date = datetime.now().strftime("%b %d, %Y at %I:%M %p")
    
    html_body, has_alerts, high_count, medium_count = format_clean_alert(results, scan_date)
    
    if high_count > 0:
        subject = f"🔴 BSC: {high_count} High Alert{'s' if high_count != 1 else ''}"
    elif medium_count > 0:
        subject = f"🟡 BSC: {medium_count} Medium Alert{'s' if medium_count != 1 else ''}"
    else:
        subject = f"📊 BSC Daily — {datetime.now().strftime('%b %d')}"
    
    print(f"\n{'='*50}")
    print(f"BSC Email Alert")
    print(f"{'='*50}")
    print(f"Scanned: {len(results)} stocks")
    print(f"High: {high_count} | Medium: {medium_count}")
    print(f"{'='*50}\n")
    
    for email in alert_emails:
        send_email(email, subject, html_body)

if __name__ == "__main__":
    main()
