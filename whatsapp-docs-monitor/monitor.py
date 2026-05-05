#!/usr/bin/env python3
"""
WhatsApp Embedded Signup Docs Monitor - Simple version
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
LAST_HASH_FILE = SCRIPT_DIR / "last_hash.txt"
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

def load_last_hash():
    if LAST_HASH_FILE.exists():
        return LAST_HASH_FILE.read_text().strip()
    return None

def save_last_hash(h):
    LAST_HASH_FILE.write_text(h)

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
    new_hash = get_hash(content)
    last_hash = load_last_hash()
    
    if last_hash is None:
        save_last_hash(new_hash)
        log("Baseline saved.")
    elif new_hash == last_hash:
        send_email("Coex Updates - NO CHANGES", "No changes detected.", config)
    else:
        send_email("Coex Updates", "Changes detected in docs.", config)
        save_last_hash(new_hash)
    
    log("Done.")

if __name__ == "__main__":
    main()