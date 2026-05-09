#!/usr/bin/env python3
"""
BSC MLK Day Announcement
Official notice to stakeholders
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

def create_mlk_email():
    """Create formal MLK Day announcement"""
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {
                font-family: Georgia, 'Times New Roman', serif;
                line-height: 1.8;
                color: #1a1a1a;
                max-width: 600px;
                margin: 0 auto;
                padding: 40px 20px;
                background: #ffffff;
            }
            .header {
                text-align: center;
                padding-bottom: 30px;
                margin-bottom: 40px;
                border-bottom: 2px solid #1a1a1a;
            }
            .logo {
                font-size: 28px;
                font-weight: 700;
                color: #1a1a1a;
                letter-spacing: 1px;
                margin-bottom: 8px;
            }
            .date {
                font-size: 11px;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 2px;
                margin-top: 15px;
            }
            .salutation {
                margin: 30px 0 25px 0;
                font-size: 15px;
            }
            .body-text {
                font-size: 15px;
                margin: 20px 0;
                text-align: justify;
            }
            .quote {
                margin: 35px 0;
                padding: 25px;
                background: #f8f8f8;
                border-left: 4px solid #1a1a1a;
                font-style: italic;
                font-size: 16px;
                line-height: 1.6;
            }
            .quote-author {
                text-align: right;
                font-style: normal;
                font-weight: 600;
                margin-top: 15px;
                font-size: 14px;
            }
            .closing {
                margin-top: 40px;
                font-size: 15px;
            }
            .signature {
                margin-top: 35px;
                font-size: 15px;
            }
            .signature-name {
                font-weight: 600;
                margin-bottom: 3px;
            }
            .signature-title {
                color: #666;
                font-size: 13px;
            }
            .footer {
                margin-top: 50px;
                padding-top: 25px;
                border-top: 1px solid #e0e0e0;
                text-align: center;
                font-size: 11px;
                color: #999;
                letter-spacing: 1px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo">BLACK STARLIGHT CAPITAL</div>
            <div class="date">JANUARY 20, 2026</div>
        </div>
        
        <div class="salutation">
            Dear Colleagues and Partners,
        </div>
        
        <p class="body-text">
            On this Martin Luther King Jr. Day, Black Starlight Capital observes a day of reflection 
            in honor of Dr. King's enduring legacy and his unwavering commitment to justice, equality, 
            and the advancement of opportunity for all Americans.
        </p>
        
        <p class="body-text">
            Dr. King's vision extended beyond the immediate struggles of his time. He understood that 
            economic empowerment and financial literacy were essential components of true equality. 
            His advocacy for economic justice reminds us that markets, capital, and opportunity must 
            be accessible to all who seek to participate in the American economic system.
        </p>
        
        <div class="quote">
            "The ultimate measure of a man is not where he stands in moments of comfort and convenience, 
            but where he stands at times of challenge and controversy."
            <div class="quote-author">— Dr. Martin Luther King Jr.</div>
        </div>
        
        <p class="body-text">
            In recognition of this federal holiday, our operations will observe standard market closures. 
            Regular communications and analytical updates will resume on Tuesday, January 21st, 2026.
        </p>
        
        <p class="body-text">
            We encourage each of you to take this day to reflect on Dr. King's contributions to our 
            nation and to consider how we might each contribute to the ongoing work of building a 
            more equitable society.
        </p>
        
        <div class="closing">
            With respect and appreciation,
        </div>
        
        <div class="signature">
            <div class="signature-name">Black Starlight Capital</div>
            <div class="signature-title">Quantitative Research Division</div>
        </div>
        
        <div class="footer">
            BLACK STARLIGHT CAPITAL · PROPRIETARY M&A INTELLIGENCE
        </div>
    </body>
    </html>
    """
    
    return html

def send_mlk_announcement():
    """Send MLK Day announcement to all recipients"""
    
    subject = "Observance of Martin Luther King Jr. Day"
    html_body = create_mlk_email()
    
    print("="*70)
    print("SENDING MLK DAY ANNOUNCEMENT")
    print("="*70)
    print()
    
    success_count = 0
    failed = []
    
    for recipient in RECIPIENTS:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = SMTP_USERNAME
            msg['To'] = recipient
            
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
            
            print(f"✓ Sent to {recipient}")
            success_count += 1
            
        except Exception as e:
            print(f"✗ Failed to send to {recipient}: {str(e)[:50]}")
            failed.append(recipient)
    
    print()
    print("="*70)
    print(f"SUMMARY: {success_count}/{len(RECIPIENTS)} sent successfully")
    if failed:
        print(f"Failed: {', '.join(failed)}")
    print("="*70)

if __name__ == "__main__":
    send_mlk_announcement()
