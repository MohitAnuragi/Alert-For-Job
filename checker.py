"""
Job Alert System — checker.py
Monitors 142 startup companies for new SDE/Android internship job postings on LinkedIn.
Sends HTML email alerts via Gmail SMTP when new openings are detected.
State is persisted in seen_jobs.json committed back to GitHub.
"""

import csv
import json
import logging
import os
import random
import re
import smtplib
import ssl
import sys
import time
import urllib.parse
from datetime import date
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ─── Logging Setup ───────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────────

SEEN_JOBS_FILE = "seen_jobs.json"
WHITELIST_CSV_FILE = "final_master_startup_sheet_150.csv"
RECIPIENT_EMAIL = "crazymohit468@gmail.com"
MAX_RETRIES = 3
BASE_BACKOFF = 2  # seconds

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
]

COMPANIES = [
    "Appsmith", "ToolJet", "Hoppscotch", "SigNoz", "Hasura", "Supabase",
    "Postman", "Razorpay", "Juspay", "Zeta", "Meesho", "Swiggy", "Zepto",
    "CRED", "ShareChat", "Koo", "Pocket FM", "Stage", "Rooter", "Chingari",
    "Krutrim", "Sarvam AI", "Mad Street Den", "SigTuple", "Uniphore",
    "Yellow.ai", "Rephrase.ai", "Ganit", "Fi Money", "Jar", "Slice", "Navi",
    "Uni Cards", "Open Financial Technologies", "Rupeek", "Perfios",
    "Banyan Cloud", "Airlearn", "Nbyula", "DrinkPrime", "SkilloVilla",
    "Turbostart", "2070 Health", "Outplay", "Ati Motors", "Peppermint Robotics",
    "Masai School", "Newton School", "Scaler", "FunctionUp", "ClearFeed",
    "Infilect", "100ms", "ARTPARK", "CloudSEK", "Openhouse", "Eloelo",
    "Vymo", "Zycus", "Leap Finance", "Instawork", "EarnIn", "SWARA",
    "demtech.ai", "Gamtus", "Senzcraft", "Zaimler", "Playo", "Triplespeed",
    "Bibha AI Labs", "Groww", "Upstox", "CoinDCX", "BrowserStack",
    "Freshworks", "Chargebee", "Zoho", "Whatfix", "Capillary", "Darwinbox",
    "Unacademy", "Vedantu", "Byjus", "PhysicsWallah", "Testbook", "Toppr",
    "Coding Ninjas", "Scaler Academy", "InterviewBit", "GeekyAnts",
    "Livspace", "Urban Company", "NoBroker", "Housing", "MagicBricks",
    "Ola Electric", "Bounce", "Ather Energy", "Yulu", "Rapido", "Delhivery",
    "Shadowfax", "BlackBuck", "Rivigo", "Porter", "Locus", "Shipsy",
    "Pickrr", "ElasticRun", "OfBusiness", "Dunzo", "Pocketly", "Credgenics",
    "Fampay", "Simpl", "OkCredit", "Khatabook", "Udaan", "Infra.Market",
    "Bizongo", "DealShare", "CityMall", "Trella", "Loadshare", "FarEye",
    "Ninjacart", "Frnd", "Turnip", "Loco", "Bolo Live", "Kubeapps",
    "M365Consult", "Ekagga Technology", "NewSpace Research",
]

APPROVED_ROLE_PHRASES = (
    "android developer", "android engineer", "android software engineer",
    "android application developer", "android mobile developer",
    "mobile developer", "mobile engineer", "mobile software engineer",
    "software engineer android", "software engineer - android",
    "software development engineer android", "android platform engineer",
    "android sdk engineer", "android intern", "android engineering intern",
    "mobile developer intern", "mobile engineering intern",
    "android application intern", "android software intern", "android trainee",
    "android graduate engineer", "junior android developer",
    "associate android developer", "kotlin developer", "kotlin engineer",
    "kotlin software engineer", "backend kotlin developer",
    "backend kotlin engineer", "jvm developer", "jvm engineer",
    "backend developer", "backend engineer", "java backend engineer",
    "java developer", "java software engineer", "java engineer",
    "spring boot developer", "spring boot engineer",
    "software engineer backend", "backend software engineer",
    "api developer", "server-side developer", "platform engineer backend",
    "associate backend engineer", "junior backend developer",
    "backend intern", "java intern", "backend engineering intern",
    "full stack developer", "full stack engineer",
    "software engineer full stack", "software developer full stack",
    "full stack software engineer", "mern developer", "mean developer",
    "node.js developer", "node.js engineer", "express.js developer",
    "express.js engineer", "typescript developer", "typescript engineer",
    "javascript full stack developer", "associate full stack engineer",
    "junior full stack developer", "full stack intern",
    "node.js intern", "full stack engineering intern",
    "software engineer", "software developer",
    "software development engineer", "sde", "sde i", "sde-1",
    "software engineer i", "software engineer 1",
    "associate software engineer", "graduate software engineer",
    "graduate engineer", "graduate software developer",
    "entry level software engineer", "early career software engineer",
    "junior software engineer", "software engineering intern",
    "software developer intern", "engineering intern",
    "technical intern", "application engineer", "product engineer",
    "platform engineer", "systems engineer software",
    "solutions engineer software",
)

