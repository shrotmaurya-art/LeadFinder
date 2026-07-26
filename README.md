# LeadFinder

Find and reach out to local businesses in your target market — scout Google
Maps for leads, audit their online presence, score and draft personalised
outreach, and track them through a CRM pipeline.

## Overview

## Setup

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.ai) running locally with a model configured in
  `config.py` (default: `llama3.1:8b`)

### Install dependencies
```bash
pip install -r requirements.txt
```

### Install Playwright browser
```bash
playwright install chromium
```
On Linux, use `playwright install --with-deps chromium` instead — the
`--with-deps` flag installs required system libraries via apt. On macOS and
Windows the plain command above is sufficient.

### Configure environment
Copy `.env.example` to `.env` and set your target city and categories:
```bash
cp .env.example .env
```
Key variables (see `config.py` for all options):

| Variable               | Default         | Description                              |
|------------------------|-----------------|------------------------------------------|
| `CITY`                 | `""`            | City to scout (e.g. `Virar`)             |
| `CATEGORIES`           | `""`            | Comma-separated categories (e.g. `Cafes, Gyms`) |
| `OLLAMA_MODEL`         | `llama3.1:8b`   | Model for draft generation               |
| `LEAD_SCORE_THRESHOLD` | `40`            | Minimum score to auto-draft a lead       |
| `EMAIL_DAILY_CAP`      | `30`            | Max email sends per day                  |
| `WHATSAPP_DAILY_CAP`   | `30`            | Max WhatsApp sends per day               |
| `DATA_SOURCE`          | `playwright`    | `playwright` or `google_places`          |

## Running

### Full daily pipeline
```bash
python scripts/run_daily.py --city Virar --categories Cafes,Gyms
```
This runs the complete workflow: scout Google Maps for new leads, audit each
business's online presence, score them, generate AI-drafted email and WhatsApp
messages, and transition qualifying leads to "Ready to Contact". Duplicates
are detected automatically.

### Dashboard
```bash
streamlit run ui/dashboard.py
```
The dashboard opens in your browser with an **Overview** tab (leads to review,
outreach drafting, send & mark-as-sent) and a **Pipeline** tab (Kanban board
showing every lead by status — drag-style status changes via dropdown selectors
restricted to valid transitions).

### Running steps individually
- **Scout only** — import and call `scout.pipeline.run_scout(city, category, db)`
- **Audit** — `analyzer.audit.run_audit(business, db)`
- **Score** — `analyzer.scorer.score_lead(audit, business)`
- **Generate drafts** — `outreach.email_generator.generate_email(...)` /
  `outreach.whatsapp_generator.generate_whatsapp(...)`
- **Follow-up candidates** — `crm.followups.get_followup_candidates(db)`

### Tests
```bash
pytest tests/
```

## Compliance Notes

1. **TRAI DLT and Meta policies.** Bulk commercial SMS in India generally
   requires TRAI Distributed Ledger Technology (DLT) registration. WhatsApp
   business messaging outside a user-initiated 24-hour session requires Meta's
   Business Messaging Policy compliance and approved message templates. For
   these reasons LeadFinder keeps sending **manual and low-volume** — it
   generates drafts and opens your email/WhatsApp client but never automates
   dispatch.

2. **Opt-out.** LeadFinder honours opt-out requests immediately. When a contact
   replies "STOP" or otherwise asks to be removed, the lead is marked via
   `mark_opt_out()` and transitioned to "Closed" so no further outreach is
   attempted.

3. **Public data only.** LeadFinder scrapes only publicly listed business
   contact information (Google Maps listings, public websites). It never
   purchases lists or scrapes private/personal data.

4. **Not legal advice.** The above is a summary provided for convenience, not
   legal advice. Regulations change — always verify the current rules that
   apply to your jurisdiction and use case before scaling volume or automating
   sends.

## Deployment

See [deploy/README.md](deploy/README.md) for deployment instructions covering
server setup, environment configuration, automated daily runs via cron /
scheduled tasks, and production-adjacent considerations (backups, monitoring).

## Known Limitations / Future Versions

- **Multi-city scouts.** The current scouting pipeline targets a single city
  per run. A future version will support multiple cities with configurable
  schedules.
- **Reply classification.** Inbound email/WhatsApp replies are not yet
  classified. Planned: auto-detect "STOP", meeting requests, questions, and
  update the CRM status accordingly.
- **Quote generation.** LeadFinder does not yet generate quotes or
  proposals. A future module will produce personalised quotes based on
  audit findings.
- **Analytics dashboard.** Charts, conversion funnels, and per-campaign
  reporting are planned for a future release.
