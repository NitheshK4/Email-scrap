"""
app.py — Flask Web Server for Email Scraper
"""

import io
import csv
import json
import threading
import uuid
import imaplib
import email as email_lib
from email.header import decode_header
from datetime import datetime
from pathlib import Path


from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS

from email_scraper.scraper import EmailScraper
from email_scraper.validator import EmailValidator
from email_scraper.exporter import DataExporter
from email_scraper.compliance import SuppressionList, AuditLogger

app = Flask(__name__)
CORS(app)

Path("output").mkdir(exist_ok=True)

# In-memory job store  { job_id: { status, contacts, error } }
JOBS: dict = {}
JOBS_LOCK = threading.Lock()

suppression = SuppressionList()
audit       = AuditLogger()
exporter    = DataExporter(output_dir="output")


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/sample")
def sample_page():
    """
    A realistic-looking public company/university contact page
    with real email addresses embedded in HTML.
    The scraper can scrape THIS page to demonstrate live BS4 extraction.
    """
    html = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>VIT-AP University — Contact Directory</title></head>
<body>
<h1>VIT-AP University — Staff Contact Directory</h1>
<p>For general enquiries, reach us at <a href="mailto:info@vitapstudent.ac.in">info@vitapstudent.ac.in</a></p>

<h2>Administration</h2>
<table>
  <tr><td>Vice Chancellor</td><td>Dr. S. V. Kota Reddy</td><td><a href="mailto:vc@vitapstudent.ac.in">vc@vitapstudent.ac.in</a></td><td>+91 863 2344 700</td></tr>
  <tr><td>Registrar</td><td>Dr. A. Rajesh Kumar</td><td>registrar@vitapstudent.ac.in</td><td>+91 863 2344 701</td></tr>
  <tr><td>Admissions</td><td>Mr. Pradeep Nair</td><td>admissions@vitapstudent.ac.in</td><td>+91 863 2344 710</td></tr>
  <tr><td>Finance Officer</td><td>Ms. Sunita Verma</td><td>finance@vitapstudent.ac.in</td><td>+91 863 2344 720</td></tr>
</table>

<h2>Department Heads</h2>
<ul>
  <li>CSE Department — Dr. Ravi Kumar &lt;hod.cse@vitapstudent.ac.in&gt; | +91 863 2344 800</li>
  <li>ECE Department — Dr. Priya Sharma &lt;hod.ece@vitapstudent.ac.in&gt;</li>
  <li>MBA Department — Dr. Anil Mehta &lt;hod.mba@vitapstudent.ac.in&gt;</li>
  <li>Civil Engineering — Dr. Lakshmi Reddy &lt;hod.civil@vitapstudent.ac.in&gt;</li>
</ul>

<h2>Student Services</h2>
<p>Placement Cell: <a href="mailto:placements@vitapstudent.ac.in">placements@vitapstudent.ac.in</a> | Tel: +91 863 2344 900</p>
<p>Hostel Warden: hostel@vitapstudent.ac.in | Tel: +91 863 2344 910</p>
<p>Library: library@vitapstudent.ac.in</p>
<p>Sports Director: sports@vitapstudent.ac.in</p>
<p>Student Grievance: grievance@vitapstudent.ac.in</p>

<h2>Research &amp; Innovation</h2>
<p>Contact our research team at research@vitapstudent.ac.in or innovation@vitapstudent.ac.in</p>

<h2>External Collaborations</h2>
<p>Student Developer — Nithesh Kumar: <a href="mailto:nitheshk236@gmail.com">nitheshk236@gmail.com</a></p>
<p>Industry Liaison: industry@vitapstudent.ac.in | +91 863 2344 950</p>
<p>International Relations: international@vitapstudent.ac.in</p>

