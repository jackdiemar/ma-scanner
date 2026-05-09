#!/usr/bin/env python3
"""
send_alert.py - V10.4 Email alerts
Separates INVESTMENT signals from DISTRESS signals

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

def format_alert(results, scan_date):
    """Format email separating investment opportunities from distress signals"""
    
    investment_signals = []
    distress_signals = []
    
    for ticker, data in results.items():
        score = data.get('score', 0)
        mcap = data.get('market_cap', 0)
        insider_sales = data.get('c_level_sale_value', 0)
        insider_pct = (insider_sales / (mcap * 1_000_000)) * 100 if mcap > 0 else 0
        
        stock_data = {
            'ticker': ticker,
            'score': score,
            'signals': data.get('signals', []),
            'runway': data.get('runway', 0),
            'insider_sales': insider_sales,
            'insider_pct': insider_pct,
            'market_cap': mcap
        }
        
        # INVESTMENT = moderate distress (0.3-2% insider, $500M+ cap)
        # DISTRESS = extreme distress (3%+ insider OR <$100M cap)
        if score >= 85:
            if insider_pct >= 3.0 or mcap < 100:
                distress_signals.append(stock_data)
            elif 500 <= mcap <= 5000 and 0.5 <= insider_pct <= 2.0:
                investment_signals.append(stock_data)
            elif 0.3 <= insider_pct < 3.0 and mcap >= 100:
                investment_signals.append(stock_data)
            else:
                # Edge cases - default to investment if score is high
                investment_signals.append(stock_data)
    
    investment_signals.sort(key=lambda x: x['score'], reverse=True)
    distress_signals.sort(key=lambda x: x['score'], reverse=True)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ margin: 0; padding: 0; font-family: -apple-system, sans-serif; background: #0a0a0a; }}
            .container {{ max-width: 650px; margin: 0 auto; background: #fff; }}
            .header {{ background: #1a1a1a; padding: 25px 30px; text-align: center; }}
            .logo {{ font-family: Georgia; font-size: 32px; color: #fff; margin: 0; }}
            .tag {{ font-size: 10px; color: #00ff88; text-transform: uppercase; letter-spacing: 2px; margin-top: 5px; }}
            
            .summary {{ background: #f8f8f8; padding: 25px 30px; border-bottom: 3px solid #e0e0e0; }}
            .summary-title {{ font-size: 18px; font-weight: 700; margin: 0 0 15px 0; }}
            .stats {{ display: flex; gap: 10px; margin-bottom: 15px; }}
            .stat-box {{ flex: 1; background: #fff; padding: 15px; border-radius: 6px; text-align: center; border: 2px solid #e0e0e0; }}
            .stat-box.buy {{ border-color: #00ff88; }}
            .stat-box.distress {{ border-color: #ff4444; }}
            .stat-num {{ font-size: 28px; font-weight: 700; margin: 0; }}
            .stat-num.buy {{ color: #00aa66; }}
            .stat-num.distress {{ color: #ff4444; }}
            .stat-label {{ font-size: 10px; color: #666; text-transform: uppercase; margin-top: 3px; }}
            .summary-text {{ font-size: 13px; color: #555; line-height: 1.6; margin-top: 12px; }}
            
            .content {{ padding: 30px; }}
            .section-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 3px solid #00ff88; }}
            .section-title {{ font-size: 18px; font-weight: 700; margin: 0; }}
            .section-count {{ font-size: 24px; font-weight: 700; color: #00aa66; }}
            
            .stock {{ background: #fff; border: 2px solid #e0e0e0; border-radius: 8px; padding: 20px; margin-bottom: 20px; }}
            .stock.buy {{ border-color: #00ff88; background: #f0fff8; }}
            .stock.distress {{ border-color: #ff4444; background: #fff5f5; }}
            
            .stock-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
            .ticker {{ font-size: 28px; font-weight: 700; }}
            .score {{ font-size: 32px; font-weight: 700; }}
            .score.buy {{ color: #00aa66; }}
            .score.distress {{ color: #ff4444; }}
            
            .badge {{ display: inline-block; padding: 4px 10px; border-radius: 4px; font-size: 10px; font-weight: 700; text-transform: uppercase; margin-bottom: 15px; }}
            .badge.buy {{ background: #00ff88; color: #000; }}
            .badge.distress {{ background: #ff4444; color: #fff; }}
            
            .metrics {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 15px; padding: 15px; background: #f9f9f9; border-radius: 6px; }}
            .metric {{ font-size: 12px; }}
            .metric-label {{ color: #666; font-weight: 600; }}
            .metric-value {{ font-weight: 700; color: #1a1a1a; font-size: 14px; }}
            
            .signals-title {{ font-size: 12px; font-weight: 700; color: #666; margin-bottom: 10px; text-transform: uppercase; }}
            .signal {{ font-size: 13px; color: #333; padding: 8px 0; border-bottom: 1px solid #e0e0e0; line-height: 1.5; }}
            .signal:last-child {{ border-bottom: none; }}
            .signal-type {{ font-weight: 700; color: #1a1a1a; }}
            .signal-detail {{ color: #666; }}
            .signal-pts {{ float: right; font-weight: 700; color: #00aa66; }}
            
            .distress-warning {{ background: #fff3cd; border: 2px solid #ffcc00; border-radius: 8px; padding: 15px; margin-bottom: 20px; }}
            .distress-warning-title {{ font-size: 14px; font-weight: 700; color: #856404; margin-bottom: 8px; }}
            .distress-warning-text {{ font-size: 12px; color: #856404; line-height: 1.5; }}
            
            .footer {{ background: #1a1a1a; padding: 25px 30px; text-align: center; }}
            .footer-logo {{ font-family: Georgia; font-size: 22px; color: #fff; margin: 0 0 8px 0; }}
            .footer-text {{ font-size: 11px; color: #999; line-height: 1.5; margin: 6px 0; }}
            
            @media only screen and (max-width: 600px) {{
                .header {{ padding: 20px !important; }}
                .logo {{ font-size: 26px !important; }}
                .summary {{ padding: 20px !important; }}
                .stats {{ grid-template-columns: 1fr 1fr !important; }}
                .content {{ padding: 20px !important; }}
                .stock {{ padding: 15px !important; }}
                .ticker {{ font-size: 22px !important; }}
                .score {{ font-size: 26px !important; }}
                .metrics {{ grid-template-columns: 1fr !important; }}
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
                    <div class="stat-box buy">
                        <div class="stat-num buy">{len(investment_signals)}</div>
                        <div class="stat-label">Buy Signals</div>
                    </div>
                    <div class="stat-box distress">
                        <div class="stat-num distress">{len(distress_signals)}</div>
                        <div class="stat-label">Distress</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-num">{len(results)}</div>
                        <div class="stat-label">Scanned</div>
                    </div>
                </div>
                <div class="summary-text">
    """
    
    if investment_signals:
        html += f"<strong>✅ ACTIONABLE:</strong> {len(investment_signals)} investment opportunit{'ies' if len(investment_signals) != 1 else 'y'} detected — review immediately<br><br>"
    else:
        html += "<strong>📊 STATUS:</strong> No investment opportunities today<br><br>"
    
    html += f"<strong>📊 Sector Health:</strong> {len(distress_signals)} extreme distress signal{'s' if len(distress_signals) != 1 else ''} detected<br>"
    
    if len(distress_signals) >= 5:
        html += "⚠️ Elevated sector stress — wait for better opportunities"
    elif len(distress_signals) <= 2:
        html += "✅ Healthy sector — good time to deploy capital"
    else:
        html += "⚠️ Moderate sector stress — proceed with caution"
    
    html += """
                </div>
            </div>
            
            <div class="content">
    """
    
    # INVESTMENT SIGNALS
    if investment_signals:
        html += f"""
            <div class="section-header">
                <div class="section-title">✅ Investment Opportunities</div>
                <div class="section-count">{len(investment_signals)}</div>
            </div>
        """
        
        for stock in investment_signals:
            top_signals = sorted(stock['signals'], key=lambda x: x.get('pts', 0), reverse=True)[:5]
            
            # Determine tier
            if 500 <= stock['market_cap'] <= 5000 and 0.5 <= stock['insider_pct'] <= 2.0:
                tier = "HIGH CONVICTION"
            else:
                tier = "MODERATE"
            
            html += f"""
            <div class="stock buy">
                <div class="badge buy">{tier}</div>
                <div class="stock-header">
                    <div class="ticker">{stock['ticker']}</div>
                    <div class="score buy">{stock['score']:.0f}</div>
                </div>
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-label">Market Cap</div>
                        <div class="metric-value">${stock['market_cap']:.0f}M</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Cash Runway</div>
                        <div class="metric-value">{stock['runway']:.1f} quarters</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Insider Sales</div>
                        <div class="metric-value">${stock['insider_sales']/1_000_000:.1f}M</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">% of Company</div>
                        <div class="metric-value">{stock['insider_pct']:.2f}%</div>
                    </div>
                </div>
                <div class="signals-title">Key Signals</div>
            """
            
            for sig in top_signals:
                html += f"""
                <div class="signal">
                    <span class="signal-type">{sig.get('type', 'Signal')}</span>
                    <span class="signal-pts">{sig.get('pts', 0):.0f}pts</span><br>
                    <span class="signal-detail">{sig.get('detail', '')}</span>
                </div>
                """
            
            html += "</div>"
    
    # DISTRESS SIGNALS
    if distress_signals:
        html += f"""
            <div class="distress-warning">
                <div class="distress-warning-title">⚠️ About Distress Signals</div>
                <div class="distress-warning-text">
                    The following companies show extreme distress (3%+ insider selling or tiny market cap). 
                    Based on historical data, these have 75% bankruptcy risk. <strong>DO NOT INVEST.</strong>
                    Use for sector health tracking only.
                </div>
            </div>
            
            <div class="section-header" style="border-color: #ff4444;">
                <div class="section-title" style="color: #ff4444;">🚨 Distress Signals (Avoid)</div>
                <div class="section-count" style="color: #ff4444;">{len(distress_signals)}</div>
            </div>
        """
        
        for stock in distress_signals:
            top_signals = sorted(stock['signals'], key=lambda x: x.get('pts', 0), reverse=True)[:3]
            
            html += f"""
            <div class="stock distress">
                <div class="badge distress">BANKRUPTCY RISK</div>
                <div class="stock-header">
                    <div class="ticker">{stock['ticker']}</div>
                    <div class="score distress">{stock['score']:.0f}</div>
                </div>
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-label">Market Cap</div>
                        <div class="metric-value">${stock['market_cap']:.0f}M</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Insider % (EXTREME)</div>
                        <div class="metric-value">{stock['insider_pct']:.2f}%</div>
                    </div>
                </div>
                <div class="signals-title">Why This Is Distressed</div>
            """
            
            for sig in top_signals:
                html += f"""
                <div class="signal">
                    <span class="signal-type">{sig.get('type', 'Signal')}</span><br>
                    <span class="signal-detail">{sig.get('detail', '')}</span>
                </div>
                """
            
            html += "</div>"
    
    html += """
            </div>
            <div class="footer">
                <div class="footer-logo">bsc</div>
                <div class="footer-text">Black Starlight Capital · M&A Intelligence</div>
                <div class="footer-text" style="margin-top: 10px; font-size: 9px; color: #666;">
                    ✅ BUY: Moderate distress (0.3-2% insider) · 🚨 AVOID: Extreme distress (3%+ insider)
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html, len(investment_signals), len(distress_signals)

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
    
    html_body, buy_count, distress_count = format_alert(results, scan_date)
    
    if buy_count > 0:
        subject = f"✅ BSC: {buy_count} Investment Signal{'s' if buy_count != 1 else ''}"
    elif distress_count > 0:
        subject = f"📊 BSC Daily — {distress_count} Distress Signal{'s' if distress_count != 1 else ''}"
    else:
        subject = f"📊 BSC Daily — {datetime.now().strftime('%b %d')}"
    
    print(f"\n{'='*50}")
    print(f"BSC Email Alert")
    print(f"{'='*50}")
    print(f"Scanned: {len(results)} stocks")
    print(f"Buy: {buy_count} | Distress: {distress_count}")
    print(f"{'='*50}\n")
    
    for email in alert_emails:
        send_email(email, subject, html_body)

if __name__ == "__main__":
    main()
