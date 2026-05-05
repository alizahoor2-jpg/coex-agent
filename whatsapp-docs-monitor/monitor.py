#!/usr/bin/env python3
"""
WhatsApp Docs Monitor - Checks for changes and emails detailed report
"""

import os
import hashlib
import smtplib
import subprocess
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
STORAGE_FILE = SCRIPT_DIR / "stored_page.txt"
LOG_FILE = SCRIPT_DIR / "monitor.log"

URL = "https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-business-app-users/"

EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender": "mohdalizahoor@gmail.com",
    "password": "qlwb lerb nwom owna",
    "recipient": "mohdalizahoor@gmail.com"
}

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}] {msg}\n")

def fetch_page(url):
    """Fetch the page using curl with iPhone user-agent"""
    try:
        result = subprocess.run([
            "curl", "-s", "-L",
            "-A", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            url
        ], capture_output=True, text=True, timeout=60)
        
        text = result.stdout
        if not text or len(text) < 1000:
            return None
        if "Sorry, something went wrong" in text or "We're working on getting this fixed" in text:
            return None
        return text
    except Exception as e:
        log(f"Fetch error: {e}")
        return None

def extract_text(html):
    """Extract clean text content from HTML"""
    if not html:
        return ""
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Remove unwanted elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    
    # Get main content
    main = soup.find("article") or soup.find("main") or soup.find("div", {"role": "main"})
    if main:
        text = main.get_text(separator="\n", strip=True)
    else:
        text = soup.get_text(separator="\n", strip=True)
    
    # Filter to meaningful lines (sentences, not fragments)
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if len(line) > 10:  # At least 10 chars
            lines.append(line)
    
    return "\n".join(lines)

def get_hash(content):
    return hashlib.sha256(content.encode()).hexdigest()

def load_stored():
    if STORAGE_FILE.exists():
        return STORAGE_FILE.read_text()
    return None

def save_stored(content):
    STORAGE_FILE.write_text(content)

def find_changes(old_text, new_text):
    """Find exact lines added and removed"""
    old_lines = old_text.split("\n")
    new_lines = new_text.split("\n")
    
    old_set = set(old_lines)
    new_set = set(new_lines)
    
    added = [line for line in new_lines if line not in old_set]
    removed = [line for line in old_lines if line not in new_set]
    
    return added, removed

def send_email(subject, body):
    """Send email"""
    msg = MIMEMultipart()
    msg["From"] = EMAIL_CONFIG["sender"]
    msg["To"] = EMAIL_CONFIG["recipient"]
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))
    
    try:
        server = smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"])
        server.starttls()
        server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
        server.sendmail(EMAIL_CONFIG["sender"], EMAIL_CONFIG["recipient"], msg.as_string())
        server.quit()
        log(f"Email sent: {subject}")
    except Exception as e:
        log(f"Email error: {e}")

def main():
    log("=" * 50)
    log("Checking page for changes...")
    
    # Fetch current page
    html = fetch_page(URL)
    if not html:
        send_email("Coex Updates - ERROR", "Could not fetch page. It may be blocked.")
        log("Failed to fetch page")
        return
    
    # Extract text
    current_text = extract_text(html)
    if len(current_text) < 500:
        send_email("Coex Updates - ERROR", f"Page too short ({len(current_text)} chars). May be blocked.")
        log(f"Page too short: {len(current_text)}")
        return
    
    # Load stored version
    stored_text = load_stored()
    
    if stored_text is None:
        # First run - store and notify
        save_stored(current_text)
        send_email("Coex Updates - BASELINE SET", f"Monitoring started.\n\nPage saved: {len(current_text)} chars.")
        log(f"Baseline saved: {len(current_text)} chars")
        return
    
    # Compare
    if current_text == stored_text:
        send_email("Coex Updates - NO CHANGES", f"No changes detected.\n\nPage: {URL}")
        log("No changes")
    else:
        # Find what changed
        added, removed = find_changes(stored_text, current_text)
        
        # Build detailed email
        email_body = []
        email_body.append("=" * 50)
        email_body.append("DOCS CHANGED")
        email_body.append("=" * 50)
        email_body.append(f"Page: {URL}")
        email_body.append("")
        
        # Added content
        if added:
            email_body.append(f"NEW CONTENT ({len(added)} items added):")
            email_body.append("-" * 40)
            for line in added[:15]:
                if len(line) > 0:
                    email_body.append(f"+ {line[:200]}")
            if len(added) > 15:
                email_body.append(f"... and {len(added) - 15} more")
            email_body.append("")
        
        # Removed content
        if removed:
            email_body.append(f"REMOVED CONTENT ({len(removed)} items removed):")
            email_body.append("-" * 40)
            for line in removed[:15]:
                if len(line) > 0:
                    email_body.append(f"- {line[:200]}")
            if len(removed) > 15:
                email_body.append(f"... and {len(removed) - 15} more")
            email_body.append("")
        
        email_body.append("=" * 50)
        
        send_email("Coex Updates - CHANGES FOUND", "\n".join(email_body))
        
        # Save new version
        save_stored(current_text)
        log(f"Changes: {len(added)} added, {len(removed)} removed")
    
    log("Done")

if __name__ == "__main__":
    main()