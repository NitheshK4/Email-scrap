"""
main.py — Email Scraper CLI Entry Point

Usage examples:
  python main.py --url https://example.com --mode single
  python main.py --url https://example.com --mode crawl --max-pages 30
  python main.py --urls-file urls.txt --format all
  python main.py --validate-only emails.txt
"""

import argparse
import logging
import sys
from pathlib import Path

from email_scraper.scraper import EmailScraper
from email_scraper.validator import EmailValidator
from email_scraper.exporter import DataExporter
from email_scraper.compliance import (
    SuppressionList, AuditLogger, ComplianceChecker, COMPLIANCE_NOTICE
)

# ------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("output/scraper.log", mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def ensure_output_dir():
    Path("output").mkdir(exist_ok=True)


def run_scrape(args):
    """Main scrape flow."""
    suppression = SuppressionList()
    audit = AuditLogger()
    exporter = DataExporter(output_dir="output")

    scraper = EmailScraper(
        validate_emails=not args.no_validate,
        check_robots=not args.no_robots,
        delay=(args.delay_min, args.delay_max),
    )

    contacts = []

    if args.url:
        urls = [args.url]
    elif args.urls_file:
        with open(args.urls_file) as f:
            urls = [line.strip() for line in f if line.strip()]
    else:
        print("[ERROR] Provide --url or --urls-file")
        sys.exit(1)

    for url in urls:
        audit.log_scrape_start(url, purpose=args.purpose)
        if args.mode == "crawl":
            found = scraper.crawl(
                start_url=url,
                max_pages=args.max_pages,
                stay_on_domain=True,
                target_paths=["contact", "about", "team", "staff", "people"],
            )
        else:
            found = scraper.scrape_url(url)
        audit.log_scrape_end(url, len(found))
        contacts.extend(found)

    # Apply suppression list
    contacts = suppression.filter_contacts(contacts)

    # Export
    out_path = exporter.export(contacts, format=args.format, filename=args.output)
    audit.log_export(str(out_path), len(contacts))

    # Summary
    exporter.print_summary(contacts)
    print(f"✅  Results saved to: {out_path}")


def run_validate_only(args):
    """Validate a plain-text file of email addresses."""
    validator = EmailValidator(check_mx=True)
    with open(args.validate_only) as f:
        emails = [line.strip() for line in f if line.strip()]

    print(f"\nValidating {len(emails)} email(s)...\n")
    valid, invalid = [], []
    for email in emails:
        result = validator.validate(email)
        status = "✅ VALID" if result.is_valid else "❌ INVALID"
        flag = ""
        if result.is_disposable:
            flag = " [DISPOSABLE]"
        if result.is_role_based:
            flag += " [ROLE-BASED]"
        print(f"  {status:12} {email:40} Score: {result.score:3d}{flag}")
        (valid if result.is_valid else invalid).append(email)

    print(f"\n  ✅ Valid  : {len(valid)}")
    print(f"  ❌ Invalid: {len(invalid)}\n")


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="email-scraper",
        description="Professional Email Scraper with BS4 — Ethical & Accurate",
    )
    parser.add_argument("--url", help="Single URL to scrape")
    parser.add_argument("--urls-file", help="Text file with one URL per line")
    parser.add_argument(
        "--mode", choices=["single", "crawl"], default="single",
        help="'single': one page only | 'crawl': follow links recursively"
    )
    parser.add_argument("--max-pages", type=int, default=20,
                        help="Max pages to crawl (default: 20)")
    parser.add_argument(
        "--format", choices=["csv", "json", "excel", "all"], default="csv",
        help="Output format (default: csv)"
    )
    parser.add_argument("--output", default="scraped_emails",
                        help="Output filename without extension (default: scraped_emails)")
    parser.add_argument("--purpose", default="lead_generation",
                        help="Scraping purpose for audit log (e.g., recruitment, market_research)")
    parser.add_argument("--delay-min", type=float, default=1.0,
                        help="Min delay between requests in seconds (default: 1.0)")
    parser.add_argument("--delay-max", type=float, default=3.0,
                        help="Max delay between requests in seconds (default: 3.0)")
    parser.add_argument("--no-validate", action="store_true",
                        help="Skip email validation (faster but less accurate)")
    parser.add_argument("--no-robots", action="store_true",
                        help="Ignore robots.txt (NOT recommended — unethical)")
    parser.add_argument("--validate-only",
                        help="Path to a text file of emails to validate (no scraping)")
    parser.add_argument("--add-suppression", nargs="+",
                        help="Add one or more emails to the suppression list")
    parser.add_argument("--show-notice", action="store_true",
                        help="Print the compliance and ethics notice")
    return parser


def main():
    ensure_output_dir()
    parser = build_parser()
    args = parser.parse_args()

    if args.show_notice:
        print(COMPLIANCE_NOTICE)
        return

    if args.add_suppression:
        sl = SuppressionList()
        audit = AuditLogger()
        for email in args.add_suppression:
            sl.add(email)
            audit.log_suppression(email, "manual_opt_out")
            print(f"  ➕ Added to suppression list: {email}")
        return

    if args.validate_only:
        run_validate_only(args)
        return

    print(COMPLIANCE_NOTICE)
    run_scrape(args)


if __name__ == "__main__":
    main()
