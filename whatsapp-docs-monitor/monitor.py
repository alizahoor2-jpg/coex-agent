#!/usr/bin/env python3
"""
WhatsApp Embedded Signup Docs Monitor - Detailed version
"""

import os
import json
import hashlib
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
SNAPSHOT_FILE = SCRIPT_DIR / "snapshots" / "onboarding-business-app-users.txt"
LOG_FILE = SCRIPT_DIR / "monitor.log"

URL = "https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-business-app-users/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def load_config():
    return {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender_email": "mohdalizahoor@gmail.com",
        "sender_password": "qlwb lerb nwom owna",
        "recipient_email": "mohdalizahoor@gmail.com"
    }

def fetch_page(url):
    try:
        import subprocess
        # Try curl first (better for bypassing blocks)
        try:
            result = subprocess.run([
                "curl", "-s", "-L", 
                "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                url
            ], capture_output=True, text=True, timeout=60)
if result.stdout and len(result.stdout) > 1000:
            text = result.stdout
            if "Sorry, something went wrong" not in text and "We're working on getting this fixed" not in text:
                return text, url
        except:
            pass
        
        # Fallback to requests
        session = requests.Session()
        r = session.get(url, headers=HEADERS, timeout=60)
        return r.text, r.url
    except Exception as e:
        log(f"Error: {e}")
        return None, url

def extract_content(html):
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    
    # Remove unwanted elements
    for s in soup(["script", "style", "nav", "footer", "header", "aside"]):
        s.decompose()
    
    # Get main content
    main = soup.find("article") or soup.find("main") or soup.find("div", {"role": "main"})
    if main:
        text = main.get_text(separator="\n", strip=True)
    else:
        text = soup.get_text(separator="\n", strip=True)
    
    # Filter to get meaningful content only
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        # Skip short lines and navigation items
        if len(line) > 20 and not line.startswith("#") and not line.startswith("http"):
            lines.append(line)
    
    return "\n".join(lines)

def get_hash(content):
    return hashlib.sha256(content.encode()).hexdigest()

def load_snapshot():
    if SNAPSHOT_FILE.exists():
        return SNAPSHOT_FILE.read_text()
    return None

def save_snapshot(content):
    SNAPSHOT_FILE.write_text(content)

def analyze_changes(old_content, new_content):
    old_lines = old_content.split("\n")
    new_lines = new_content.split("\n")
    
    old_set = set(old_lines)
    new_set = set(new_lines)
    
    added = [l for l in new_lines if l not in old_set]
    removed = [l for l in old_lines if l not in new_set]
    
    return added, removed

def send_email(subject, body, config):
    msg = MIMEMultipart()
    msg["From"] = config["sender_email"]
    msg["To"] = config["recipient_email"]
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
        server.starttls()
        server.login(config["sender_email"], config["sender_password"])
        server.sendmail(config["sender_email"], config["recipient_email"], msg.as_string())
        server.quit()
        log(f"Email sent: {subject}")
    except Exception as e:
        log(f"Email error: {e}")

def main():
    log("Starting monitor")
    config = load_config()
    
    html, url = fetch_page(URL)
    
    if not html:
        # Check if we have a previous snapshot
        old = load_snapshot()
        if old:
            send_email("Coex Updates - ERROR", "Could not fetch page (may be blocked). Will retry next run.", config)
        else:
            send_email("Coex Updates - ERROR", "Could not fetch page on first run.", config)
        return
    
    content = extract_content(html)
    
    # Check if we got meaningful content
    if len(content) < 500:
        send_email("Coex Updates - ERROR", f"Got empty/error page ({len(content)} chars). Page may be blocked.", config)
        return
    
    old_content = load_snapshot()
    new_hash = get_hash(content)
    
    if old_content is None:
        save_snapshot(content)
        send_email("Coex Updates - BASELINE SET", f"First run complete. {len(content)} chars saved.", config)
    else:
        old_hash = get_hash(old_content)
        if new_hash == old_hash:
            send_email("Coex Updates - NO CHANGES", "No changes detected in docs.", config)
        else:
            added, removed = analyze_changes(old_content, content)
            
            # Build detailed email with actual sentences
            body = []
            body.append("=" * 60)
            body.append("DOCS CHANGE DETECTED")
            body.append("=" * 60)
            body.append(f"Page: {URL}")
            body.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            body.append("")
            
            # Filter to get real content changes (sentences, not fragments)
            real_added = [l for l in added if len(l) > 30 and not l.isupper()]
            real_removed = [l for l in removed if len(l) > 30 and not l.isupper()]
            
            body.append(f"NEW sentences/paragraphs: {len(real_added)}")
            body.append(f"REMOVED sentences/paragraphs: {len(real_removed)}")
            body.append("")
            
            if real_added:
                body.append("--- NEW CONTENT ---")
                for line in real_added[:10]:
                    body.append(f"+ {line[:200]}")
                if len(real_added) > 10:
                    body.append(f"... and {len(real_added) - 10} more")
                body.append("")
            
            if real_removed:
                body.append("--- REMOVED CONTENT ---")
                for line in real_removed[:10]:
                    body.append(f"- {line[:200]}")
                if len(real_removed) > 10:
                    body.append(f"... and {len(real_removed) - 10} more")
                body.append("")
            
            body.append("=" * 60)
            
            send_email("Coex Updates", "\n".join(body), config)
            save_snapshot(content)
            
            # Push updated snapshot back to repo
            try:
                import subprocess
                subprocess.run(["git", "add", "snapshots/"], cwd=SCRIPT_DIR, capture_output=True)
                subprocess.run(["git", "commit", "-m", "Update snapshot"], cwd=SCRIPT_DIR, capture_output=True)
                subprocess.run(["git", "push"], cwd=SCRIPT_DIR, capture_output=True)
            except:
                pass
    
    log("Done.")

if __name__ == "__main__":
    main()