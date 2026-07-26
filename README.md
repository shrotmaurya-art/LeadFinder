# LeadFinder

## Setup

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.ai) running locally

### Install dependencies
```bash
pip install -r requirements.txt
```

### Install Playwright browser
```bash
playwright install chromium
```
On Linux, use `playwright install --with-deps chromium` instead — the `--with-deps` flag installs required system libraries via apt. On macOS and Windows the plain command above is sufficient.

## Compliance Notes

1. **TRAI DLT and Meta policies.** Bulk commercial SMS in India generally requires
   TRAI Distributed Ledger Technology (DLT) registration. WhatsApp business
   messaging outside a user-initiated 24-hour session requires Meta's Business
   Messaging Policy compliance and approved message templates. For these reasons
   LeadFinder keeps sending **manual and low-volume** — it generates drafts and
   opens your email/WhatsApp client but never automates dispatch.

2. **Opt-out.** LeadFinder honours opt-out requests immediately. When a contact
   replies "STOP" or otherwise asks to be removed, the lead is marked via
   `mark_opt_out()` and transitioned to "Closed" so no further outreach is
   attempted.

3. **Public data only.** LeadFinder scrapes only publicly listed business
   contact information (Google Maps listings, public websites). It never
   purchases lists or scrapes private/personal data.

4. **Not legal advice.** The above is a summary provided for convenience, not
   legal advice. Regulations change — always verify the current rules that apply
   to your jurisdiction and use case before scaling volume or automating sends.