<p>Follow us on LinkedIn: <a href="https://linkedin.com/company/vit-ap-university">VIT-AP LinkedIn</a></p>
</body>
</html>"""
    return html



@app.route("/api/mail-scrape", methods=["POST"])
def mail_scrape():
    """
    Connect to Gmail via IMAP and extract all unique email addresses
    found in the inbox (From, To, CC, Reply-To fields).
    Requires an App Password (not regular Gmail password).
    """
    data     = request.get_json(force=True)
    email_id = data.get("email", "").strip()
    password = data.get("password", "").strip()
    limit    = int(data.get("limit", 100))   # max emails to scan

    if not email_id or not password:
        return jsonify({"error": "Email and App Password are required"}), 400

    # Detect provider
    domain = email_id.split("@")[-1].lower()
    imap_servers = {
        "gmail.com"     : ("imap.gmail.com",   993),
        "yahoo.com"     : ("imap.mail.yahoo.com", 993),
        "outlook.com"   : ("imap-mail.outlook.com", 993),
        "hotmail.com"   : ("imap-mail.outlook.com", 993),
        "icloud.com"    : ("imap.mail.me.com", 993),
    }
    host, port = imap_servers.get(domain, ("imap." + domain, 993))

    try:
        # Connect
        mail = imaplib.IMAP4_SSL(host, port)
        mail.login(email_id, password)
        mail.select("INBOX")

        # Fetch latest `limit` message IDs
        _, msg_ids = mail.search(None, "ALL")
        id_list = msg_ids[0].split()
        recent  = id_list[-limit:] if len(id_list) > limit else id_list

        found_emails: set = set()
        contacts = []

        def decode_str(s):
            if not s:
                return ""
            parts = decode_header(s)
            out = []
            for part, enc in parts:
                if isinstance(part, bytes):
                    out.append(part.decode(enc or "utf-8", errors="ignore"))
                else:
                    out.append(str(part))
            return " ".join(out)

        import re
        addr_re = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

        for mid in reversed(recent):
            _, data_raw = mail.fetch(mid, "(RFC822.SIZE RFC822.HEADER)")
            raw = data_raw[0][1]
            msg = email_lib.message_from_bytes(raw)

            headers_to_check = ["From", "To", "Cc", "Reply-To"]
            for hdr in headers_to_check:
                val = msg.get(hdr, "")
                if not val:
                    continue
                emails_in_field = addr_re.findall(val)
                for e in emails_in_field:
                    e = e.lower()
                    if e not in found_emails:
                        found_emails.add(e)
                        contacts.append({
                            "email"           : e,
                            "name_hint"       : decode_str(msg.get("From", "")) if hdr == "From" else "",
                            "phone"           : "",
                            "linkedin"        : "",
                            "twitter"         : "",
                            "source_url"      : f"Inbox ({hdr})",
                            "page_title"      : decode_str(msg.get("Subject", ""))[:60],
                            "scrape_timestamp": datetime.now().isoformat(timespec="seconds"),
                        })

        mail.logout()
        audit.log(f"MAIL_SCRAPE", f"USER={email_id} FOUND={len(contacts)}")

        return jsonify({
            "status"  : "done",
            "contacts": contacts,
            "total"   : len(contacts),
            "has_phone": 0,
            "has_name" : sum(1 for c in contacts if c["name_hint"]),
            "has_linkedin": 0,
        })

    except imaplib.IMAP4.error as e:
        return jsonify({"error": f"Login failed: {str(e)}. Make sure you use an App Password, not your regular password."}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/scrape", methods=["POST"])

def scrape():
    data = request.get_json(force=True)
    url       = data.get("url", "").strip()
    mode      = data.get("mode", "single")       # single | crawl
    max_pages = int(data.get("max_pages", 20))
    validate  = data.get("validate", True)
    purpose   = data.get("purpose", "lead_generation")

    if not url:
        return jsonify({"error": "URL or email address is required"}), 400

    # ── Auto-detect: if user entered an email address, extract domain ──
    resolved_from_email = None
    if "@" in url and not url.startswith("http"):
        domain = url.split("@")[-1].strip()
        resolved_from_email = url          # original email
        url = f"https://{domain}"         # scrape the domain website

    # ── Auto-add https:// if missing ──
    elif not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    job_id = str(uuid.uuid4())
    with JOBS_LOCK:
        JOBS[job_id] = {
            "status": "running", "contacts": [], "error": None, "progress": 0,
            "resolved_url": url,
            "resolved_from_email": resolved_from_email,
        }

    thread = threading.Thread(
        target=_run_scrape,
        args=(job_id, url, mode, max_pages, validate, purpose),
        daemon=True,
    )
    thread.start()
    return jsonify({"job_id": job_id, "resolved_url": url, "resolved_from_email": resolved_from_email}), 202


@app.route("/api/job/<job_id>")
def job_status(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/validate", methods=["POST"])
def validate_emails():
    data   = request.get_json(force=True)
    emails = data.get("emails", [])
    if isinstance(emails, str):
        emails = [e.strip() for e in emails.splitlines() if e.strip()]

    validator = EmailValidator(check_mx=False)
    results = []
    for email in emails[:200]:  # cap at 200
        r = validator.validate(email)
        results.append(r.to_dict())

    return jsonify({"results": results})


@app.route("/api/export/<job_id>")
def export(job_id):
    fmt = request.args.get("format", "csv")
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job or job["status"] != "done":
        return jsonify({"error": "Job not ready"}), 404

    from email_scraper.scraper import ScrapedContact
    contacts = job["contacts"]  # already list of dicts

    if fmt == "json":
        buf = io.BytesIO(json.dumps(contacts, indent=2, ensure_ascii=False).encode("utf-8"))
        buf.seek(0)
        return send_file(buf, mimetype="application/json",
                         download_name="scraped_emails.json", as_attachment=True)
    else:  # csv default
        fieldnames = ["email","name_hint","phone","linkedin","twitter",
                      "source_url","page_title","scrape_timestamp"]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(contacts)
        buf.seek(0)
        return send_file(
            io.BytesIO(buf.getvalue().encode("utf-8")),
            mimetype="text/csv",
            download_name="scraped_emails.csv",
            as_attachment=True,
        )


@app.route("/api/suppress", methods=["POST"])
def add_suppression():
    data  = request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "email required"}), 400
    suppression.add(email)
    audit.log_suppression(email, "web_ui_opt_out")
    return jsonify({"message": f"{email} added to suppression list"})


# ─────────────────────────────────────────────
# Background worker
# ─────────────────────────────────────────────

def _run_scrape(job_id, url, mode, max_pages, validate, purpose):
    try:
        scraper = EmailScraper(
            validate_emails=validate,
            check_robots=True,
            delay=(0.5, 1.5),
        )
        audit.log_scrape_start(url, purpose)

        if mode == "crawl":
            contacts = scraper.crawl(
                start_url=url,
                max_pages=max_pages,
                stay_on_domain=True,
                target_paths=["contact", "about", "team", "staff", "people"],
            )
        else:
            contacts = scraper.scrape_url(url)

        contacts = suppression.filter_contacts(contacts)
        audit.log_scrape_end(url, len(contacts))

        contact_dicts = [c.to_dict() for c in contacts]

        # Quality metrics
        total    = len(contact_dicts)
        has_phone   = sum(1 for c in contact_dicts if c.get("phone"))
        has_name    = sum(1 for c in contact_dicts if c.get("name_hint"))
        has_linkedin = sum(1 for c in contact_dicts if c.get("linkedin"))

        with JOBS_LOCK:
            JOBS[job_id] = {
                "status"   : "done",
                "contacts" : contact_dicts,
                "error"    : None,
                "total"    : total,
                "has_phone": has_phone,
                "has_name" : has_name,
                "has_linkedin": has_linkedin,
                "scraped_url" : url,
                "timestamp"   : datetime.now().isoformat(timespec="seconds"),
            }
    except Exception as exc:
        with JOBS_LOCK:
            JOBS[job_id] = {
                "status": "error",
                "contacts": [],
                "error": str(exc),
            }


if __name__ == "__main__":
    app.run(debug=True, port=5051)
