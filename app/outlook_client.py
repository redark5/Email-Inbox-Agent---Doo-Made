from __future__ import annotations

import logging
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

import pythoncom
import win32com.client

from app.config import load_config


LOGGER = logging.getLogger(__name__)

_OUTLOOK: Any = None
_NAMESPACE: Any = None

OL_FOLDER_INBOX = 6
OL_FOLDER_DRAFTS = 16


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def _get_namespace() -> Any:
    global _OUTLOOK, _NAMESPACE
    if _NAMESPACE is not None:
        return _NAMESPACE
    pythoncom.CoInitialize()
    _OUTLOOK = win32com.client.Dispatch("Outlook.Application")
    _NAMESPACE = _OUTLOOK.GetNamespace("MAPI")
    LOGGER.info("Connected to local Outlook via COM.")
    return _NAMESPACE


def _get_folder(folder_type: int) -> Any:
    """Get the inbox or drafts folder for the configured email account."""
    config = load_config()
    ns = _get_namespace()
    email_addr = config.email_address.lower().strip()

    if email_addr:
        for account in ns.Accounts:
            try:
                if account.SmtpAddress.lower() == email_addr:
                    return account.DeliveryStore.GetDefaultFolder(folder_type)
            except Exception:
                continue

    # Fallback to default account folder
    return ns.GetDefaultFolder(folder_type)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _mail_to_dict(mail: Any) -> dict[str, str]:
    try:
        sender_name = getattr(mail, "SenderName", "") or ""
        sender_email = getattr(mail, "SenderEmailAddress", "") or ""
        from_str = f"{sender_name} <{sender_email}>".strip() if sender_name else sender_email
        subject = getattr(mail, "Subject", "") or ""
        body = getattr(mail, "Body", "") or ""
        snippet = body[:200].replace("\n", " ").strip()
        entry_id = getattr(mail, "EntryID", "") or ""
        conversation_id = getattr(mail, "ConversationID", "") or entry_id

        return {
            "id": entry_id,
            "threadId": conversation_id,
            "from": from_str,
            "subject": subject,
            "messageIdHeader": entry_id,
            "snippet": snippet,
            "body": body,
        }
    except Exception as exc:
        LOGGER.warning("Failed to parse mail item: %s", exc)
        return {
            "id": "", "threadId": "", "from": "", "subject": "",
            "messageIdHeader": "", "snippet": "", "body": "",
        }