APPROVED_EXPERIENCE_TERMS = (
    "intern", "internship", "new grad", "graduate", "associate",
    "entry level", "junior", "0-1 years", "0-2 years", "1 year",
    "freshers", "campus hiring", "university hiring", "college hiring",
    "software engineer i", "sde i", "graduate program",
    "early career", "return offer program",
)

REJECTED_TITLE_TERMS = (
    "senior", "sr.", "lead", "principal", "manager", "director",
    "staff engineer", "architect", "vp", "head", "10+ years",
    "8+ years", "7+ years", "6+ years", "5+ years",
    "ui designer", "ux designer", "graphic designer", "marketing",
    "growth", "sales", "business development", "finance", "hr",
    "recruiter", "talent acquisition", "customer success", "support engineer",
    "it support", "network engineer", "devops", "cloud engineer",
    "data analyst", "business analyst", "data scientist",
    "machine learning engineer", "ai researcher", "research scientist",
    "prompt engineer", "embedded engineer", "hardware engineer",
    "qa engineer", "automation tester", "manual tester",
    "security engineer", "cyber security", "blockchain", "sap",
    "oracle consultant", "game developer", "unity developer",
    "flutter developer", "react native developer", "ios developer",
    "php developer", "wordpress developer", "seo", "content writer",
    "technical writer", "legal", "operations", "procurement",
    "supply chain", "admin",
)


def _normalize_text(text: str) -> str:
    """Normalize text for strict keyword matching."""
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def normalize_company_name(company_name: str) -> str:
    """Normalize a company name for whitelist comparison."""
    normalized = re.sub(r"\s+", " ", (company_name or "").strip()).lower()
    if not normalized:
        return ""

    removable_suffixes = [
        "pvt", "pvt.", "pvt ltd", "pvt. ltd.", "private limited",
        "inc", "llc", "ltd", "limited", "technologies", "technology",
        "tech", "labs", "solutions", "ai",
    ]

    for suffix in removable_suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)].strip()
            break

    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def load_company_whitelist(csv_path: str = WHITELIST_CSV_FILE) -> set[str]:
    """Load approved companies from the CSV once and return them as a set."""
    if not os.path.exists(csv_path):
        logger.error("ERROR\nUnable to load company whitelist.\nFile:\n%s\nExecution stopped.", csv_path)
        sys.exit(1)

    try:
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            companies = {
                normalize_company_name(row.get("Company", ""))
                for row in reader
                if normalize_company_name(row.get("Company", ""))
            }
    except Exception as exc:
        logger.error("ERROR\nUnable to load company whitelist.\nFile:\n%s\nExecution stopped.", csv_path)
        logger.error("CSV parse error: %s", exc)
        sys.exit(1)

    if not companies:
        logger.error("ERROR\nUnable to load company whitelist.\nFile:\n%s\nExecution stopped.", csv_path)
        sys.exit(1)

    logger.info("Loaded company whitelist.")
    logger.info("Approved companies: %d", len(companies))
    return companies


def is_relevant_job(title: str, experience_text: str = "", description: str = "") -> bool:
    """Apply the strict candidate-specific role and experience filter."""
    combined_text = " ".join(filter(None, [title, experience_text, description]))
    normalized_text = _normalize_text(combined_text)

    if not normalized_text:
        return False

    if any(term in normalized_text for term in REJECTED_TITLE_TERMS):
        return False

    if not any(phrase in normalized_text for phrase in APPROVED_ROLE_PHRASES):
        return False

    if not any(term in normalized_text for term in APPROVED_EXPERIENCE_TERMS):
        return False

    return True


