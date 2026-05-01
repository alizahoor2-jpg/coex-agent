#!/usr/bin/env python3
"""
WhatsApp Embedded Signup Documentation Monitor
Fetches all official Meta/WhatsApp Embedded Signup documentation pages,
compares against previous snapshots, and emails detailed change reports.
"""

import os
import sys
import json
import time
import hashlib
import difflib
import smtplib
import requests
import subprocess
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent.resolve()
SNAPSHOTS_DIR = SCRIPT_DIR / "snapshots"
LOG_FILE = SCRIPT_DIR / "monitor.log"
CONFIG_FILE = SCRIPT_DIR / "config.json"  # Kept for reference, not used

# All WhatsApp Embedded Signup documentation URLs to monitor
URLS = [
    # Main Embedded Signup pages
    {
        "url": "https://developers.facebook.com/docs/whatsapp/embedded-signup/",
        "name": "Embedded Signup - Overview",
        "slug": "embedded-signup-overview",
    },
    {
        "url": "https://developers.facebook.com/docs/whatsapp/embedded-signup/implementation/",
        "name": "Embedded Signup - Implementation",
        "slug": "implementation",
    },
    {
        "url": "https://developers.facebook.com/docs/whatsapp/embedded-signup/custom-flows/",
        "name": "Customizing the default flow",
        "slug": "custom-flows",
    },
    {
        "url": "https://developers.facebook.com/docs/whatsapp/embedded-signup/custom-flows/onboarding-business-app-users/",
        "name": "Onboard WhatsApp Business app users (Coexistence)",
        "slug": "onboarding-business-app-users",
    },
    {
        "url": "https://developers.facebook.com/docs/whatsapp/embedded-signup/pre-filled-data/",
        "name": "Pre-filling screens",
        "slug": "pre-filled-data",
    },
    {
        "url": "https://developers.facebook.com/docs/whatsapp/embedded-signup/pre-verified-numbers/",
        "name": "Pre-verified phone numbers",
        "slug": "pre-verified-numbers",
    },
    {
        "url": "https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/bypass-phone-addition/",
        "name": "Bypassing phone number screens",
        "slug": "bypass-phone-addition",
    },
    {
        "url": "https://developers.facebook.com/docs/whatsapp/embedded-signup/custom-flows/website-optional/",
        "name": "Making website optional",
        "slug": "making-website-optional",
    },
    {
        "url": "https://developers.facebook.com/docs/whatsapp/embedded-signup/custom-flows/app-only-install/",
        "name": "App-only install",
        "slug": "app-only-install",
    },
    {
        "url": "https://developers.facebook.com/docs/whatsapp/embedded-signup/hosted-es/",
        "name": "Hosted ES",
        "slug": "hosted-es",
    },
    {
        "url": "https://developers.facebook.com/docs/whatsapp/embedded-signup/automatic-events-api/",
        "name": "Automatic Events API",
        "slug": "automatic-events-api",
    },
    # Onboarding customers
    {
        "url": "https://developers.facebook.com/docs/whatsapp/embedded-signup/onboarding-customers-as-a-tech-provider/",
        "name": "Onboarding customers as a Tech Provider",
        "slug": "onboarding-tech-provider",
    },
    {
        "url": "https://developers.facebook.com/docs/whatsapp/embedded-signup/onboarding-customers-as-a-solution-partner/",
        "name": "Onboarding customers as a Solution Partner",
        "slug": "onboarding-solution-partner",
    },
    # Versions
    {
        "url": "https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/version-4/",
        "name": "Version 4",
        "slug": "version-4",
    },
    # Errors
    {
        "url": "https://developers.facebook.com/docs/whatsapp/embedded-signup/errors/",
        "name": "Embedded Signup Errors",
        "slug": "errors",
    },
    # Multi-Partner Solutions
    {
        "url": "https://developers.facebook.com/docs/whatsapp/solution-providers/multi-partner-solutions/",
        "name": "Multi-Partner Solutions Overview",
        "slug": "multi-partner-solutions-overview",
    },
    {
        "url": "https://developers.facebook.com/docs/whatsapp/solution-providers/support/migrating-wabas-among-solutions-via-embedded-signup",
        "name": "Migrate WABAs among solutions via Embedded Signup",
        "slug": "migrate-wabas-solutions-embedded",
    },
    {
        "url": "https://developers.facebook.com/docs/whatsapp/solution-providers/support/migrating-wabas-among-solution-partners-via-embedded-signup/",
        "name": "Migrate WABAs among partners via Embedded Signup",
        "slug": "migrate-wabas-partners-embedded",
    },
    {
        "url": "https://developers.facebook.com/docs/whatsapp/solution-providers/support/migrating-customers-off-solutions-via-embedded-signup/",
        "name": "Migrating customers off solutions via Embedded Signup",
        "slug": "migrate-off-solutions-embedded",
    },
    {
        "url": "https://developers.facebook.com/docs/whatsapp/solution-providers/support/adding-waba-to-mps/",
        "name": "Add WABAs to a Multi-Partner Solution",
        "slug": "add-wabas-multi-partner",
    },
    # Partner-led business verification
    {
        "url": "https://developers.facebook.com/docs/whatsapp/solution-providers/partner-led-business-verification/",
        "name": "Partner-led business verification",
        "slug": "partner-led-business-verification",
    },
    # Partner-initiated WABA creation
    {
        "url": "https://developers.facebook.com/docs/whatsapp/solution-providers/partner-initiated-waba-creation/",
        "name": "Partner-initiated WABA creation",
        "slug": "partner-initiated-waba-creation",
    },
    # Pixel tracking
    {
        "url": "https://developers.facebook.com/docs/whatsapp/embedded-signup/pixel-tracking/",
        "name": "Pixel tracking",
        "slug": "pixel-tracking",
    },
]

