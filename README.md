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
Copy `.env.example` to `.env` and set your target cities and categories:
```bash
cp .env.example .env
```
Key variables (see `config.py` for all options):

| Variable               | Default         | Description                              |
|------------------------|-----------------|------------------------------------------|
| `CITIES`               | `""`            | Comma-separated cities to scout (e.g. `Virar,Vasai,Nalasopara`) |
| `CATEGORIES`           | `""`            | Comma-separated categories (e.g. `Cafes, Gyms`) |
| `OLLAMA_MODEL`         | `llama3.1:8b`   | Model for draft generation               |
| `LEAD_SCORE_THRESHOLD` | `40`            | Minimum score to auto-draft a lead       |
| `EMAIL_DAILY_CAP`      | `30`            | Max email sends per day                  |
| `EMAIL_LINK_STYLE`     | `mailto`        | `mailto` (OS default mail app) or `gmail_web` (Gmail web compose) |
| `WHATSAPP_DAILY_CAP`   | `30`            | Max WhatsApp sends per day               |
| `DATA_SOURCE`          | `playwright`    | `playwright` or `google_places`          |
| `NOTIFY_EMAIL`         | `""`            | Email address for operator notifications |
| `SMTP_HOST`            | `smtp.gmail.com`| SMTP server host                         |
| `SMTP_PORT`            | `587`           | SMTP server port                         |
| `SMTP_USER`            | `""`            | SMTP username (usually your email)       |
| `SMTP_PASSWORD`        | `""`            | SMTP password (use an App Password)      |
| `ENABLE_EMAIL_NOTIFY`  | `true`          | Send email notifications after daily run |
| `ENABLE_DESKTOP_NOTIFY`| `true`          | Send desktop notifications after daily run |

> **Note on `EMAIL_LINK_STYLE`:** When set to `gmail_web`, you must already
> be logged into Gmail in your default browser. The link opens a new browser
> tab with Gmail's compose window rather than launching a desktop mail app.
> This bypasses any OS default mail client settings.

### Email notification (Gmail App Password)

If you use Gmail (or most other email providers) for `SMTP_USER` / `SMTP_PASSWORD`,
you **cannot** use your normal account password. Gmail requires a 16-character
**App Password** instead. To generate one:

1. Enable **2-Step Verification** on your Google account
   (https://myaccount.google.com/security).
2. Go to **App passwords**
   (https://myaccount.google.com/apppasswords).
3. Select **Mail** and your device, then click **Generate**.
4. Copy the 16-character password into `SMTP_PASSWORD` in your `.env` file.

Other providers (Outlook, Yahoo, etc.) have similar App Password or
less-secure-apps requirements — consult their documentation.

## Running

### Full daily pipeline
```bash
python scripts/run_daily.py
```
This runs the complete workflow: scout Google Maps for new leads across all
configured cities and categories, audit each business's online presence, score
them, generate AI-drafted email and WhatsApp messages, and transition qualifying
leads to "Ready to Contact". Duplicates are detected automatically.

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

- **Reply classification.** Inbound email/WhatsApp replies are not yet
  classified. Planned: auto-detect "STOP", meeting requests, questions, and
  update the CRM status accordingly.
- **Quote generation.** LeadFinder does not yet generate quotes or
  proposals. A future module will produce personalised quotes based on
  audit findings.
- **Analytics dashboard.** Charts, conversion funnels, and per-campaign
  reporting are planned for a future release.
