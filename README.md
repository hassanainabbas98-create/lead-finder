# Business Opportunity Finder

A professional, modern web application for discovering local businesses, analyzing their observable digital presence, and prioritizing qualified prospects for web development, online booking systems, and AI automation services.

Built with **Python 3.12**, **FastAPI**, **SQLAlchemy 2.x**, **SQLite**, **Jinja2 templates**, and **Bootstrap 5**. Runs 100% locally on Windows without requiring Docker, cloud databases, or paid API keys.

---

## 1. Project Purpose & Services Offered

Business Opportunity Finder helps digital agencies and freelance engineers prospect and qualify local businesses based on visible digital gaps:

* **Custom Website Development & Modernization:** Prospects with no website listed in public registries or broken/inaccessible sites.
* **Online Booking & Appointment Scheduling Systems:** Clinics, salons, barber shops, restaurants, and hospitality businesses lacking online booking widgets.
* **Customer Support Chatbots & WhatsApp Automation:** Businesses with high customer query volumes but no detectable live chat launchers or automated inquiry channels.
* **AI Voice-Call Agents:** Phone-centric businesses (restaurants for reservations, clinics for appointments, service contractors) that can benefit from after-hours AI call reception.
* **Industry Management Systems:** Specialized software for restaurants, hotels, schools, dental practices, and real estate agencies.

---

## 2. Architecture & Tech Stack

```
                   +---------------------------------------------+
                   |          Browser / User Interface           |
                   |    Bootstrap 5.3 + Jinja2 + Vanilla JS      |
                   +---------------------+-----------------------+
                                         | HTTP / JSON / SSE
                                         v
                   +---------------------------------------------+
                   |             FastAPI Application             |
                   |   (Lifespan, Security Headers, Middleware)  |
                   +----+----------------+------------------+----+
                        |                |                  |
                        v                v                  v
               +----------------+  +---------------+  +---------------+
               | Web Routers    |  | Core Services |  | Security &    |
               | - Dashboard    |  | - Overpass OSM|  | Background    |
               | - Search       |  | - Safe Audit  |  | - SSRF Guard  |
               | - Leads/Lists  |  | - Detectors   |  | - Safe CSV    |
               | - Tasks        |  | - Scoring     |  | - ThreadPool  |
               | - Export/Jobs  |  | - Recommend   |  |   Job Manager |
               +----------------+  +---------------+  +---------------+
                        |                |                  |
                        +----------------+------------------+
                                         | SQLAlchemy 2.0 ORM
                                         v
                   +---------------------------------------------+
                   |               SQLite Database               |
                   |           (opportunity_finder.db)           |
                   +---------------------------------------------+
```

### Stack Components:
* **Backend:** Python 3.12, FastAPI, Uvicorn (ASGI)
* **Database:** SQLite with SQLAlchemy 2.x ORM
* **Frontend:** Jinja2 templates, Bootstrap 5.3 (SaaS theme: light canvas `#f8fafc`, white cards `#ffffff`, slate text `#0f172a`, emerald green accents `#10b981`), Bootstrap Icons, Vanilla JS
* **Data Discovery:** OpenStreetMap via community Overpass API (with server rotation across 3 mirrors, client-side rate-limiting, and cached geocoding)
* **Website Audit:** Requests, BeautifulSoup4, and custom regex extractors with strict SSRF protection (loopback, private IPv4/IPv6, cloud metadata blocking)
* **Background Worker:** In-process, thread-safe `ThreadPoolExecutor` job manager tracking progress percentages and error states
* **Export:** RFC 4180-compliant CSV streaming with formula injection sanitization (`=`, `+`, `-`, `@` escaping)
* **Testing:** pytest, AnyIO, FastAPI TestClient (35 passing automated tests)

---

## 3. Directory Structure