# Browser-like headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def load_config():
    """Load configuration - hardcoded for GitHub Actions."""
    return {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender_email": "mohdalizahoor@gmail.com",
        "sender_password": "qlwb lerb nwom owna",
        "recipient_email": "mohdalizahoor@gmail.com"
    }


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def fetch_page(url):
    """Fetch a page and return the HTML content."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        response.raise_for_status()
        return response.text, response.url
    except requests.RequestException as e:
        log(f"ERROR fetching {url}: {e}")
        return None, url


def extract_content(html, url):
    """Extract clean text content from HTML page."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.decompose()

    # Try to get the main article/content area
    content_div = soup.find("article") or soup.find("main") or soup.find("div", class_="content") or soup.find("body")

    if content_div:
        text = content_div.get_text(separator="\n", strip=True)
    else:
        text = soup.get_text(separator="\n", strip=True)

    # Clean up: remove empty lines, normalize whitespace
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if line:
            lines.append(line)

    content = "\n".join(lines)
    return content


def get_content_hash(content):
    """Get SHA256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def save_snapshot(slug, content, final_url):
    """Save content snapshot to file."""
    snapshot_path = SNAPSHOTS_DIR / f"{slug}.txt"
    meta_path = SNAPSHOTS_DIR / f"{slug}.meta.json"

    with open(snapshot_path, "w", encoding="utf-8") as f:
        f.write(content)

    meta = {
        "slug": slug,
        "url": final_url,
        "content_hash": get_content_hash(content),
        "line_count": len(content.split("\n")),
        "char_count": len(content),
        "word_count": len(content.split()),
        "last_updated": datetime.now().isoformat(),
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return meta


def load_snapshot(slug):
    """Load previous snapshot if it exists."""
    snapshot_path = SNAPSHOTS_DIR / f"{slug}.txt"
    meta_path = SNAPSHOTS_DIR / f"{slug}.meta.json"

    if snapshot_path.exists() and meta_path.exists():
        with open(snapshot_path, "r", encoding="utf-8") as f:
            content = f.read()
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        return content, meta
    return None, None


def generate_unified_diff(old_content, new_content, from_name="Previous", to_name="Current", context=3):
    """Generate a detailed unified diff between old and new content."""
    old_lines = old_content.split("\n")
    new_lines = new_content.split("\n")

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=from_name,
        tofile=to_name,
        lineterm="",
        n=context,
    )
    return "\n".join(diff)


def analyze_changes(old_content, new_content, page_name, url):
    """Analyze changes between old and new content in detail."""
    old_lines = old_content.split("\n")
    new_lines = new_content.split("\n")

    changes = []

    # Use difflib for detailed comparison
    diff = list(difflib.SequenceMatcher(None, old_lines, new_lines).get_opcodes())

    for tag, i1, i2, j1, j2 in diff:
        if tag == "equal":
            continue
        elif tag == "replace":
            for idx, line in enumerate(old_lines[i1:i2]):
                changes.append({
                    "type": "REMOVED",
                    "old_line": i1 + idx + 1,
                    "text": line,
                })
            for idx, line in enumerate(new_lines[j1:j2]):
                changes.append({
                    "type": "ADDED",
                    "new_line": j1 + idx + 1,
                    "text": line,
                })
        elif tag == "delete":
            for idx, line in enumerate(old_lines[i1:i2]):
                changes.append({
                    "type": "REMOVED",
                    "old_line": i1 + idx + 1,
                    "text": line,
                })
        elif tag == "insert":
            for idx, line in enumerate(new_lines[j1:j2]):
                changes.append({
                    "type": "ADDED",
                    "new_line": j1 + idx + 1,
                    "text": line,
                })

    return changes


def build_email_body(all_changes, new_pages, removed_pages):
    """Build detailed email body with ALL changes shown explicitly."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")

    body = []
    body.append("=" * 80)
    body.append("WhatsApp Embedded Signup Docs - DETAILED CHANGE REPORT")
    body.append("=" * 80)
    body.append("")
    body.append(f"Checked: {now}")
    body.append(f"Total pages monitored: {len(URLS)}")
    body.append(f"New pages found: {len(new_pages)}")
    body.append(f"Pages removed: {len(removed_pages)}")
    body.append(f"Pages with changes: {len(all_changes)}")
    body.append("")

    # Summary of changes
    total_added = 0
    total_removed = 0
    for page_changes in all_changes.values():
        for change in page_changes["changes"]:
            if change["type"] == "ADDED":
                total_added += 1
            elif change["type"] == "REMOVED":
                total_removed += 1

    body.append("-" * 80)
    body.append("SUMMARY")
    body.append("-" * 80)
    body.append(f"  Total lines ADDED across all pages: {total_added}")
    body.append(f"  Total lines REMOVED across all pages: {total_removed}")
    body.append("")

    # NEW PAGES
    if new_pages:
        body.append("=" * 80)
        body.append("🆕 NEW PAGES DISCOVERED")
        body.append("=" * 80)
        body.append("")
        for page in new_pages:
            body.append(f"  NAME: {page['name']}")
            body.append(f"  URL: {page['url']}")
            body.append(f"  Lines: {page['line_count']}")
            body.append(f"  Words: {page['word_count']}")
            body.append(f"  Characters: {page['char_count']}")
            body.append("")
            body.append("  [FULL CONTENT OF NEW PAGE]")
            body.append("  " + "-" * 76)
            for line in page["content"].split("\n")[:200]:
                body.append(f"  | {line}")
            body.append("  " + "-" * 76)
            body.append("")

    # REMOVED PAGES
    if removed_pages:
        body.append("=" * 80)
        body.append("❌ PAGES REMOVED (404 or inaccessible)")
        body.append("=" * 80)
        body.append("")
        for page in removed_pages:
            body.append(f"  NAME: {page['name']}")
            body.append(f"  URL: {page['url']}")
            body.append(f"  Was last seen: {page.get('last_updated', 'unknown')}")
            body.append("")

    # DETAILED CHANGES PER PAGE
    if all_changes:
        body.append("=" * 80)
        body.append("📝 DETAILED CHANGES BY PAGE")
        body.append("=" * 80)
        body.append("")

        for page_name, data in all_changes.items():
            body.append("-" * 80)
            body.append(f"PAGE: {page_name}")
            body.append(f"URL: {data['url']}")
            body.append(f"Size: {data['old_meta']['char_count']} → {data['new_meta']['char_count']} characters ({data['new_meta']['char_count'] - data['old_meta']['char_count']:+d})")
            body.append(f"Words: {data['old_meta']['word_count']} → {data['new_meta']['word_count']} ({data['new_meta']['word_count'] - data['old_meta']['word_count']:+d})")
            body.append(f"Lines: {data['old_meta']['line_count']} → {data['new_meta']['line_count']} ({data['new_meta']['line_count'] - data['old_meta']['line_count']:+d})")
            body.append("")

            page_changes = data["changes"]
            added = [c for c in page_changes if c["type"] == "ADDED"]
            removed = [c for c in page_changes if c["type"] == "REMOVED"]

            body.append(f"  Lines added: {len(added)}")
            body.append(f"  Lines removed: {len(removed)}")
            body.append("")

            # Group changes by context (consecutive changes)
            body.append("  EXACT CHANGES:")
            body.append("  " + "=" * 74)

            # Show additions and removals with context
            old_lines = data["old_content"].split("\n")
            new_lines = data["new_content"].split("\n")

            # Show REMOVED lines
            if removed:
                body.append("")
                body.append("  --- REMOVED (was in previous version) ---")
                body.append("")
                for change in removed:
                    body.append(f"  Line {change['old_line']} (OLD):")
                    body.append(f"    ❌ {change['text']}")
                    body.append("")

            # Show ADDED lines
            if added:
                body.append("")
                body.append("  +++ ADDED (new in current version) +++")
                body.append("")
                for change in added:
                    body.append(f"  Line {change['new_line']} (NEW):")
                    body.append(f"    ✅ {change['text']}")
                    body.append("")

            # Also provide a unified diff view
            body.append("")
            body.append("  UNIFIED DIFF VIEW:")
            body.append("  " + "=" * 74)
            unified_diff = generate_unified_diff(
                data["old_content"],
                data["new_content"],
                from_name="Previous version",
                to_name="Current version",
                context=5,
            )
            for line in unified_diff.split("\n"):
                if line.startswith("---") or line.startswith("+++"):
                    body.append(f"  {line}")
                elif line.startswith("@@"):
                    body.append(f"  {line}")
                elif line.startswith("+"):
                    body.append(f"  + {line[1:]}")
                elif line.startswith("-"):
                    body.append(f"  - {line[1:]}")
                elif line.startswith(" "):
                    body.append(f"    {line[1:]}")
            body.append("")
            body.append("")

    if not all_changes and not new_pages and not removed_pages:
        body.append("NO CHANGES DETECTED - All pages are identical to previous snapshots.")
        body.append("")

    body.append("=" * 80)
    body.append("End of report")
    body.append("=" * 80)

    return "\n".join(body)


