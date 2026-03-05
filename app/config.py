from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from agents import set_default_openai_client, set_default_openai_key, set_tracing_disabled
from dotenv import load_dotenv
from openai import AsyncOpenAI


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    openai_api_key: str
    openai_base_url: str
    openai_model_triage: str
    openai_model_draft: str
    openai_agents_disable_tracing: bool

    suspicious_confidence_threshold: float
    suspicious_min_signals: int
    trusted_sender_domains: tuple[str, ...]
    trusted_sender_emails: tuple[str, ...]

    category_labeling_enabled: bool
    exclude_already_labeled: bool
    label_personal_direct: str
    label_finance: str
    label_sales_outreach: str
    label_events_calendar: str
    label_action_required: str
    label_newsletters: str
    label_security_admin: str
    label_professional_network: str
    label_receipts_billing: str
    label_saas_tools: str

    google_credentials_file: Path
    google_token_file: Path
    log_level: str
    max_emails_per_run: int
    include_read_inbox_emails: bool
    inbox_subject_contains: str


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _as_float(value: str | None, default: float) -> float:
    try:
        return float(value or "")
    except (TypeError, ValueError):
        return default


def _as_int(value: str | None, default: int) -> int:
    try:
        return int(value or "")
    except (TypeError, ValueError):
        return default


def _split_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return tuple()
    parts = [part.strip().lower() for part in value.split(",")]
    return tuple(part for part in parts if part)


def load_config() -> Config:
    load_dotenv(override=False)

    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    openai_model_triage = os.getenv("OPENAI_MODEL_TRIAGE", "gpt-4.1-mini").strip()
    openai_model_draft = os.getenv("OPENAI_MODEL_DRAFT", "gpt-4.1-mini").strip()
    openai_agents_disable_tracing = _as_bool(
        os.getenv("OPENAI_AGENTS_DISABLE_TRACING", "true"),
        default=True,
    )

    suspicious_confidence_threshold = _as_float(
        os.getenv("SUSPICIOUS_CONFIDENCE_THRESHOLD", "0.80"),
        default=0.80,
    )
    suspicious_confidence_threshold = max(0.0, min(1.0, suspicious_confidence_threshold))
    suspicious_min_signals = max(1, _as_int(os.getenv("SUSPICIOUS_MIN_SIGNALS", "2"), default=2))
    trusted_sender_domains = _split_csv(os.getenv("TRUSTED_SENDER_DOMAINS", ""))
    trusted_sender_emails = _split_csv(os.getenv("TRUSTED_SENDER_EMAILS", ""))

    category_labeling_enabled = _as_bool(os.getenv("CATEGORY_LABELING_ENABLED", "true"), default=True)
    exclude_already_labeled = _as_bool(os.getenv("EXCLUDE_ALREADY_LABELED", "true"), default=True)

    label_personal_direct = os.getenv("LABEL_PERSONAL_DIRECT", "Personal & Direct").strip()
    label_finance = os.getenv("LABEL_FINANCE", "Finance").strip()
    label_sales_outreach = os.getenv("LABEL_SALES_OUTREACH", "Sales & Outreach").strip()
    label_events_calendar = os.getenv("LABEL_EVENTS_CALENDAR", "Events & Calendar").strip()
    label_action_required = os.getenv("LABEL_ACTION_REQUIRED", "Action Required").strip()
    label_newsletters = os.getenv("LABEL_NEWSLETTERS", "Newsletters").strip()
    label_security_admin = os.getenv("LABEL_SECURITY_ADMIN", "Security & Admin").strip()
    label_professional_network = os.getenv("LABEL_PROFESSIONAL_NETWORK", "Professional Network").strip()
    label_receipts_billing = os.getenv("LABEL_RECEIPTS_BILLING", "Receipts & Billing").strip()
    label_saas_tools = os.getenv("LABEL_SAAS_TOOLS", os.getenv("LABEL_SALES_TOOLS", "SaaS & Tools")).strip()

    google_credentials_file = PROJECT_ROOT / os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    google_token_file = PROJECT_ROOT / os.getenv("GOOGLE_TOKEN_FILE", "token.json")
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    max_emails_per_run = _as_int(os.getenv("MAX_EMAILS_PER_RUN", "10"), default=10)
    include_read_inbox_emails = _as_bool(
        os.getenv("INCLUDE_READ_INBOX_EMAILS", "false"),
        default=False,
    )
    inbox_subject_contains = os.getenv("INBOX_SUBJECT_CONTAINS", "").strip()

    return Config(
        openai_api_key=openai_api_key,
        openai_base_url=openai_base_url,
        openai_model_triage=openai_model_triage,
        openai_model_draft=openai_model_draft,
        openai_agents_disable_tracing=openai_agents_disable_tracing,
        suspicious_confidence_threshold=suspicious_confidence_threshold,
        suspicious_min_signals=suspicious_min_signals,
        trusted_sender_domains=trusted_sender_domains,
        trusted_sender_emails=trusted_sender_emails,
        category_labeling_enabled=category_labeling_enabled,
        exclude_already_labeled=exclude_already_labeled,
        label_personal_direct=label_personal_direct,
        label_finance=label_finance,
        label_sales_outreach=label_sales_outreach,
        label_events_calendar=label_events_calendar,
        label_action_required=label_action_required,
        label_newsletters=label_newsletters,
        label_security_admin=label_security_admin,
        label_professional_network=label_professional_network,
        label_receipts_billing=label_receipts_billing,
        label_saas_tools=label_saas_tools,
        google_credentials_file=google_credentials_file,
        google_token_file=google_token_file,
        log_level=log_level,
        max_emails_per_run=max_emails_per_run,
        include_read_inbox_emails=include_read_inbox_emails,
        inbox_subject_contains=inbox_subject_contains,
    )


def setup_logging(level: str) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )


def configure_openai_client(config: Config) -> None:
    if not config.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required.")

    set_tracing_disabled(config.openai_agents_disable_tracing)
    set_default_openai_key(config.openai_api_key, use_for_tracing=False)
    client = AsyncOpenAI(api_key=config.openai_api_key, base_url=config.openai_base_url)
    set_default_openai_client(client, use_for_tracing=False)
