from __future__ import annotations

import json
import logging
from email.utils import parseaddr
from typing import Any

from agents import Runner

from app.agents import TriageDecision, build_draft_agent, build_triage_agent
from app.config import Config, load_config
from app.outlook_client import (
    add_label_to_message,
    apply_action_label,
    fetch_unread_emails,
    get_email_by_id,
    remove_label_from_message,
    save_draft_reply,
)


LOGGER = logging.getLogger(__name__)

VALID_ACTIONS = {"IGNORE", "REPLY", "SUSPICIOUS"}
TOPIC_CATEGORIES = {
    "PERSONAL_DIRECT",
    "FINANCE",
    "SALES_OUTREACH",
    "EVENTS_CALENDAR",
    "NEWSLETTERS",
    "SECURITY_ADMIN",
    "PROFESSIONAL_NETWORK",
    "RECEIPTS_BILLING",
    "SAAS_TOOLS",
}


def _as_probability(value: Any, default: float = 0.0) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, score))


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _normalize_signal_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    signals: list[str] = []
    for item in value:
        if isinstance(item, str):
            text = item.strip()
            if text:
                signals.append(text)
    return signals


def _normalize_single_triage_output(raw_output: Any) -> dict[str, Any]:
    if isinstance(raw_output, TriageDecision):
        decision = raw_output.model_dump()
        return {
            "action": str(decision.get("action", "SUSPICIOUS")).upper(),
            "category": str(decision.get("category", "")).upper(),
            "confidence": _as_probability(decision.get("confidence", 0.0)),
            "suspicious_signals": _normalize_signal_list(decision.get("suspicious_signals", [])),
            "reason": str(decision.get("reason", "")).strip(),
        }

    if isinstance(raw_output, dict):
        return {
            "action": str(raw_output.get("action", "SUSPICIOUS")).upper(),
            "category": str(raw_output.get("category", "")).upper(),
            "confidence": _as_probability(raw_output.get("confidence", 0.0)),
            "suspicious_signals": _normalize_signal_list(raw_output.get("suspicious_signals", [])),
            "reason": str(raw_output.get("reason", "")).strip(),
        }

    if isinstance(raw_output, str):
        text = raw_output.strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return {
                    "action": str(parsed.get("action", "SUSPICIOUS")).upper(),
                    "category": str(parsed.get("category", "")).upper(),
                    "confidence": _as_probability(parsed.get("confidence", 0.0)),
                    "suspicious_signals": _normalize_signal_list(parsed.get("suspicious_signals", [])),
                    "reason": str(parsed.get("reason", "")).strip(),
                }
        except json.JSONDecodeError:
            pass

        upper = text.upper()
        for action in ("REPLY", "IGNORE", "SUSPICIOUS"):
            if action in upper:
                return {
                    "action": action,
                    "category": "",
                    "confidence": 0.5,
                    "suspicious_signals": [],
                    "reason": "Model returned free text; action inferred.",
                }

    return {
        "action": "SUSPICIOUS",
        "category": "SECURITY_ADMIN",
        "confidence": 0.0,
        "suspicious_signals": [],
        "reason": "Model output was invalid; marked for manual review.",
    }


def _sender_identity(email: dict[str, str]) -> tuple[str, str]:
    from_header = email.get("from", "")
    addr = parseaddr(from_header)[1].strip().lower()
    domain = ""
    if "@" in addr:
        domain = addr.split("@", 1)[1]
    return addr, domain


def _is_trusted_sender(config: Config, email: dict[str, str]) -> bool:
    sender_email, sender_domain = _sender_identity(email)
    return sender_email in config.trusted_sender_emails or sender_domain in config.trusted_sender_domains


def _has_reply_request(text: str) -> bool:
    return _contains_any(
        text,
        [
            "please reply",
            "reply yes/no",
            "can you",
            "could you",
            "let me know",
            "open to it",
            "confirm attendance",
            "investigate",
            "reply with eta",
            "need your response",
            "please confirm",
            "sign the",
            "approve",
        ],
    )


def _looks_actionable(email: dict[str, str]) -> bool:
    text = " ".join([email.get("subject", ""), email.get("snippet", ""), email.get("body", "")]).lower()
    if _contains_any(text, ["no action required", "no action needed", "for your records", "fyi"]):
        return False
    return _has_reply_request(text)