# ─── HTTP Helper ─────────────────────────────────────────────────────────────

def _get_random_headers() -> dict:
    """Return a dict of HTTP headers with a rotated User-Agent."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "DNT": "1",
    }


def _fetch_with_retry(url: str, timeout: int = 15) -> Optional[requests.Response]:
    """
    Fetch a URL with up to MAX_RETRIES attempts and exponential backoff.
    Returns the Response on success, or None on all failures.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                url,
                headers=_get_random_headers(),
                timeout=timeout,
                allow_redirects=True,
            )
            if response.status_code == 200:
                return response
            elif response.status_code in (429, 503):
                wait = BASE_BACKOFF ** attempt + random.uniform(0, 1)
                logger.warning(
                    "Rate-limited (%s) on attempt %d/%d — sleeping %.1fs: %s",
                    response.status_code, attempt, MAX_RETRIES, wait, url,
                )
                time.sleep(wait)
            else:
                logger.warning(
                    "HTTP %s on attempt %d/%d: %s",
                    response.status_code, attempt, MAX_RETRIES, url,
                )
                break
        except requests.exceptions.RequestException as exc:
            wait = BASE_BACKOFF ** attempt + random.uniform(0, 1)
            logger.warning(
                "Request error on attempt %d/%d (%.1fs backoff): %s — %s",
                attempt, MAX_RETRIES, wait, url, exc,
            )
            time.sleep(wait)
    return None


# ─── Scraper: LinkedIn ────────────────────────────────────────────────────────

def get_linkedin_jobs(company_name: str) -> list[dict]:
    """
    Search LinkedIn Jobs for a company's internship postings from the last 24h.

    Args:
        company_name: The company name to search for.

    Returns:
        List of job dicts with keys: job_id, title, company, location,
        posted_time, job_url. Returns empty list on any failure.
    """
    try:
        encoded = urllib.parse.quote_plus(f"{company_name} intern")
        url = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={encoded}&f_TPR=r86400&f_JT=I&location=India"
        )
        response = _fetch_with_retry(url)
        if response is None:
            return []

        soup = BeautifulSoup(response.text, "lxml")
        jobs: list[dict] = []

        # LinkedIn job cards appear in <ul class="jobs-search__results-list">
        job_cards = soup.select("li.result-card, div.base-card, li[data-id]")

        # Fallback selector for alternate page structures
        if not job_cards:
            job_cards = soup.select("div.job-search-card, article.job-card-container")

        for card in job_cards:
            try:
                # Extract job ID
                job_id = (
                    card.get("data-id")
                    or card.get("data-entity-urn", "").split(":")[-1]
                    or ""
                )

                # Extract job URL
                link_tag = card.select_one("a.result-card__full-card-link, a.base-card__full-link, a[href*='/jobs/view/']")
                job_url = ""
                if link_tag and link_tag.get("href"):
                    job_url = link_tag["href"].split("?")[0]  # strip tracking params
                    if not job_id:
                        # Derive ID from URL: /jobs/view/1234567890/
                        match = re.search(r"/jobs/view/(\d+)", job_url)
                        if match:
                            job_id = match.group(1)

                if not job_url and not job_id:
                    continue  # can't identify this card

                # Use URL as fallback ID
                unique_key = job_id if job_id else job_url

                # Extract title
                title_tag = card.select_one(
                    "h3.result-card__title, h3.base-search-card__title, "
                    "span.screen-reader-text, h3[class*='title']"
                )
                title = title_tag.get_text(strip=True) if title_tag else "N/A"

                # Extract company name from card (may differ from search term)
                company_tag = card.select_one(
                    "h4.result-card__subtitle, h4.base-search-card__subtitle, "
                    "a[class*='company'], span[class*='company']"
                )
                card_company = company_tag.get_text(strip=True) if company_tag else company_name

                # Extract location
                location_tag = card.select_one(
                    "span.job-search-card__location, span[class*='location']"
                )
                location = location_tag.get_text(strip=True) if location_tag else "India"

                # Extract posted time
                time_tag = card.select_one("time, span[class*='date'], span[class*='listdate']")
                posted_time = ""
                if time_tag:
                    posted_time = time_tag.get("datetime") or time_tag.get_text(strip=True)

                jobs.append(
                    {
                        "job_id": unique_key,
                        "title": title,
                        "company": card_company,
                        "location": location,
                        "posted_time": posted_time,
                        "job_url": job_url or f"https://www.linkedin.com/jobs/view/{job_id}/",
                        "source": "LinkedIn",
                    }
                )
            except Exception as card_exc:
                logger.warning("Error parsing LinkedIn job card for %s: %s", company_name, card_exc)
                continue

        logger.info("LinkedIn → %s: found %d job(s)", company_name, len(jobs))
        return jobs

    except Exception as exc:
        logger.warning("get_linkedin_jobs failed for %s: %s", company_name, exc)
        return []


