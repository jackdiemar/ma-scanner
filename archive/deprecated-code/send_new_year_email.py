#!/usr/bin/env python3
"""
BSC New Year 2026 Email
Send beautiful New Year greeting from Black Starlight Capital
"""

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

# Recipients
RECIPIENTS = get_csv_env("SMTP_RECIPIENTS")

def create_new_year_email():
    """Create beautiful HTML email for New Year 2026"""
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <!--[if mso]>
        <style type="text/css">
            body, table, td {font-family: Arial, Helvetica, sans-serif !important;}
        </style>
        <![endif]-->
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
            
            body {
                margin: 0 !important;
                padding: 0 !important;
                width: 100% !important;
                -webkit-text-size-adjust: 100%;
                -ms-text-size-adjust: 100%;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                background: #0a0a0a;
            }
            
            table {
                border-collapse: collapse;
                mso-table-lspace: 0pt;
                mso-table-rspace: 0pt;
            }
            
            img {
                border: 0;
                height: auto;
                line-height: 100%;
                outline: none;
                text-decoration: none;
                -ms-interpolation-mode: bicubic;
            }
            
            .container {
                max-width: 600px;
                margin: 0 auto;
                background: #ffffff;
            }
            
            .header {
                background: linear-gradient(135deg, #1a1a1a 0%, #000000 100%);
                padding: 60px 40px;
                text-align: center;
                position: relative;
                overflow: hidden;
            }
            
            .header::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: radial-gradient(circle at 30% 50%, rgba(0, 255, 136, 0.1) 0%, transparent 50%);
                pointer-events: none;
            }
            
            .logo {
                font-family: Georgia, serif;
                font-size: 56px;
                font-weight: normal;
                letter-spacing: -2px;
                color: #ffffff;
                margin: 0 0 10px 0;
                position: relative;
                z-index: 1;
            }
            
            .tagline {
                font-size: 14px;
                color: #00ff88;
                text-transform: uppercase;
                letter-spacing: 3px;
                font-weight: 600;
                position: relative;
                z-index: 1;
            }
            
            .year-banner {
                background: #00ff88;
                padding: 20px;
                text-align: center;
            }
            
            .year-text {
                font-size: 48px;
                font-weight: 700;
                color: #000000;
                margin: 0;
                letter-spacing: -1px;
            }
            
            .content {
                padding: 50px 40px;
                background: #ffffff;
            }
            
            .greeting {
                font-size: 28px;
                font-weight: 600;
                color: #1a1a1a;
                margin: 0 0 30px 0;
                line-height: 1.3;
            }
            
            .message {
                font-size: 16px;
                color: #333333;
                line-height: 1.8;
                margin: 0 0 25px 0;
            }
            
            .highlight {
                background: linear-gradient(120deg, #00ff88 0%, #00cc6a 100%);
                color: #000000;
                padding: 30px;
                border-radius: 8px;
                margin: 40px 0;
            }
            
            .highlight-title {
                font-size: 20px;
                font-weight: 700;
                color: #000000;
                margin: 0 0 15px 0;
            }
            
            .highlight-text {
                font-size: 15px;
                color: #1a1a1a;
                line-height: 1.6;
                margin: 0;
            }
            
            .stats {
                display: flex;
                justify-content: space-around;
                margin: 40px 0;
                padding: 30px 0;
                border-top: 2px solid #f0f0f0;
                border-bottom: 2px solid #f0f0f0;
            }
            
            .stat {
                text-align: center;
            }
            
            .stat-value {
                font-size: 36px;
                font-weight: 700;
                color: #00ff88;
                margin: 0 0 5px 0;
            }
            
            .stat-label {
                font-size: 12px;
                color: #666666;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            
            .closing {
                font-size: 16px;
                color: #333333;
                line-height: 1.8;
                margin: 30px 0 0 0;
            }
            
            .signature {
                margin-top: 40px;
                padding-top: 30px;
                border-top: 1px solid #e0e0e0;
            }
            
            .signature-name {
                font-size: 18px;
                font-weight: 600;
                color: #1a1a1a;
                margin: 0 0 5px 0;
            }
            
            .signature-title {
                font-size: 14px;
                color: #666666;
                margin: 0;
            }
            
            .footer {
                background: #1a1a1a;
                padding: 40px;
                text-align: center;
            }
            
            .footer-logo {
                font-family: Georgia, serif;
                font-size: 32px;
                color: #ffffff;
                margin: 0 0 15px 0;
                letter-spacing: -1px;
            }
            
            .footer-text {
                font-size: 13px;
                color: #999999;
                line-height: 1.6;
                margin: 10px 0;
            }
            
            .footer-link {
                color: #00ff88;
                text-decoration: none;
            }
            
            /* ========================================
               MOBILE RESPONSIVE STYLES
               ======================================== */
            
            @media only screen and (max-width: 600px) {
                body {
                    padding: 0 !important;
                }
                
                .container {
                    width: 100% !important;
                    max-width: 100% !important;
                }
                
                .header {
                    padding: 40px 20px !important;
                }
                
                .logo {
                    font-size: 42px !important;
                }
                
                .tagline {
                    font-size: 11px !important;
                    letter-spacing: 2px !important;
                }
                
                .year-banner {
                    padding: 15px !important;
                }
                
                .year-text {
                    font-size: 36px !important;
                }
                
                .content {
                    padding: 30px 20px !important;
                }
                
                .greeting {
                    font-size: 24px !important;
                    margin: 0 0 20px 0 !important;
                }
                
                .message {
                    font-size: 15px !important;
                    line-height: 1.7 !important;
                    margin: 0 0 20px 0 !important;
                }
                
                .highlight {
                    padding: 20px !important;
                    margin: 30px 0 !important;
                }
                
                .highlight-title {
                    font-size: 18px !important;
                }
                
                .highlight-text {
                    font-size: 14px !important;
                }
                
                .stats {
                    flex-direction: column !important;
                    padding: 20px 0 !important;
                    margin: 30px 0 !important;
                }
                
                .stat {
                    margin: 15px 0 !important;
                }
                
                .stat-value {
                    font-size: 32px !important;
                }
                
                .stat-label {
                    font-size: 11px !important;
                }
                
                .closing {
                    font-size: 15px !important;
                    line-height: 1.7 !important;
                }
                
                .signature {
                    margin-top: 30px !important;
                    padding-top: 20px !important;
                }
                
                .signature-name {
                    font-size: 16px !important;
                }
                
                .signature-title {
                    font-size: 13px !important;
                }
                
                .footer {
                    padding: 30px 20px !important;
                }
                
                .footer-logo {
                    font-size: 28px !important;
                }
                
                .footer-text {
                    font-size: 12px !important;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <div class="logo">bsc</div>
                <div class="tagline">Black Starlight Capital</div>
            </div>
            
            <!-- Year Banner -->
            <div class="year-banner">
                <div class="year-text">2026</div>
            </div>
            
            <!-- Content -->
            <div class="content">
                <div class="greeting">
                    Happy New Year! 🎉
                </div>
                
                <p class="message">
                    As we close the chapter on 2025 and step into 2026, I wanted to take a moment to express my gratitude and excitement for what lies ahead.
                </p>
                
                <p class="message">
                    This past year has been transformative. We've built systems, refined strategies, and laid the groundwork for something truly exceptional. The M&A intelligence platform is now operational, battle-tested, and ready to capitalize on the opportunities that 2026 will bring.
                </p>
                
                <!-- Highlight Box -->
                <div class="highlight">
                    <div class="highlight-title">Our 2026 Vision</div>
                    <p class="highlight-text">
                        This year, Black Starlight Capital will execute with precision. Our automated M&A prediction system is poised to identify billion-dollar acquisitions before they happen. The data is clear, the system is proven, and the opportunities are massive.
                    </p>
                </div>
                
                <!-- Stats -->
                <div class="stats">
                    <div class="stat">
                        <div class="stat-value">64%</div>
                        <div class="stat-label">Hit Rate</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">0%</div>
                        <div class="stat-label">False Positives</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">$85B</div>
                        <div class="stat-label">Deal Value Captured</div>
                    </div>
                </div>
                
                <p class="message">
                    <strong>What's coming in 2026:</strong>
                </p>
                
                <p class="message">
                    ✓ Daily automated scans across 200-600 biotech stocks<br>
                    ✓ Real-time alerts on high-conviction acquisition targets<br>
                    ✓ Systematic execution on proven M&A signals<br>
                    ✓ Target: 6-15 major deals captured throughout the year
                </p>
                
                <p class="closing">
                    Here's to a year of bold moves, calculated risks, and exceptional returns. The foundation is built. The system is ready. Now we execute.
                </p>
                
                <p class="closing">
                    Wishing you a prosperous and successful 2026. Let's make it unforgettable.
                </p>
                
                <!-- Signature -->
                <div class="signature">
                    <div class="signature-name">Jack Diemar</div>
                    <div class="signature-title">Black Starlight Capital</div>
                </div>
            </div>
            
            <!-- Footer -->
            <div class="footer">
                <div class="footer-logo">bsc</div>
                <div class="footer-text">
                    Black Starlight Capital<br>
                    M&A Intelligence Platform
                </div>
                <div class="footer-text">
                    <a href="mailto:{contact_email}" class="footer-link">{contact_email}</a>
                </div>
                <div class="footer-text" style="margin-top: 20px; font-size: 11px; color: #666666;">
                    © 2026 Black Starlight Capital. All rights reserved.
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html.replace("{contact_email}", SMTP_USERNAME)

def send_new_year_email(recipient_email):
    """Send New Year email to recipient"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Happy New Year from Black Starlight Capital 🎉"
        msg['From'] = f"Black Starlight Capital <{SMTP_USERNAME}>"
        msg['To'] = recipient_email
        
        html_content = create_new_year_email()
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"✓ New Year email sent to {recipient_email}")
        return True
        
    except Exception as e:
        print(f"✗ Error sending to {recipient_email}: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("BLACK STARLIGHT CAPITAL - NEW YEAR 2026 EMAIL")
    print("="*60 + "\n")
    
    print(f"Sending New Year greetings to {len(RECIPIENTS)} recipients...\n")
    
    success_count = 0
    for recipient in RECIPIENTS:
        if send_new_year_email(recipient):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"✓ Successfully sent {success_count}/{len(RECIPIENTS)} emails")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