def _infer_topic_category(action: str, email: dict[str, str]) -> str:
    if action == "SUSPICIOUS":
        return "SECURITY_ADMIN"

    text = " ".join([email.get("subject", ""), email.get("snippet", ""), email.get("body", "")]).lower()

    if _contains_any(text, ["credit card statement", "statement balance", "minimum payment", "payment due date"]):
        return "FINANCE"
    if _contains_any(text, ["invoice", "receipt", "billing", "charge", "renewal", "order", "tracking", "shipped"]):
        return "RECEIPTS_BILLING"
    if _contains_any(
        text,
        [
            "meeting",
            "invite",
            "calendar",
            "schedule",
            "appointment",
            "flight",
            "itinerary",
            "departure:",
            "return:",
            "booking ref",
        ],
    ):
        return "EVENTS_CALENDAR"
    if _contains_any(text, ["demo", "funnel", "teardown", "pipeline", "lead", "open to it"]):
        return "SALES_OUTREACH"
    if _contains_any(text, ["partnership", "network", "collaborate", "linkedin"]):
        return "PROFESSIONAL_NETWORK"
    if _contains_any(text, ["newsletter", "weekly", "digest", "blog"]):
        return "NEWSLETTERS"
    if _contains_any(text, ["api", "incident", "status", "uptime", "github", "workspace", "tool"]):
        return "SAAS_TOOLS"
    if _contains_any(text, ["security alert", "new admin login", "verify now", "password", "suspended"]):
        return "SECURITY_ADMIN"

    if action == "REPLY":
        return "PERSONAL_DIRECT"
    return "PERSONAL_DIRECT" if "hi daniel" in text else "NEWSLETTERS"


def _normalize_topic_category(category: str, action: str, email: dict[str, str]) -> str:
    if category in TOPIC_CATEGORIES:
        return category
    return _infer_topic_category(action, email)


def _enforce_suspicious_quality(
    *,
    config: Config,
    action: str,
    category: str,
    confidence: float,
    suspicious_signals: list[str],
    reason: str,
    email: dict[str, str],
) -> tuple[str, str, str]:
    if action != "SUSPICIOUS":
        return action, category, reason

    has_strong_evidence = (
        confidence >= config.suspicious_confidence_threshold
        and len(suspicious_signals) >= config.suspicious_min_signals
    )
    if has_strong_evidence:
        return action, category, reason

    downgraded_action = "REPLY" if _looks_actionable(email) else "IGNORE"
    downgraded_category = _infer_topic_category(downgraded_action, email)
    if _is_trusted_sender(config, email):
        downgraded_reason = (
            f"Downgraded from SUSPICIOUS for trusted sender; "
            f"evidence was weak (confidence={confidence:.2f}, signals={len(suspicious_signals)}). "
            f"{reason}"
        ).strip()
        return downgraded_action, downgraded_category, downgraded_reason

    downgraded_reason = (
        f"Downgraded from SUSPICIOUS due to weak evidence "
        f"(confidence={confidence:.2f}, signals={len(suspicious_signals)}). {reason}"
    ).strip()
    return downgraded_action, downgraded_category, downgraded_reason


