# Email Inbox Agent (OpenAI Agents SDK + Gmail API)

Python email agent that triages unread Gmail messages, applies productivity labels, and creates Gmail reply drafts.

- Stack: `openai-agents-python` + Gmail API OAuth2
- Model backend: OpenAI API or any OpenAI-compatible endpoint (including Ollama)
- Safety: creates drafts only, never auto-sends

## What Happens When New Emails Arrive

Each run (`python -m app.main`) does this:

1. Reads inbox emails (unread-only by default; can include read emails for backfill/testing).
2. Triage agent decides:
   - `IGNORE`
   - `REPLY`
   - `SUSPICIOUS`
3. Triage agent assigns one topic label:
   - `Personal & Direct`
   - `Finance`
   - `Sales & Outreach`
   - `Events & Calendar`
   - `Newsletters`
   - `Security & Admin`
   - `Professional Network`
   - `Receipts & Billing`
   - `SaaS & Tools`
4. App applies exactly one topic label (exclusive among managed topic labels).
5. If action is `REPLY`, app also applies `Action Required` as an overlay label.
6. For `REPLY`, draft agent writes a short reply and saves it as a Gmail draft in the same thread.
7. Logs summary counts to stdout.

## Project Structure

```text
.
|- README.md
|- pyproject.toml
|- requirements.txt
|- .env.example
`- app/
   |- __init__.py
   |- agents.py
   |- cleanup_labels.py
   |- config.py
   |- gmail_client.py
   |- main.py
   |- setup_wizard.py
   |- tools.py
   `- workflows.py
```

## Requirements

- Python 3.11+
- Google Cloud project with Gmail API enabled
- Gmail OAuth desktop client JSON (`credentials.json`)
- Model backend:
  - OpenAI API key, or
  - local Ollama endpoint

## Setup (Step-by-Step)

### 1) Create venv and install

Windows PowerShell:

```powershell
py -3 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Generate `.env` interactively

```bash
python -m app.setup_wizard
```

The wizard asks up front for:

- OS/environment
- model backend (`ollama` / `openai` / custom endpoint)
- model names
- suspicious confidence rules
- trusted sender domains/emails
- Gmail file paths
- label mapping for your existing labels (including `Action Required` overlay label)

### 3) Add Gmail OAuth file

Place OAuth client JSON in project root as `credentials.json`.

Google Cloud quick path:

1. Open [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select project
3. Enable Gmail API
4. Configure OAuth consent screen
5. Create OAuth Client ID of type **Desktop app**
6. Download JSON as `credentials.json`

### 4) Run the app

```bash
python -m app.main
```

First run opens browser consent and writes `token.json`.

## Local LLM (Ollama) Example

```bash
ollama pull qwen3.5:9b
ollama serve
```

Set in `.env`:

```env
OPENAI_API_KEY="ollama"
OPENAI_BASE_URL="http://localhost:11434/v1"
OPENAI_MODEL_TRIAGE="qwen3.5:9b"
OPENAI_MODEL_DRAFT="qwen3.5:9b"
OPENAI_AGENTS_DISABLE_TRACING="true"
```

If `ollama serve` says port `11434` is already in use, Ollama is already running. Just keep it running and execute the agent.

## Existing Label Mapping

Configure these in `.env` to match your Gmail labels:

- `LABEL_PERSONAL_DIRECT`
- `LABEL_FINANCE`
- `LABEL_SALES_OUTREACH`
- `LABEL_EVENTS_CALENDAR`
- `LABEL_NEWSLETTERS`
- `LABEL_SECURITY_ADMIN`
- `LABEL_PROFESSIONAL_NETWORK`
- `LABEL_RECEIPTS_BILLING`
- `LABEL_SAAS_TOOLS`
- `LABEL_ACTION_REQUIRED` (overlay label for `REPLY` items)

If your Gmail label names include emojis, the app resolves labels by normalized text so plain names still map correctly.

## Remove Legacy Labels from Older Versions

Dry run:

```bash
python -m app.cleanup_labels --dry-run
```

Delete legacy labels:

```bash
python -m app.cleanup_labels
```

This removes old `AI/...` and `ORG/...` labels from prior logic.

## Configuration Reference

Core:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL_TRIAGE`
- `OPENAI_MODEL_DRAFT`
- `OPENAI_AGENTS_DISABLE_TRACING`

Triage quality gates:

- `SUSPICIOUS_CONFIDENCE_THRESHOLD` (0.0-1.0)
- `SUSPICIOUS_MIN_SIGNALS` (int >= 1)
- `TRUSTED_SENDER_DOMAINS` (CSV)
- `TRUSTED_SENDER_EMAILS` (CSV)

Gmail:

- `GOOGLE_CREDENTIALS_FILE`
- `GOOGLE_TOKEN_FILE`

Runtime:

- `LOG_LEVEL`
- `MAX_EMAILS_PER_RUN`
- `INCLUDE_READ_INBOX_EMAILS` (`false` by default; set `true` for backfill/testing)
- `INBOX_SUBJECT_CONTAINS` (optional subject filter; useful with include-read mode)
- `CATEGORY_LABELING_ENABLED`
- `EXCLUDE_ALREADY_LABELED` (set `false` when you intentionally want to reprocess already-labeled emails)

## Run Continuously (24/7)

This app is run-per-execution. For always-on behavior, schedule it every few minutes.

### Windows Task Scheduler

Use action:

```text
Program/script: C:\Windows\System32\cmd.exe
Arguments: /c cd /d "C:\path\to\repo" && ".\.venv\Scripts\python.exe" -m app.main >> ".\logs\agent.log" 2>&1
```

### macOS launchd

Use `StartInterval` (for example 300 seconds) in a LaunchAgent plist and run:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.emailinbox.agent.plist
launchctl enable gui/$(id -u)/com.emailinbox.agent
launchctl kickstart -k gui/$(id -u)/com.emailinbox.agent
```

## Security Notes

- Do not commit `.env`, `credentials.json`, or `token.json`.
- Keep `.env.example` with placeholders only.
- Every user should provide their own OAuth and model credentials.