# ─── Scraper: Google Fallback ─────────────────────────────────────────────────

def get_google_jobs(company_name: str) -> list[dict]:
    """
    Fallback: Google-search for the company's internship postings on LinkedIn.
    Extracts /jobs/view/ URLs from search results.

    Args:
        company_name: The company name to search for.

    Returns:
        List of job dicts. Returns empty list on any failure.
    """
    try:
        query = urllib.parse.quote_plus(
            f"{company_name} intern site:linkedin.com/jobs/view"
        )
        url = f"https://www.google.com/search?q={query}&num=20"
        response = _fetch_with_retry(url)
        if response is None:
            return []

        soup = BeautifulSoup(response.text, "lxml")
        jobs: list[dict] = []
        seen_ids: set[str] = set()

        # Extract all href attributes containing linkedin.com/jobs/view
        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            # Google wraps links in /url?q=...
            if "/url?q=" in href:
                href = urllib.parse.unquote(href.split("/url?q=")[1].split("&")[0])

            match = re.search(r"linkedin\.com/jobs/view/(\d+)", href)
            if match:
                job_id = match.group(1)
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                job_url = f"https://www.linkedin.com/jobs/view/{job_id}/"

                # Try to pull title from the surrounding anchor text
                title = tag.get_text(strip=True) or "Internship Opening"
                if not title or len(title) < 3:
                    title = "Internship Opening"

                jobs.append(
                    {
                        "job_id": job_id,
                        "title": title,
                        "company": company_name,
                        "location": "India",
                        "posted_time": "",
                        "job_url": job_url,
                        "source": "Google",
                    }
                )

        logger.info("Google fallback → %s: found %d job(s)", company_name, len(jobs))
        return jobs

    except Exception as exc:
        logger.warning("get_google_jobs failed for %s: %s", company_name, exc)
        return []


# ─── State Persistence ────────────────────────────────────────────────────────

def load_seen_jobs() -> set[str]:
    """
    Load the set of previously seen job IDs/URLs from seen_jobs.json.

    Returns:
        Set of string identifiers. Empty set if file is missing or invalid.
    """
    if not os.path.exists(SEEN_JOBS_FILE):
        logger.info("seen_jobs.json not found — starting fresh.")
        return set()
    try:
        with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            return set(data)
        logger.warning("seen_jobs.json has unexpected format — starting fresh.")
        return set()
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read seen_jobs.json: %s — starting fresh.", exc)
        return set()


def save_seen_jobs(seen: set[str]) -> None:
    """
    Persist the set of seen job IDs/URLs to seen_jobs.json (pretty-printed).

    Args:
        seen: The complete set of all seen job identifiers.
    """
    try:
        with open(SEEN_JOBS_FILE, "w", encoding="utf-8") as fh:
            json.dump(sorted(seen), fh, indent=2, ensure_ascii=False)
        logger.info("Saved %d seen job(s) to %s.", len(seen), SEEN_JOBS_FILE)
    except OSError as exc:
        logger.error("Failed to save seen_jobs.json: %s", exc)


# ─── Email ────────────────────────────────────────────────────────────────────