def _enforce_productivity_overrides(
    *,
    action: str,
    category: str,
    reason: str,
    email: dict[str, str],
) -> tuple[str, str, str]:
    """
    Deterministic business rules to correct recurring small-model mistakes.
    """
    text = " ".join([email.get("subject", ""), email.get("snippet", ""), email.get("body", "")]).lower()

    is_phishing = (
        _contains_any(text, ["urgent", "immediately", "verify now", "mailbox", "password", "banking info"])
        and _contains_any(text, ["hxxp://", "http://", "suspended", "salary may be delayed", "data deletion"])
    )
    if is_phishing:
        return (
            "SUSPICIOUS",
            "SECURITY_ADMIN",
            f"Override: phishing language and malicious-link indicators detected. {reason}".strip(),
        )

    if _contains_any(text, ["flight itinerary", "flight booking", "departure:", "return:", "booking ref"]):
        category = "EVENTS_CALENDAR"
        reason = f"Category override: travel itinerary/calendar details detected. {reason}".strip()
        if not _has_reply_request(text):
            action = "IGNORE"
            reason = f"Action override: informational itinerary with no reply request. {reason}".strip()
        return action, category, reason

    if _contains_any(text, ["credit card statement", "statement balance", "minimum payment", "payment due date"]):
        category = "FINANCE"
        reason = f"Category override: finance statement details detected. {reason}".strip()
        if not _has_reply_request(text):
            action = "IGNORE"
            reason = f"Action override: statement update does not request a response. {reason}".strip()
        return action, category, reason

    if _contains_any(text, ["inbound demos", "funnel", "teardown", "open to it", "lead generation"]):
        category = "SALES_OUTREACH"
        action = "REPLY"
        reason = f"Override: outbound sales pitch requesting response. {reason}".strip()
        return action, category, reason

    if _contains_any(text, ["contractor agreement", "sign the", "redlines", "by thursday", "eod"]):
        category = "PROFESSIONAL_NETWORK"
        action = "REPLY"
        reason = f"Override: contractual workflow requires follow-up. {reason}".strip()
        return action, category, reason

    if _contains_any(text, ["cannot download invoice", "500 error", "investigate", "reply with eta"]):
        category = "RECEIPTS_BILLING"
        action = "REPLY"
        reason = f"Override: billing support incident requests ETA response. {reason}".strip()
        return action, category, reason

    is_billing_renewal = (
        _contains_any(text, ["renewal", "subscription", "renews in", "annual plan"])
        and _contains_any(text, ["amount", "billing", "invoice", "receipt", "payment", "charge"])
    )
    if is_billing_renewal:
        category = "RECEIPTS_BILLING"
        reason = f"Category override: detected billing/subscription renewal. {reason}".strip()
        if _contains_any(
            text,
            [
                "no action required",
                "no action needed",
                "no customer intervention required",
                "unless you want to change",
                "unless you need to change",
            ],
        ):
            action = "IGNORE"
            reason = f"Action override: sender explicitly indicates no action required. {reason}".strip()
        return action, category, reason

    if action == "REPLY" and _contains_any(text, ["no action required", "no action needed"]):
        action = "IGNORE"
        reason = f"Action override: explicit no-action language detected. {reason}".strip()
    return action, category, reason


def _topic_label_map(config: Config) -> dict[str, str]:
    return {
        "PERSONAL_DIRECT": config.label_personal_direct,
        "FINANCE": config.label_finance,
        "SALES_OUTREACH": config.label_sales_outreach,
        "EVENTS_CALENDAR": config.label_events_calendar,
        "NEWSLETTERS": config.label_newsletters,
        "SECURITY_ADMIN": config.label_security_admin,
        "PROFESSIONAL_NETWORK": config.label_professional_network,
        "RECEIPTS_BILLING": config.label_receipts_billing,
        "SAAS_TOOLS": config.label_saas_tools,
    }


