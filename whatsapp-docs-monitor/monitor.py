#!/usr/bin/env python3
"""
WhatsApp Embedded Signup Docs Monitor - Detailed version
"""

import os
import json
import hashlib
import smtplib
import difflib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
SNAPSHOT_FILE = SCRIPT_DIR / "previous_snapshot.txt"
LOG_FILE = SCRIPT_DIR / "monitor.log"

URL = "https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-business-app-users/"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"}

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
        r = requests.get(url, headers=HEADERS, timeout=30)
        return r.text, r.url
    except Exception as e:
        log(f"Error: {e}")
        return None, url

def extract_content(html):
    soup = BeautifulSoup(html, "html.parser")
    for s in soup(["script", "style", "nav", "footer", "header"]):
        s.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return "\n".join(l.strip() for l in text.split("\n") if l.strip())

def get_hash(content):
    return hashlib.sha256(content.encode()).hexdigest()

def load_snapshot():
    if SNAPSHOT_FILE.exists():
        return SNAPSHOT_FILE.read_text()
    return None

def save_snapshot(content):
    SNAPSHOT_FILE.write_text(content)

def diff_content(old_content, new_content):
    old_lines = old_content.split("\n")
    new_lines = new_content.split("\n")
    
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm="", n=3))
    return "\n".join(diff)

def analyze_changes(old_content, new_content):
    old_lines = set(old_content.split("\n"))
    new_lines = set(new_content.split("\n"))
    
    added = new_lines - old_lines
    removed = old_lines - new_lines
    
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
        send_email("Coex Updates - ERROR", "Could not fetch page", config)
        return
    
    content = extract_content(html)
    old_content = load_snapshot()
    new_hash = get_hash(content)
    
    if old_content is None:
        save_snapshot(content)
        send_email("Coex Updates - BASELINE SET", "First run complete. Monitoring started.", config)
    else:
        old_hash = get_hash(old_content)
        if new_hash == old_hash:
            send_email("Coex Updates - NO CHANGES", "No changes detected in docs.", config)
        else:
            # Get detailed changes
            added_lines, removed_lines = analyze_changes(old_content, content)
            
            # Build detailed email
            body = []
            body.append("=" * 50)
            body.append("DOCS CHANGE DETECTED")
            body.append("=" * 50)
            body.append(f"URL: {URL}")
            body.append("")
            body.append(f"Lines added: {len(added_lines)}")
            body.append(f"Lines removed: {len(removed_lines)}")
            body.append("")
            
            if added_lines:
                body.append("--- NEW LINES ---")
                for line in sorted(added_lines)[:20]:
                    body.append(f"+ {line}")
                if len(added_lines) > 20:
                    body.append(f"... and {len(added_lines) - 20} more")
                body.append("")
            
            if removed_lines:
                body.append("--- REMOVED LINES ---")
                for line in sorted(removed_lines)[:20]:
                    body.append(f"- {line}")
                if len(removed_lines) > 20:
                    body.append(f"... and {len(removed_lines) - 20} more")
                body.append("")
            
            body.append("=" * 50)
            
            send_email("Coex Updates", "\n".join(body), config)
            save_snapshot(content)
            
            # Push updated snapshot back to repo
            try:
                import subprocess
                subprocess.run(["git", "add", "previous_snapshot.txt"], cwd=SCRIPT_DIR, capture_output=True)
                subprocess.run(["git", "commit", "-m", "Update snapshot"], cwd=SCRIPT_DIR, capture_output=True)
                subprocess.run(["git", "push"], cwd=SCRIPT_DIR, capture_output=True)
            except:
                pass
    
    log("Done.")

if __name__ == "__main__":
    main()