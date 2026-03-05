from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"


def ask(prompt: str, default: str) -> str:
    value = input(f"{prompt} [{default}]: ").strip()
    return value if value else default


def ask_bool(prompt: str, default: bool) -> bool:
    default_text = "yes" if default else "no"
    value = input(f"{prompt} [{default_text}]: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "true", "1", "on"}


def build_env_lines() -> list[str]:
    print("\n=== Email Agent Setup Wizard ===")
    print("This will generate/update .env for your environment.\n")

    os_choice = ask("Environment OS (windows/mac/linux)", "windows")
    backend = ask("Model backend (ollama/openai/custom)", "ollama").lower()

    if backend == "openai":
        openai_api_key = ask("OPENAI_API_KEY", "your-openai-api-key")
        openai_base_url = ask("OPENAI_BASE_URL", "https://api.openai.com/v1")
        triage_model = ask("OPENAI_MODEL_TRIAGE", "gpt-4.1-mini")
        draft_model = ask("OPENAI_MODEL_DRAFT", "gpt-4.1-mini")
    elif backend == "custom":
        openai_api_key = ask("OPENAI_API_KEY (for your compatible endpoint)", "changeme")
        openai_base_url = ask("OPENAI_BASE_URL", "http://localhost:11434/v1")
        triage_model = ask("OPENAI_MODEL_TRIAGE", "qwen3.5:9b")
        draft_model = ask("OPENAI_MODEL_DRAFT", triage_model)
    else:
        openai_api_key = ask("OPENAI_API_KEY", "ollama")
        openai_base_url = ask("OPENAI_BASE_URL", "http://localhost:11434/v1")
        triage_model = ask("OPENAI_MODEL_TRIAGE", "qwen3.5:9b")
        draft_model = ask("OPENAI_MODEL_DRAFT", triage_model)

    suspicious_conf = ask("SUSPICIOUS_CONFIDENCE_THRESHOLD", "0.80")
    suspicious_signals = ask("SUSPICIOUS_MIN_SIGNALS", "2")

    trusted_domains = ask(
        "TRUSTED_SENDER_DOMAINS (comma-separated, optional)",
        "",
    )
    trusted_emails = ask(
        "TRUSTED_SENDER_EMAILS (comma-separated, optional)",
        "",
    )

    credentials_file = ask("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    token_file = ask("GOOGLE_TOKEN_FILE", "token.json")
    log_level = ask("LOG_LEVEL", "INFO")
    max_emails = ask("MAX_EMAILS_PER_RUN", "10")
    max_email_age_hours = ask("MAX_EMAIL_AGE_HOURS (0 disables age filter)", "12")
    include_read_inbox = ask_bool("INCLUDE_READ_INBOX_EMAILS", False)
    inbox_subject_contains = ask(
        "INBOX_SUBJECT_CONTAINS (optional; helps limit backfill scope)",
        "",
    )

    category_labeling_enabled = ask_bool("CATEGORY_LABELING_ENABLED", True)
    exclude_already_labeled = ask_bool("EXCLUDE_ALREADY_LABELED", True)

    print("\nMap topic labels to your Gmail labels (press Enter to keep defaults):")
    label_personal_direct = ask("LABEL_PERSONAL_DIRECT", "Personal & Direct")
    label_finance = ask("LABEL_FINANCE", "Finance")
    label_sales_outreach = ask("LABEL_SALES_OUTREACH", "Sales & Outreach")
    label_events_calendar = ask("LABEL_EVENTS_CALENDAR", "Events & Calendar")
    label_action_required = ask("LABEL_ACTION_REQUIRED", "Action Required")
    label_newsletters = ask("LABEL_NEWSLETTERS", "Newsletters")
    label_security_admin = ask("LABEL_SECURITY_ADMIN", "Security & Admin")
    label_professional_network = ask("LABEL_PROFESSIONAL_NETWORK", "Professional Network")
    label_receipts_billing = ask("LABEL_RECEIPTS_BILLING", "Receipts & Billing")
    label_saas_tools = ask("LABEL_SAAS_TOOLS", "SaaS & Tools")

    lines = [
        "# OpenAI-compatible model endpoint",
        f'OPENAI_API_KEY="{openai_api_key}"',
        f'OPENAI_BASE_URL="{openai_base_url}"',
        f'OPENAI_MODEL_TRIAGE="{triage_model}"',
        f'OPENAI_MODEL_DRAFT="{draft_model}"',
        'OPENAI_AGENTS_DISABLE_TRACING="true"',
        "",
        "# Suspicious classification quality gate",
        f'SUSPICIOUS_CONFIDENCE_THRESHOLD="{suspicious_conf}"',
        f'SUSPICIOUS_MIN_SIGNALS="{suspicious_signals}"',
        "",
        "# Trusted senders (comma-separated; optional)",
        f'TRUSTED_SENDER_DOMAINS="{trusted_domains}"',
        f'TRUSTED_SENDER_EMAILS="{trusted_emails}"',
        "",
        "# Gmail OAuth local files",
        f'GOOGLE_CREDENTIALS_FILE="{credentials_file}"',
        f'GOOGLE_TOKEN_FILE="{token_file}"',
        "",
        "# Runtime",
        f'LOG_LEVEL="{log_level}"',
        f'MAX_EMAILS_PER_RUN="{max_emails}"',
        f'MAX_EMAIL_AGE_HOURS="{max_email_age_hours}"',
        f'INCLUDE_READ_INBOX_EMAILS="{"true" if include_read_inbox else "false"}"',
        f'INBOX_SUBJECT_CONTAINS="{inbox_subject_contains}"',
        "",
        "# Labeling behavior",
        f'CATEGORY_LABELING_ENABLED="{"true" if category_labeling_enabled else "false"}"',
        f'EXCLUDE_ALREADY_LABELED="{"true" if exclude_already_labeled else "false"}"',
        "",
        "# Map topic labels to your existing Gmail labels",
        f'LABEL_PERSONAL_DIRECT="{label_personal_direct}"',
        f'LABEL_FINANCE="{label_finance}"',
        f'LABEL_SALES_OUTREACH="{label_sales_outreach}"',
        f'LABEL_EVENTS_CALENDAR="{label_events_calendar}"',
        f'LABEL_NEWSLETTERS="{label_newsletters}"',
        f'LABEL_SECURITY_ADMIN="{label_security_admin}"',
        f'LABEL_PROFESSIONAL_NETWORK="{label_professional_network}"',
        f'LABEL_RECEIPTS_BILLING="{label_receipts_billing}"',
        f'LABEL_SAAS_TOOLS="{label_saas_tools}"',
        "",
        "# Overlay label applied when action is REPLY",
        f'LABEL_ACTION_REQUIRED="{label_action_required}"',
        "",
        f'# Setup hint: OS={os_choice}',
    ]

    return lines


def main() -> None:
    lines = build_env_lines()
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote {ENV_PATH}")
    print("Next: run `python -m app.main`")


if __name__ == "__main__":
    main()