def run_triage_and_print(max_results: int = 10) -> list[dict[str, Any]]:
    config = load_config()
    topic_map = _topic_label_map(config)
    managed_topic_labels = list(topic_map.values())
    exclude_labels = (
        list(dict.fromkeys([*managed_topic_labels, config.label_action_required]))
        if config.exclude_already_labeled
        else []
    )

    emails = fetch_unread_emails(
        max_results=max_results,
        exclude_label_names=exclude_labels,
        include_read_inbox=config.include_read_inbox_emails,
        subject_contains=config.inbox_subject_contains,
        max_age_hours=config.max_email_age_hours,
    )
    if not emails:
        LOGGER.info("Triage results (0 emails):")
        return []

    triage_agent = build_triage_agent()
    triage_results: list[dict[str, Any]] = []

    for email in emails:
        email_id = email.get("id", "")
        if not email_id:
            continue

        prompt = (
            "Classify this email.\n\n"
            f"From: {email.get('from', '')}\n"
            f"Subject: {email.get('subject', '')}\n"
            f"Snippet: {email.get('snippet', '')}\n"
            f"Body:\n{email.get('body', '')}\n"
        )

        try:
            result = Runner.run_sync(triage_agent, prompt)
            normalized = _normalize_single_triage_output(result.final_output)
        except Exception as exc:
            LOGGER.warning("Triage failed for id=%s, defaulting to SUSPICIOUS: %s", email_id, exc)
            normalized = {
                "action": "SUSPICIOUS",
                "category": "SECURITY_ADMIN",
                "confidence": 0.0,
                "suspicious_signals": [],
                "reason": "Triage failed; marked for manual review.",
            }

        action = normalized.get("action", "SUSPICIOUS").upper()
        if action not in VALID_ACTIONS:
            action = "SUSPICIOUS"

        category = _normalize_topic_category(
            str(normalized.get("category", "")).upper(),
            action,
            email,
        )

        confidence = _as_probability(normalized.get("confidence", 0.0))
        suspicious_signals = _normalize_signal_list(normalized.get("suspicious_signals", []))
        action, category, reason = _enforce_suspicious_quality(
            config=config,
            action=action,
            category=category,
            confidence=confidence,
            suspicious_signals=suspicious_signals,
            reason=str(normalized.get("reason", "")).strip(),
            email=email,
        )
        action, category, reason = _enforce_productivity_overrides(
            action=action,
            category=category,
            reason=reason,
            email=email,
        )
        category = _normalize_topic_category(category, action, email)

        # Flagged emails are always forced to REPLY
        if config.flagged_only:
            action = "REPLY"
            reason = f"Flagged for follow-up; reply enforced. {reason}".strip()

        triage_results.append(
            {
                "id": email_id,
                "action": action,
                "category": category,
                "confidence": round(confidence, 3),
                "suspicious_signals": suspicious_signals,
                "reason": reason,
            }
        )

        if config.category_labeling_enabled:
            try:
                apply_action_label(
                    message_id=email_id,
                    target_label_name=topic_map[category],
                    all_action_label_names=managed_topic_labels,
                )
                if action == "REPLY":
                    add_label_to_message(email_id, config.label_action_required)
                else:
                    remove_label_from_message(email_id, config.label_action_required)
            except Exception as exc:
                LOGGER.warning(
                    "Labeling failed for message id=%s category=%s action=%s: %s",
                    email_id,
                    category,
                    action,
                    exc,
                )

    LOGGER.info("Triage results (%s emails):", len(triage_results))
    for item in triage_results:
        LOGGER.info(
            "id=%s | action=%s | category=%s | confidence=%.2f | signals=%s | reason=%s",
            item.get("id", ""),
            item.get("action", ""),
            item.get("category", ""),
            float(item.get("confidence", 0.0)),
            len(item.get("suspicious_signals", [])),
            item.get("reason", ""),
        )
    return triage_results


def run_drafting_for_replies(triage_results: list[dict[str, Any]]) -> None:
    draft_agent = build_draft_agent()
    reply_items = [item for item in triage_results if item.get("action") == "REPLY"]

    if not reply_items:
        LOGGER.info("No emails marked for reply. Skipping drafting workflow.")
        return

    LOGGER.info("Drafting replies for %s email(s).", len(reply_items))
    for item in reply_items:
        message_id = item.get("id", "")
        if not message_id:
            continue

        try:
            email_data = get_email_by_id(message_id)
            prompt = (
                "You are replying to an email thread. Read the FULL thread below carefully "
                "to understand the complete context before writing your reply.\n\n"
                f"From: {email_data.get('from', '')}\n"
                f"Subject: {email_data.get('subject', '')}\n\n"
                f"--- Full Thread ---\n{email_data.get('body', '')}\n--- End Thread ---\n\n"
                "Write a short professional reply that directly addresses the latest message "
                "while being aware of the full conversation history above."
            )
            result = Runner.run_sync(draft_agent, prompt)
            reply_text = str(result.final_output).strip()

            if not reply_text:
                LOGGER.warning("Empty draft content for message id=%s. Skipping.", message_id)
                continue

            draft_id = save_draft_reply(message_id=message_id, reply_text=reply_text)
            LOGGER.info(
                "Created draft for message id=%s | subject=%s | draft_id=%s",
                message_id,
                email_data.get("subject", ""),
                draft_id,
            )
        except Exception as exc:
            LOGGER.exception("Failed drafting reply for message id=%s: %s", message_id, exc)
