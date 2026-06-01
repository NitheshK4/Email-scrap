# 📧 Email Scraper — Professional Email Scraping Toolkit with BeautifulSoup4

A production-ready, ethical email scraping project that covers **quality**, **accuracy**, **compliance**, and all major **use-cases** of email data collection.

---

## 📁 Project Structure

```
email scraper/
├── email_scraper/
│   ├── __init__.py       # Package init
│   ├── scraper.py        # Core BS4 scraper (single page + recursive crawl)
│   ├── validator.py      # Multi-layer email validation
│   ├── exporter.py       # CSV / JSON / Excel export
│   └── compliance.py     # GDPR/CAN-SPAM, suppression list, audit log
├── output/               # All exported files land here
├── main.py               # CLI entry point
├── demo.py               # Interactive demo of all features
├── requirements.txt
└── README.md
```

---

## ✅ Quality of Email Scraping

| Quality Dimension         | How This Project Addresses It                        |
|---------------------------|------------------------------------------------------|
| **Accuracy**              | RFC 5322 regex + MX record validation                |
| **Valid email addresses** | Multi-layer validator (syntax → domain → MX)         |
| **Relevance**             | Target-path crawling (contact / team / about pages)  |
| **Fresh & updated data**  | Every run timestamps each contact record             |
| **No duplicates**         | Session-wide deduplication before export             |
| **High deliverability**   | Disposable & role-based address filtering + scoring  |
| **Complete contact**      | Co-extracts name hint, phone, LinkedIn, Twitter      |
| **Privacy compliance**    | GDPR/CAN-SPAM/CCPA checks, suppression list          |
| **Ethical collection**    | robots.txt respected, rate-limited, no login bypass  |
| **Low bounce rate**       | Deliverability score (0–100) on every address        |

---

## 🎯 Supported Use-Cases

| Use-Case               | Feature Used                                      |
|------------------------|---------------------------------------------------|
| Lead generation        | Crawl + validate + CSV/Excel export               |
| Email marketing        | Deduplication, deliverability score, suppression  |
| Customer acquisition   | Target-path crawl (contact, about pages)          |
| Recruitment            | Name hint + LinkedIn co-extraction                |
| Business networking    | Full contact record (phone, social profiles)      |
| Market research        | Bulk URL scraping + JSON export                   |
| Survey distribution    | Clean, validated list with low bounce rate        |
| Sales outreach         | Role-based filtering, Excel export                |
| Brand promotion        | Audit log for compliance documentation            |
| Competitor analysis    | Multi-URL batch scraping                          |

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the demo

```bash
python demo.py
```

### 3. CLI Usage

```bash
# Scrape a single page and export as CSV
python main.py --url https://example.com --mode single --format csv

# Recursively crawl a website (up to 50 pages)
python main.py --url https://company.com --mode crawl --max-pages 50 --format all

# Scrape multiple URLs from a file
python main.py --urls-file urls.txt --format excel --output my_leads

# Validate-only (no scraping)
python main.py --validate-only emails.txt

# Add email to suppression/opt-out list
python main.py --add-suppression optout@example.com

# Show compliance notice
python main.py --show-notice
```

### 4. All CLI Options

| Option              | Default         | Description                                        |
|---------------------|-----------------|----------------------------------------------------|
| `--url`             | —               | Single URL to scrape                               |
| `--urls-file`       | —               | File with one URL per line                         |
| `--mode`            | `single`        | `single` or `crawl`                               |
| `--max-pages`       | `20`            | Max pages for crawl mode                           |
| `--format`          | `csv`           | `csv`, `json`, `excel`, or `all`                  |
| `--output`          | `scraped_emails`| Output filename (no extension)                     |
| `--purpose`         | `lead_generation`| Logged to audit trail                             |
| `--delay-min`       | `1.0`           | Min seconds between requests                       |
| `--delay-max`       | `3.0`           | Max seconds between requests                       |
| `--no-validate`     | off             | Skip validation (faster, less accurate)            |
| `--no-robots`       | off             | Ignore robots.txt (NOT recommended)               |
| `--validate-only`   | —               | Validate a file of emails without scraping         |
| `--add-suppression` | —               | Add emails to suppression list                     |
| `--show-notice`     | off             | Print ethics/compliance notice                     |

---

## 🔍 Module Details

### `email_scraper/validator.py`
- RFC 5322 compliant regex
- Disposable domain blacklist (mailinator, guerrillamail, etc.)
- Role-based prefix detection (admin, info, noreply, etc.)
- Optional MX record lookup
- **Deliverability score** (0–100)

### `email_scraper/scraper.py`
- `requests` + `BeautifulSoup4 (lxml parser)`
- `mailto:` link extraction (most reliable)
- Full text regex fallback scan
- User-agent rotation (4 real browser fingerprints)
- Polite rate limiting with jitter
- Retry with exponential back-off (HTTP 429, network errors)
- Robots.txt compliance via `urllib.robotparser`
- Co-extracts: phone numbers, LinkedIn URLs, Twitter/X URLs, name hints

### `email_scraper/exporter.py`
- **CSV**: UTF-8, universal compatibility
- **JSON**: Pretty-printed, machine-readable
- **Excel**: Styled header row, auto-fit columns (requires pandas + openpyxl)
- Pre-export deduplication
- Quality summary table printed to console

### `email_scraper/compliance.py`
- `SuppressionList`: persistent opt-out file, auto-filters contacts
- `ComplianceChecker`: detects privacy policy and ToS restrictions in HTML
- `AuditLogger`: timestamped audit trail for GDPR accountability
- Printed compliance notice covering GDPR, CAN-SPAM, CCPA, CASL

---

## ⚖️ Ethical Guidelines

> **Only scrape publicly available data.**
> Always respect `robots.txt` (enabled by default).
> Use the suppression list for all opt-outs.
> Never scrape behind login walls or paywalls.
> Comply with GDPR, CAN-SPAM, CCPA, and CASL.

---

## 📦 Dependencies

| Package         | Purpose                              |
|-----------------|--------------------------------------|
| `beautifulsoup4`| HTML parsing                         |
| `lxml`          | Fast HTML parser backend             |
| `requests`      | HTTP client                          |
| `pandas`        | Excel/DataFrame operations           |
| `openpyxl`      | Excel file writing                   |
| `colorama`      | Colored terminal output              |
| `tqdm`          | Progress bars                        |
| `dnspython`     | MX record lookups (optional)         |
| `fake-useragent`| User-agent rotation                  |
| `validators`    | URL validation helpers               |