```
Lead_generation_Website/
├── .env.example
├── .env
├── .gitignore
├── requirements.txt
├── run.py                          # Windows-friendly launcher with reloader
├── README.md                       # Comprehensive project documentation
├── opportunity_finder.db           # Local SQLite database
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app factory, lifespan, security middleware
│   ├── config.py                   # Pydantic BaseSettings configuration
│   ├── database.py                 # SQLite engine, sessionmaker, default seeds
│   ├── models/
│   │   ├── __init__.py
│   │   ├── business.py             # Business & BusinessContact models
│   │   ├── audit.py                # WebsiteAudit model
│   │   ├── lead.py                 # SavedLead, LeadList, LeadListItem models
│   │   ├── task.py                 # FollowUpTask model
│   │   ├── rules.py                # ServiceRule model
│   │   └── job.py                  # SearchJob & AuditJob models
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── search.py               # Search request & response schemas
│   │   ├── lead.py                 # Lead management & batch save schemas
│   │   ├── audit.py                # Website audit & batch audit schemas
│   │   └── task.py                 # Follow-up task schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── discovery/
│   │   │   ├── __init__.py
│   │   │   ├── overpass_client.py  # Multi-mirror Overpass API client with retry logic
│   │   │   ├── geocoding.py        # Nominatim geocoder with caching and rate limits
│   │   │   ├── tag_mappings.py     # Industry category to OSM tag mapping dictionary
│   │   │   └── service.py          # Discovery orchestrator and deduplication engine
│   │   ├── website/
│   │   │   ├── __init__.py
│   │   │   ├── ssrf_guard.py       # SSRF protection: private IP & DNS rebinding checks
│   │   │   ├── checker.py          # Safe HTTP client, redirect validator, timeout cap
│   │   │   ├── contacts.py         # Regex contact extraction (emails, phones, socials)
│   │   │   ├── detectors.py        # Booking, chatbot, ordering, and viewport detectors
│   │   │   └── service.py          # Website audit orchestrator & persistence
│   │   ├── scoring/
│   │   │   ├── __init__.py
│   │   │   └── engine.py           # Transparent 0-100 opportunity scoring engine
│   │   ├── recommendation/
│   │   │   ├── __init__.py
│   │   │   └── engine.py           # Service recommendation and sales pitch generator
│   │   ├── jobs/
│   │   │   ├── __init__.py
│   │   │   ├── manager.py          # Thread-safe BackgroundJobManager
│   │   │   └── tasks.py            # Async worker functions for discovery & batch audits
│   │   └── export/
│   │       ├── __init__.py
│   │       └── csv_exporter.py     # Safe CSV formula injection escaping
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── dashboard.py            # Overview KPIs, priority charts, recent leads
│   │   ├── search.py               # Live OSM discovery search & multi-select actions
│   │   ├── leads.py                # Pipeline management, lead profile, batch saving
│   │   ├── lists.py                # Custom campaign lists and list items
│   │   ├── tasks.py                # Follow-up tasks & callback schedule
│   │   ├── audit.py                # Digital presence audit history & single URL inspector
│   │   ├── export.py               # Safe CSV export center with segment filters
│   │   ├── jobs.py                 # Background jobs API for async processing
│   │   ├── settings.py             # Industry-to-service mapping rules
│   │   └── about.py                # OpenStreetMap attribution & data disclosures
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css           # Custom SaaS stylesheet (emerald accents, responsive)
│   │   └── js/
│   │       └── app.js              # Reusable toast notifications and confirmation modals
│   └── templates/
│       ├── base.html               # Base layout with collapsible sidebar and navigation
│       ├── dashboard.html          # Metric stat cards and recent lead table
│       ├── search.html             # Business discovery form, multi-select, batch actions
│       ├── leads.html              # Lead prospecting pipeline with filters
│       ├── lead_detail.html        # Comprehensive lead profile, audit history, task schedule
│       ├── lists.html              # Custom campaign lists with lead counts and delete actions
│       ├── tasks.html              # Actionable outreach task calendar
│       ├── audit.html              # Digital presence audit history & manual URL inspector
│       ├── export.html             # CSV download center with targeted campaign filters
│       ├── settings.html           # Industry recommendation rules configuration
│       └── about.html              # OpenStreetMap attribution & data governance
└── tests/
    ├── __init__.py
    ├── conftest.py                 # In-memory SQLite test database and TestClient fixtures
    ├── test_background_jobs.py     # Worker thread execution and background API tests
    ├── test_csv_security.py        # Spreadsheet formula injection sanitization tests
    ├── test_discovery.py           # Overpass normalization and geocoding tests
    ├── test_lead_pipeline_and_export.py # Pipeline, batch saves, list cascades, filtered exports
    ├── test_models.py              # Database relationships and constraint tests
    ├── test_routes.py              # Web page rendering and route tests
    ├── test_scoring_and_recommendations.py # Feature detectors, scoring, pitch hooks tests
    └── test_website_audit.py       # SSRF blocking, contact extraction, and audit flow tests
```

---

## 4. Application Pages & Capabilities

| Page | Route | Description |
|---|---|---|
| **Dashboard** | `/` | Metric cards (Total Discovered, Saved Leads, High Priority, Scheduled Tasks), priority breakdown, recent leads, quick actions. |
| **Find Businesses** | `/search` | Search form (Category, City, Country, Max Results, Website filter), live Overpass API query, multi-select checkboxes, batch save, batch audit, batch export. |
| **My Leads** | `/leads` | Filterable prospecting pipeline (Status: New, To Review, Contacted, Interested, Converted; Priority: High, Medium, Low, Needs Review). |
| **Lead Profile** | `/leads/view/{id}` | Comprehensive 360-degree prospect view: address, contact links, live opportunity score breakdown, recommended agency packages, outreach pitch hook, audit history, custom lists assignment, and inline follow-up tasks. |
| **Saved Lists** | `/lists` | Custom campaign lists (e.g. "Lahore Barber Shops", "Peshawar Clinics") with color badges, lead counts, direct CSV exports, and safe deletion. |
| **Follow-up Tasks** | `/tasks` | Actionable outreach task scheduler with priority badges, due dates, checkbox completion toggling, and associated lead navigation. |
| **Website Audit** | `/audit` | Manual URL reachability check with real-time SSRF inspection, extracted contacts, mobile viewport detection, and audit history table. |
| **Export Center** | `/export` | Safe CSV download hub: All Leads, All Discovered Businesses, Website Audits, High/Medium Priority cohorts, and custom list exports. |
| **Settings** | `/settings` | Transparent industry-to-service mapping rules with editable recommended packages and customized pitch hooks. |
| **About & Data Sources** | `/about` | OpenStreetMap attribution (ODbL), Overpass API etiquette, and honest prospecting limitations. |

