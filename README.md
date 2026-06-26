# 🚨 Job Alert Monitor

An automated, **zero-cost** system that monitors **142 Indian startup companies** for new SDE and Android internship openings every 4 hours and instantly emails you whenever a new position is detected.

Built with Python + GitHub Actions — no paid APIs, no Selenium, no cloud costs.

---

## What This Does

The script (`checker.py`) scrapes LinkedIn Jobs for each of the 142 tracked companies, filtering for internship postings published in the last 24 hours. If LinkedIn's public pages return no results (rate-limit or block), it automatically falls back to a Google search. Any newly discovered jobs — ones not seen in previous runs — are compiled into a rich HTML email and sent to `crazymohit468@gmail.com` via Gmail SMTP. Seen job IDs are stored in `seen_jobs.json` and committed back to the repository after each run, ensuring you never receive duplicate alerts.

---

## Setup

### 1. Fork or Clone This Repository

```bash
git clone https://github.com/YOUR_USERNAME/job-alert-monitor.git
cd job-alert-monitor
```

Then push it to your own GitHub repository.

### 2. Enable GitHub Actions

- Go to your repository on GitHub.
- Click the **Actions** tab.
- If prompted, click **"I understand my workflows, go ahead and enable them"**.

The workflow will now run automatically on schedule (every 4 hours, Monday–Saturday).

### 3. Add GitHub Secrets

The script needs two secrets to send email. **Never commit these to your code.**

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
2. Add the following two secrets:

| Secret Name          | Value                              |
|----------------------|------------------------------------|
| `GMAIL_USER`         | Your Gmail address (e.g. `you@gmail.com`) |
| `GMAIL_APP_PASSWORD` | Your 16-character Gmail App Password (see below) |

### 4. How to Get a Gmail App Password

> ⚠️ **You must have 2-Step Verification enabled on your Google account first.**

1. Go to your Google Account → **Security** (https://myaccount.google.com/security)
2. Under *"How you sign in to Google"*, click **2-Step Verification** and enable it if not already done.
3. Return to Security and search for **"App passwords"** (or go to https://myaccount.google.com/apppasswords)
4. Select app: **Mail** → Select device: **Other (Custom name)** → Enter `Job Alert Bot` → Click **Generate**
5. Copy the **16-character password** shown (spaces don't matter) — this is your `GMAIL_APP_PASSWORD`.

### 5. Manual Trigger

To run the monitor immediately without waiting for the schedule:

1. Go to your repo → **Actions** tab
2. Click **"Job Alert Monitor"** in the left sidebar
3. Click **"Run workflow"** → **"Run workflow"** (green button)

---

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run with email (set env vars first)
export GMAIL_USER="you@gmail.com"
export GMAIL_APP_PASSWORD="your_16_char_app_password"
python checker.py

# Run without email (will scrape and log, but skip sending)
python checker.py
```

If `GMAIL_USER` or `GMAIL_APP_PASSWORD` are not set, the script will still run the full scrape and log all discovered jobs — it just skips sending the email and prints a warning.

---

## Project Structure

```
job-alert-monitor/
├── checker.py                      # Main scraper + email script
├── requirements.txt                # Python dependencies
├── seen_jobs.json                  # Persistent state (auto-updated by bot)
└── .github/
    └── workflows/
        └── job_alert.yml           # GitHub Actions schedule definition
```

---

## LinkedIn Scraping — Limitations & Fixes

LinkedIn aggressively blocks scrapers. Here's what to know:

| Issue | What Happens | Fix |
|---|---|---|
| **Soft block (429)** | LinkedIn returns HTTP 429 | Script auto-retries with exponential backoff (up to 3 times) |
| **Hard block (empty results)** | LinkedIn returns 200 but 0 job cards | Script falls back to Google search automatically |
| **Total block (CAPTCHA)** | Google also returns empty | That company is skipped for that run; next run may succeed |
| **User-Agent detection** | Bot fingerprinting | Script rotates through 5 realistic browser User-Agents |

### If you're seeing 0 results consistently:

1. **Run locally first** — GitHub's IP range may be blocked while your home IP is not.
2. **Increase the delay** — Edit `sleep_secs = random.uniform(3, 6)` in `main()` to a larger range like `(8, 15)`.
3. **Use a proxy** (if you have one) — You can add `proxies={"https": "http://your-proxy:port"}` to the `requests.get()` call in `_fetch_with_retry`.
4. **Consider Apify or ScrapingBee** — Both have free tiers if scraping becomes unreliable (this would require small code changes).

---

## Schedule

The monitor runs at these UTC times on Monday through Saturday:

```
00:00, 04:00, 08:00, 12:00, 16:00, 20:00  (UTC)
```

In IST (UTC+5:30): `05:30, 09:30, 13:30, 17:30, 21:30, 01:30`

Sunday is intentionally excluded (most startups don't post on weekends).

---

## Tracked Companies (142)

Appsmith · ToolJet · Hoppscotch · SigNoz · Hasura · Supabase · Postman · Razorpay · Juspay · Zeta · Meesho · Swiggy · Zepto · CRED · ShareChat · Koo · Pocket FM · Stage · Rooter · Chingari · Krutrim · Sarvam AI · Mad Street Den · SigTuple · Uniphore · Yellow.ai · Rephrase.ai · Ganit · Fi Money · Jar · Slice · Navi · Uni Cards · Open Financial Technologies · Rupeek · Perfios · Banyan Cloud · Airlearn · Nbyula · DrinkPrime · SkilloVilla · Turbostart · 2070 Health · Outplay · Ati Motors · Peppermint Robotics · Masai School · Newton School · Scaler · FunctionUp · ClearFeed · Infilect · 100ms · ARTPARK · CloudSEK · Openhouse · Eloelo · Vymo · Zycus · Leap Finance · Instawork · EarnIn · SWARA · demtech.ai · Gamtus · Senzcraft · Zaimler · Playo · Triplespeed · Bibha AI Labs · Groww · Upstox · CoinDCX · BrowserStack · Freshworks · Chargebee · Zoho · Whatfix · Capillary · Darwinbox · Unacademy · Vedantu · Byjus · PhysicsWallah · Testbook · Toppr · Coding Ninjas · Scaler Academy · InterviewBit · GeekyAnts · Livspace · Urban Company · NoBroker · Housing · MagicBricks · Ola Electric · Bounce · Ather Energy · Yulu · Rapido · Delhivery · Shadowfax · BlackBuck · Rivigo · Porter · Locus · Shipsy · Pickrr · ElasticRun · OfBusiness · Dunzo · Pocketly · Credgenics · Fampay · Simpl · OkCredit · Khatabook · Udaan · Infra.Market · Bizongo · DealShare · CityMall · Trella · Loadshare · FarEye · Ninjacart · Frnd · Turnip · Loco · Bolo Live · Kubeapps · M365Consult · Ekagga Technology · NewSpace Research

---

*Built with ❤️ using Python, BeautifulSoup, smtplib, and GitHub Actions.*