def _normalize_category(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    cleaned = [ch.lower() for ch in normalized if ch.isalnum() or ch in {" ", "&", "/", "-", "_"}]
    return " ".join("".join(cleaned).split())


# ---------------------------------------------------------------------------
# Email fetching
# ---------------------------------------------------------------------------

def get_email_by_id(entry_id: str) -> dict[str, str]:
    ns = _get_namespace()
    try:
        mail = ns.GetItemFromID(entry_id)
        return _mail_to_dict(mail)
    except Exception as exc:
        LOGGER.warning("Could not fetch message id=%s: %s", entry_id, exc)
        return {
            "id": entry_id, "threadId": "", "from": "", "subject": "",
            "messageIdHeader": entry_id, "snippet": "", "body": "",
        }


def fetch_unread_emails(
    max_results: int = 10,
    exclude_label_name: str | None = None,
    exclude_label_names: list[str] | None = None,
    include_read_inbox: bool = False,
    subject_contains: str | None = None,
    max_age_hours: int = 0,
) -> list[dict[str, str]]:
    inbox = _get_folder(OL_FOLDER_INBOX)
    items = inbox.Items
    items.Sort("[ReceivedTime]", True)  # newest first

    # Build Restrict filter
    config = load_config()
    restrictions: list[str] = []

    if not config.flagged_only and not include_read_inbox:
        restrictions.append("[Unread] = True")

    if max_age_hours > 0 and not config.flagged_only:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        cutoff_local = cutoff.astimezone()
        cutoff_str = cutoff_local.strftime("%m/%d/%Y %I:%M %p")
        restrictions.append(f"[ReceivedTime] >= '{cutoff_str}'")

    if subject_contains and subject_contains.strip():
        safe = subject_contains.strip().replace("'", "")
        restrictions.append(f"[Subject] like '%{safe}%'")

    if restrictions:
        filter_str = " AND ".join(f"({r})" for r in restrictions)
        items = items.Restrict(filter_str)

    # Build exclude set
    exclude_names: list[str] = []
    if exclude_label_name and exclude_label_name.strip():
        exclude_names.append(exclude_label_name.strip())
    for name in exclude_label_names or []:
        if name and name.strip():
            exclude_names.append(name.strip())
    exclude_norm = {_normalize_category(n) for n in exclude_names}

    emails: list[dict[str, str]] = []
    for item in items:
        if len(emails) >= max_results:
            break
        try:
            # Skip non-flagged items when flagged_only mode is on
            if config.flagged_only and getattr(item, "FlagStatus", 0) != 2:
                continue

            # Skip already-categorized items
            if exclude_norm:
                item_cats = {
                    _normalize_category(c.strip())
                    for c in (getattr(item, "Categories", "") or "").split(",")
                    if c.strip()
                }
                if item_cats.intersection(exclude_norm):
                    continue

            data = _mail_to_dict(item)
            if data.get("id"):
                emails.append(data)
        except Exception as exc:
            LOGGER.warning("Skipping mail item: %s", exc)

    mode = "inbox+read" if include_read_inbox else "unread-only"
    age_filter = f"{max_age_hours}h" if max_age_hours > 0 else "disabled"
    LOGGER.info("Fetched %s inbox email(s) | mode=%s | age_filter=%s.", len(emails), mode, age_filter)
    return emails


# ---------------------------------------------------------------------------
# Labeling via Outlook categories
# ---------------------------------------------------------------------------

def apply_action_label(
    message_id: str,
    target_label_name: str,
    all_action_label_names: list[str],
) -> None:
    ns = _get_namespace()
    mail = ns.GetItemFromID(message_id)
    current = [c.strip() for c in (getattr(mail, "Categories", "") or "").split(",") if c.strip()]
    managed_norm = {_normalize_category(n) for n in all_action_label_names}
    kept = [c for c in current if _normalize_category(c) not in managed_norm]
    kept.append(target_label_name)
    mail.Categories = ", ".join(kept)
    mail.Save()
    LOGGER.info("Applied label '%s' to message %s.", target_label_name, message_id)


def add_label_to_message(message_id: str, label_name: str) -> None:
    ns = _get_namespace()
    mail = ns.GetItemFromID(message_id)
    current = [c.strip() for c in (getattr(mail, "Categories", "") or "").split(",") if c.strip()]
    if label_name not in current:
        current.append(label_name)
    mail.Categories = ", ".join(current)
    mail.Save()
    LOGGER.info("Added label '%s' to message %s.", label_name, message_id)


def remove_label_from_message(message_id: str, label_name: str) -> None:
    ns = _get_namespace()
    mail = ns.GetItemFromID(message_id)
    current = [c.strip() for c in (getattr(mail, "Categories", "") or "").split(",") if c.strip()]
    target_norm = _normalize_category(label_name)
    updated = [c for c in current if _normalize_category(c) != target_norm]
    if len(updated) != len(current):
        mail.Categories = ", ".join(updated)
        mail.Save()
        LOGGER.info("Removed label '%s' from message %s.", label_name, message_id)


# ---------------------------------------------------------------------------
# Draft saving via Outlook COM
# ---------------------------------------------------------------------------

def _text_to_html(text: str) -> str:
    """Convert plain text reply to simple HTML paragraphs."""
    import html as html_lib
    lines = html_lib.escape(text.strip()).split("\n")
    html_parts: list[str] = []
    para: list[str] = []
    for line in lines:
        if line.strip():
            para.append(line)
        else:
            if para:
                html_parts.append("<p>" + "<br>".join(para) + "</p>")
                para = []
    if para:
        html_parts.append("<p>" + "<br>".join(para) + "</p>")
    return "\n".join(html_parts)


def save_draft_reply(message_id: str, reply_text: str) -> str:
    ns = _get_namespace()
    mail = ns.GetItemFromID(message_id)
    reply = mail.Reply()
    html_reply = _text_to_html(reply_text.strip())
    existing_html = reply.HTMLBody or ""
    reply.HTMLBody = html_reply + existing_html
    reply.Save()
    draft_id = reply.EntryID
    LOGGER.info("Created draft %s for message %s.", draft_id, message_id)
    return draft_id