def send_email(subject, body, config):
    """Send email via SMTP."""
    msg = MIMEMultipart()
    msg["From"] = config["sender_email"]
    msg["To"] = config["recipient_email"]
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
        server.starttls()
        server.login(config["sender_email"], config["sender_password"])
        text = msg.as_string()
        server.sendmail(config["sender_email"], config["recipient_email"], text)
        server.quit()
        log(f"Email sent successfully to {config['recipient_email']}")
        return True
    except Exception as e:
        log(f"ERROR sending email: {e}")
        return False


def main():
    log("=" * 60)
    log("Starting WhatsApp Embedded Signup Docs Monitor")
    log("=" * 60)

    config = load_config()
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    # Check if this is the first run (no snapshots exist yet)
    existing_snapshots = list(SNAPSHOTS_DIR.glob("*.txt"))
    is_first_run = len(existing_snapshots) == 0

    all_changes = {}
    new_pages = []
    removed_pages = []
    errors = []

    for i, page_info in enumerate(URLS):
        url = page_info["url"]
        name = page_info["name"]
        slug = page_info["slug"]

        log(f"[{i+1}/{len(URLS)}] Fetching: {name}")

        # Load old snapshot BEFORE fetching
        old_content, old_meta = load_snapshot(slug)

        # Fetch the page
        html, final_url = fetch_page(url)
        if html is None:
            if old_meta:
                removed_pages.append({
                    "name": name,
                    "url": url,
                    "last_updated": old_meta.get("last_updated", "unknown"),
                })
                log(f"  REMOVED: {name} (was previously tracked)")
            else:
                errors.append({"name": name, "url": url, "error": "Failed to fetch"})
                log(f"  ERROR: Could not fetch {name}")
            continue

        # Extract content
        content = extract_content(html, final_url)
        if not content:
            errors.append({"name": name, "url": url, "error": "No content extracted"})
            continue

        # Calculate hash of new content
        new_hash = get_content_hash(content)

        # Save new snapshot
        new_meta = save_snapshot(slug, content, final_url)

        if old_content is None:
            # This is a new page (first time seeing it)
            new_pages.append({
                "name": name,
                "url": final_url,
                "content": content,
                "line_count": new_meta["line_count"],
                "word_count": new_meta["word_count"],
                "char_count": new_meta["char_count"],
            })
            log(f"  NEW PAGE: {name} ({new_meta['line_count']} lines)")
        elif old_meta["content_hash"] == new_hash:
            log(f"  UNCHANGED: {name}")
        else:
            # Content has changed - analyze in detail
            changes = analyze_changes(old_content, content, name, final_url)
            all_changes[name] = {
                "url": final_url,
                "changes": changes,
                "old_content": old_content,
                "new_content": content,
                "old_meta": old_meta,
                "new_meta": new_meta,
            }
            log(f"  CHANGED: {name} ({len(changes)} changes detected)")

    # Build email
    has_changes = len(all_changes) > 0 or len(new_pages) > 0 or len(removed_pages) > 0

    if is_first_run:
        log("FIRST RUN: Baseline snapshots saved. No email sent.")
        log("Subsequent runs will detect and report changes.")
    elif has_changes:
        subject = f"WhatsApp Docs CHANGES: {len(all_changes)} updated, {len(new_pages)} new, {len(removed_pages)} removed"
        body = build_email_body(all_changes, new_pages, removed_pages)
        send_email(subject, body, config)
    else:
        log("No changes detected. No email sent.")

    # Summary
    log("")
    log("=" * 60)
    log(f"Monitoring complete:")
    log(f"  Pages checked: {len(URLS)}")
    log(f"  Pages changed: {len(all_changes)}")
    log(f"  New pages: {len(new_pages)}")
    log(f"  Removed pages: {len(removed_pages)}")
    log(f"  Errors: {len(errors)}")
    log("=" * 60)


if __name__ == "__main__":
    main()
