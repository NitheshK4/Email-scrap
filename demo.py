"""
demo.py — Interactive Demo Script

Demonstrates all major use-cases of the Email Scraper project:
  1. Single page scraping
  2. Recursive crawling
  3. Email validation
  4. Suppression list
  5. Multi-format export
  6. Compliance audit log

Run:  python demo.py
"""

import logging
import sys
from pathlib import Path

# Make sure output dir exists
Path("output").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)

from email_scraper.scraper import EmailScraper
from email_scraper.validator import EmailValidator, extract_emails_from_text
from email_scraper.exporter import DataExporter
from email_scraper.compliance import (
    SuppressionList, AuditLogger, ComplianceChecker, COMPLIANCE_NOTICE
)

print(COMPLIANCE_NOTICE)

# =============================================================
# DEMO 1 — Email Validation
# =============================================================
print("\n" + "─"*55)
print("  DEMO 1: EMAIL VALIDATION")
print("─"*55)

test_emails = [
    "john.doe@example.com",
    "not-an-email",
    "admin@mailinator.com",   # disposable
    "info@google.com",        # role-based
    "real.user@github.com",
    "bad@",
    "contact@python.org",
]

validator = EmailValidator(check_mx=False)
for email in test_emails:
    result = validator.validate(email)
    status = "✅ VALID  " if result.is_valid else "❌ INVALID"
    flags = []
    if result.is_disposable:
        flags.append("DISPOSABLE")
    if result.is_role_based:
        flags.append("ROLE-BASED")
    flag_str = f" [{', '.join(flags)}]" if flags else ""
    print(f"  {status} | Score: {result.score:3d} | {email}{flag_str}")
    if not result.is_valid:
        print(f"             Reason: {result.reason}")

# =============================================================
# DEMO 2 — Extract Emails from Raw Text
# =============================================================
print("\n" + "─"*55)
print("  DEMO 2: EXTRACT EMAILS FROM RAW TEXT")
print("─"*55)

sample_html = """
<html><body>
  <p>For sales, contact us at sales@acme.com or support@acme.com</p>
  <p>CEO: jane.smith@acme.com | CTO: bob.jones@acme.com</p>
  <a href="mailto:careers@acme.com">Apply here</a>
  <p>Invalid: not@@valid | missing@</p>
</body></html>
"""

found = extract_emails_from_text(sample_html)
print(f"  Found {len(found)} candidate email(s) in raw text:")
for e in found:
    print(f"    • {e}")

# =============================================================
# DEMO 3 — Scrape a Real Public Page (books.toscrape.com)
# =============================================================
print("\n" + "─"*55)
print("  DEMO 3: SCRAPE A REAL PUBLIC PAGE")
print("─"*55)
print("  Target: https://books.toscrape.com (a legal scraping sandbox)")
print("  Note: This site may have no email addresses (it's a book demo),")
print("        but validates the full pipeline including robots.txt check.\n")

scraper = EmailScraper(validate_emails=True, check_robots=True, delay=(0.5, 1.0))
audit   = AuditLogger()

demo_url = "https://books.toscrape.com"
audit.log_scrape_start(demo_url, purpose="demo_scrape")
contacts = scraper.scrape_url(demo_url)
audit.log_scrape_end(demo_url, len(contacts))

if contacts:
    print(f"  Found {len(contacts)} email(s):")
    for c in contacts:
        print(f"    • {c.email} (source: {c.source_url})")
else:
    print("  No emails found on this page (expected — it is a book demo site).")
    print("  The pipeline (fetch → parse → validate → deduplicate) worked correctly.")

# =============================================================
# DEMO 4 — Suppression List
# =============================================================
print("\n" + "─"*55)
print("  DEMO 4: SUPPRESSION LIST (OPT-OUTS)")
print("─"*55)

suppression = SuppressionList(filepath="output/suppression_list.txt")
suppression.add("optout@example.com")
suppression.add("donotcontact@example.com")
print(f"  Suppression list now has {suppression.count} email(s).")
print(f"  Is 'optout@example.com' suppressed? {suppression.is_suppressed('optout@example.com')}")
print(f"  Is 'real@example.com' suppressed?   {suppression.is_suppressed('real@example.com')}")

# =============================================================
# DEMO 5 — Compliance Check on a Sample HTML Page
# =============================================================
print("\n" + "─"*55)
print("  DEMO 5: COMPLIANCE CHECKER")
print("─"*55)

checker = ComplianceChecker()

page_with_policy = """
<html><body>
  <a href="/privacy-policy">Privacy Policy</a>
  <p>We comply with GDPR and allow opt-out at any time.</p>
</body></html>
"""
page_without_policy = "<html><body><p>Buy our products!</p></body></html>"

result_a = checker.check_page(page_with_policy, "https://example.com/contact")
result_b = checker.check_page(page_without_policy, "https://spammy-site.com")

print(f"  Page A — has_privacy_policy: {result_a['has_privacy_policy']} | tos_restricted: {result_a['tos_restricted']}")
print(f"  Page B — has_privacy_policy: {result_b['has_privacy_policy']} | tos_restricted: {result_b['tos_restricted']}")
if result_b["warnings"]:
    print(f"  ⚠️  Warning: {result_b['warnings'][0]}")

# =============================================================
# DEMO 6 — Export (using synthetic contacts)
# =============================================================
print("\n" + "─"*55)
print("  DEMO 6: DATA EXPORT (CSV + JSON)")
print("─"*55)

from email_scraper.scraper import ScrapedContact
from datetime import datetime

synthetic_contacts = [
    ScrapedContact(
        email="alice@startup.io",
        source_url="https://startup.io/team",
        name_hint="Alice Johnson — Head of Marketing",
        phone="+1 415-555-0101",
        linkedin="https://linkedin.com/in/alicejohnson",
        page_title="Our Team | Startup.io",
        scrape_timestamp=datetime.now().isoformat(timespec="seconds"),
    ),
    ScrapedContact(
        email="bob.smith@enterprise.com",
        source_url="https://enterprise.com/contact",
        name_hint="Bob Smith — Sales Director",
        phone="+44 20 7946 0958",
        twitter="https://twitter.com/bobsmith",
        page_title="Contact | Enterprise Corp",
        scrape_timestamp=datetime.now().isoformat(timespec="seconds"),
    ),
    ScrapedContact(
        email="carol@techrecruit.net",
        source_url="https://techrecruit.net/about",
        name_hint="Carol Davis — Recruiter",
        page_title="About | TechRecruit",
        scrape_timestamp=datetime.now().isoformat(timespec="seconds"),
    ),
    # Duplicate — should be removed
    ScrapedContact(
        email="alice@startup.io",
        source_url="https://startup.io/about",
        scrape_timestamp=datetime.now().isoformat(timespec="seconds"),
    ),
]

exporter = DataExporter(output_dir="output")
csv_path  = exporter.export(synthetic_contacts, format="csv",  filename="demo_leads")
json_path = exporter.export(synthetic_contacts, format="json", filename="demo_leads")

exporter.print_summary(synthetic_contacts)

audit.log_export(str(csv_path), len(synthetic_contacts))
print(f"  📄 CSV  → {csv_path}")
print(f"  📄 JSON → {json_path}")
print(f"  📋 Audit log → output/audit_log.txt")
print(f"  📋 Scrape log → output/scraper.log\n")

print("="*55)
print("  ✅  ALL DEMOS COMPLETED SUCCESSFULLY")
print("="*55 + "\n")