def _build_html_email(new_jobs: list[dict]) -> str:
    """Build a rich HTML email body for the given list of new jobs."""
    today = date.today().strftime("%B %d, %Y")
    rows_html = ""
    for job in new_jobs:
        apply_url = job.get("job_url", "#")
        rows_html += f"""
        <tr>
          <td style="padding:12px 16px; border-bottom:1px solid #2d3748; color:#e2e8f0; font-weight:500;">
            {_esc(job.get('company', 'N/A'))}
          </td>
          <td style="padding:12px 16px; border-bottom:1px solid #2d3748; color:#cbd5e0;">
            {_esc(job.get('title', 'N/A'))}
          </td>
          <td style="padding:12px 16px; border-bottom:1px solid #2d3748; color:#a0aec0;">
            {_esc(job.get('location', 'India'))}
          </td>
          <td style="padding:12px 16px; border-bottom:1px solid #2d3748; color:#718096; font-size:13px;">
            {_esc(job.get('posted_time') or 'Last 24h')}
          </td>
          <td style="padding:12px 16px; border-bottom:1px solid #2d3748; text-align:center;">
            <a href="{apply_url}"
               style="display:inline-block; padding:7px 18px; background:linear-gradient(135deg,#667eea,#764ba2);
                      color:#fff; text-decoration:none; border-radius:6px; font-size:13px; font-weight:600;
                      letter-spacing:0.5px;">
              Apply →
            </a>
          </td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>New Internship Openings — {today}</title>
</head>
<body style="margin:0; padding:0; background-color:#0f1117; font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f1117; padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="700" cellpadding="0" cellspacing="0"
               style="background:#1a1d2e; border-radius:16px; overflow:hidden;
                      box-shadow:0 20px 60px rgba(0,0,0,0.5);">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
                        padding:36px 40px; text-align:center;">
              <div style="font-size:40px; margin-bottom:8px;">🚨</div>
              <h1 style="margin:0; color:#fff; font-size:26px; font-weight:700; letter-spacing:-0.5px;">
                {len(new_jobs)} New Internship Opening{'s' if len(new_jobs) != 1 else ''} Found!
              </h1>
              <p style="margin:8px 0 0; color:rgba(255,255,255,0.8); font-size:15px;">
                Detected on {today} · SDE &amp; Android Internships
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px 40px;">
              <p style="margin:0 0 24px; color:#a0aec0; font-size:15px; line-height:1.6;">
                The job monitor found <strong style="color:#667eea;">{len(new_jobs)} new opening(s)</strong>
                across the 142 tracked startup companies. Click <strong>Apply →</strong> to view the full
                job listing on LinkedIn.
              </p>

              <!-- Jobs Table -->
              <div style="overflow-x:auto; border-radius:10px; border:1px solid #2d3748;">
                <table width="100%" cellpadding="0" cellspacing="0"
                       style="border-collapse:collapse; min-width:580px;">
                  <thead>
                    <tr style="background:#252841;">
                      <th style="padding:14px 16px; text-align:left; color:#667eea;
                                  font-size:12px; font-weight:600; letter-spacing:1px; text-transform:uppercase;">
                        Company
                      </th>
                      <th style="padding:14px 16px; text-align:left; color:#667eea;
                                  font-size:12px; font-weight:600; letter-spacing:1px; text-transform:uppercase;">
                        Role
                      </th>
                      <th style="padding:14px 16px; text-align:left; color:#667eea;
                                  font-size:12px; font-weight:600; letter-spacing:1px; text-transform:uppercase;">
                        Location
                      </th>
                      <th style="padding:14px 16px; text-align:left; color:#667eea;
                                  font-size:12px; font-weight:600; letter-spacing:1px; text-transform:uppercase;">
                        Posted
                      </th>
                      <th style="padding:14px 16px; text-align:center; color:#667eea;
                                  font-size:12px; font-weight:600; letter-spacing:1px; text-transform:uppercase;">
                        Link
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows_html}
                  </tbody>
                </table>
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:24px 40px; border-top:1px solid #2d3748; text-align:center;">
              <p style="margin:0; color:#4a5568; font-size:12px; line-height:1.7;">
                This alert was generated automatically by the
                <strong style="color:#667eea;">Job Alert Monitor</strong> running on GitHub Actions.<br>
                Checking 142 startup companies every 4 hours · Mon – Sat<br>
                <em>You're receiving this because you set up this alert system.</em>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
    return html


def _esc(text: str) -> str:
    """HTML-escape a string for safe embedding in email HTML."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def send_email(new_jobs: list[dict]) -> None:
    """
    Send an HTML email alert listing all new internship openings via Gmail SMTP.

    Credentials are read from env vars GMAIL_USER and GMAIL_APP_PASSWORD.
    If credentials are not set, a warning is logged and the function returns early.

    Args:
        new_jobs: List of job dicts to include in the email.
    """
    gmail_user = os.environ.get("GMAIL_USER", "").strip()
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()

    if not gmail_user or not gmail_password:
        logger.warning(
            "GMAIL_USER or GMAIL_APP_PASSWORD not set — skipping email. "
            "Set these environment variables to enable email alerts."
        )
        return

    today_str = date.today().strftime("%B %d, %Y")
    subject = f"🚨 {len(new_jobs)} New Internship Opening(s) Found! — {today_str}"
    html_body = _build_html_email(new_jobs)

    # Build MIME message manually (no external deps)
    boundary = "===============job_alert_boundary=="
    msg_lines = [
        f"From: Job Alert Monitor <{gmail_user}>",
        f"To: {RECIPIENT_EMAIL}",
        f"Subject: {subject}",
        "MIME-Version: 1.0",
        f'Content-Type: multipart/alternative; boundary="{boundary}"',
        "",
        f"--{boundary}",
        'Content-Type: text/plain; charset="utf-8"',
        "Content-Transfer-Encoding: 7bit",
        "",
        f"{len(new_jobs)} new internship opening(s) detected. "
        "Please view this email in an HTML-capable client to see the full details.",
        "",
        f"--{boundary}",
        'Content-Type: text/html; charset="utf-8"',
        "Content-Transfer-Encoding: 7bit",
        "",
        html_body,
        "",
        f"--{boundary}--",
    ]
    raw_message = "\r\n".join(msg_lines).encode("utf-8")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, RECIPIENT_EMAIL, raw_message)
        logger.info("✅ Email sent to %s with %d job(s).", RECIPIENT_EMAIL, len(new_jobs))
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "Gmail authentication failed. "
            "Ensure GMAIL_APP_PASSWORD is a valid App Password (not your regular password)."
        )
    except smtplib.SMTPException as exc:
        logger.error("Failed to send email: %s", exc)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    """
    Orchestrates the full job-check pipeline:
    1. Load previously seen job IDs from seen_jobs.json.
    2. For each company, scrape LinkedIn (fallback: Google) for intern postings.
    3. Collect genuinely new jobs not in seen_jobs.json.
    4. If new jobs found: send email alert, save updated seen_jobs.json.
    5. Print a summary log line.
    """
    logger.info("═" * 60)
    logger.info("Job Alert Monitor starting — checking %d companies.", len(COMPANIES))
    logger.info("═" * 60)

    approved_companies = load_company_whitelist()
    seen_jobs: set[str] = load_seen_jobs()
    all_new_jobs: list[dict] = []
    errors: int = 0

    for idx, company in enumerate(COMPANIES, start=1):
        logger.info("[%d/%d] Checking: %s", idx, len(COMPANIES), company)
        try:
            jobs = get_linkedin_jobs(company)

            # Fallback to Google if LinkedIn returned nothing
            if not jobs:
                logger.info("  → LinkedIn empty, trying Google fallback...")
                jobs = get_google_jobs(company)

            # Filter to only truly new jobs that match the candidate profile
            for job in jobs:
                key = job["job_id"]
                title = job.get("title", "")
                company_name = job.get("company", "")
                normalized_company = normalize_company_name(company_name)

                logger.info("Company: %s", company_name)
                logger.info("Normalized: %s", normalized_company)
                if normalized_company not in approved_companies:
                    logger.info("Whitelist: NO")
                    logger.info("Skipping job.")
                    continue

                logger.info("Whitelist: YES")

                if not is_relevant_job(title):
                    logger.info("  ⏭ SKIP: %s @ %s (not a strong match)", title, company_name)
                    continue

                if key and key not in seen_jobs:
                    all_new_jobs.append(job)
                    seen_jobs.add(key)
                    logger.info("  ✦ NEW: %s @ %s (%s)", title, company_name, key)

        except Exception as exc:
            errors += 1
            logger.warning("Unexpected error for %s: %s", company, exc)

        # Polite delay between companies to avoid bot detection
        sleep_secs = random.uniform(3, 6)
        time.sleep(sleep_secs)

    # ─── Results ──────────────────────────────────────────────────────────────
    logger.info("═" * 60)
    logger.info(
        "Checked %d companies. Found %d new job(s). Errors: %d.",
        len(COMPANIES), len(all_new_jobs), errors,
    )

    if all_new_jobs:
        send_email(all_new_jobs)
        save_seen_jobs(seen_jobs)
        logger.info("State saved. All done. ✅")
    else:
        logger.info("No new jobs found — no email sent, seen_jobs.json unchanged.")

    logger.info("═" * 60)


if __name__ == "__main__":
    main()
