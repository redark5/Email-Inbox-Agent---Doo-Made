from __future__ import annotations

import json
import logging

from agents import function_tool

from app.outlook_client import fetch_unread_emails, save_draft_reply


LOGGER = logging.getLogger(__name__)


@function_tool
def list_unread_emails_tool(max_results: int = 10) -> str:
    """
    Fetch unread Gmail inbox messages and return a JSON array string.

    Returns objects with keys: id, threadId, from, subject, snippet, body.
    """

    emails = fetch_unread_emails(max_results=max_results)
    return json.dumps(emails, ensure_ascii=False)


@function_tool
def save_reply_draft_tool(message_id: str, reply_text: str) -> str:
    """
    Save a Gmail draft reply for message_id and return a JSON result string.
    """

    draft_id = save_draft_reply(message_id=message_id, reply_text=reply_text)
    result = {"status": "ok", "draft_id": draft_id}
    LOGGER.info("Draft tool created draft_id=%s for message_id=%s.", draft_id, message_id)
    return json.dumps(result, ensure_ascii=False)