---

## 5. Security & Defensive Design

### SSRF (Server-Side Request Forgery) Protection
Before any outbound HTTP request is dispatched in the website audit service:
1. Destination hostname is resolved to all associated IP addresses via DNS.
2. Every resolved IP address is verified against reserved ranges:
   * Loopback (`127.0.0.0/8`, `::1`)
   * Private IPv4 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)
   * Link-local / Cloud Metadata (`169.254.0.0/16`, `fe80::/10`)
   * Carrier-grade NAT (`100.64.0.0/10`)
   * Broadcast and multicast ranges
3. Any redirect targets (`301`, `302`, `307`) are re-validated through the SSRF guard before following.
4. Response body size is strictly capped at **5 MB** with a **10-second timeout** to protect against slowloris and resource exhaustion attacks.

### Spreadsheet Formula Injection Safeguard
To protect users who open exported CSV files in Microsoft Excel, LibreOffice, or Google Sheets:
* All cell values are inspected before serialization.
* Any values beginning with dangerous formula trigger characters (`=`, `+`, `-`, `@`, `\t`, `\r`) are automatically escaped with a leading single quote (`'`).

---

## 6. Setup & Running Options

### Option A: One-Click Windows Launcher (Fastest)
Simply double-click the included file in the folder:
* **`Start_Lead_Finder.bat`**
It starts the server and opens your browser automatically!

---

### Option B: Docker Container (Run on Any Laptop, Zero Setup)
With Docker and Docker Compose installed:
```bash
# Build and run container
docker compose up --build

# Run in background
docker compose up -d
```
Access at **`http://localhost:8000`**. Your SQLite database (`opportunity_finder.db`) is mounted on the host drive so data persists automatically.

---

### Option C: GitHub Backup & Multi-Laptop Setup Guide

To safeguard your project against hardware failure and run it on any laptop:

#### 1. Push to a Private GitHub Repository:
```powershell
git init
git add .
git commit -m "Initial commit of Business Opportunity Finder"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git push -u origin main
```
*(Always choose **Private** on GitHub so your lead pipeline and data remain 100% confidential).*

#### 2. Restore & Run on Any Other Laptop (in 60 seconds):
On any other laptop (Windows, Mac, or Linux):
```bash
git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>
docker compose up --build
```
Everything—Python, libraries, database, and web server—boots immediately in 1 command without installing Python manually!

---

### Option D: Manual Python Virtual Environment
```powershell
# 1. Activate venv
.\venv\Scripts\Activate.ps1

# 2. Run tests
pytest

# 3. Launch server
python run.py
```
Open your browser to: **`http://127.0.0.1:8000`** (or on mobile Wi-Fi at **`http://<your-wifi-ip>:8000`**)

---


## 7. Recommended Prospecting Workflow

1. **Discover:**
   * Navigate to **Find Businesses** (`/search`).
   * Enter a category (e.g. `Barber shops`), City (`Lahore`), and Country (`Pakistan`).
   * Click **Discover Businesses**. OpenStreetMap Overpass servers resolve physical businesses in that area.
2. **Filter & Select:**
   * Select `No Website Listed` to instantly find businesses that lack an official web presence.
   * Use the multi-select checkboxes to highlight targets.
3. **Batch Action:**
   * Click **Save Selected to Leads** to add them to your prospecting pipeline, or assign them to a dedicated campaign list (e.g. *"Lahore Salons Q4"*).
4. **Audit Digital Presence:**
   * For businesses with websites, click **Audit Selected** (or **Audit Website** on the lead's profile).
   * The background worker inspects the site for online booking systems, chatbot scripts, online ordering, mobile viewport tags, and public contact emails/phones.
5. **Pitch & Outreach:**
   * Open the lead profile (`/leads/view/{id}`) to view the rule-based **Opportunity Score** (0-100), the **Recommended Digital Offerings**, and the generated **Pitch Value Hook**.
   * Schedule a **Follow-up Task** (e.g. *"Call owner regarding online booking system"*).
   * Record client responses, phone notes, and update pipeline status (`Contacted`, `Interested`, `Converted`).
6. **Export:**
   * Go to **Export Center** (`/export`) to download sanitized CSV files for CRM importing or client tracking.

---

## 8. OpenStreetMap Attribution & Responsible Usage

* Data is &copy; [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), made available under the **Open Database License (ODbL)**.
* Discovery queries respect community Overpass API servers by utilizing rotating mirror servers, client-side rate-limiting, and cached geocoding.
* The application does not scrape Google Maps web pages or circumvent external access restrictions.
* Prospecting information is collected exclusively from public observable records and ethical public contact channels.
