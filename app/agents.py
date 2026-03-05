from __future__ import annotations

from typing import Literal

from agents import Agent
from pydantic import BaseModel, Field

from app.config import load_config
from app.tools import save_reply_draft_tool


class TriageDecision(BaseModel):
    action: Literal["IGNORE", "REPLY", "SUSPICIOUS"]
    category: Literal[
        "PERSONAL_DIRECT",
        "FINANCE",
        "SALES_OUTREACH",
        "EVENTS_CALENDAR",
        "NEWSLETTERS",
        "SECURITY_ADMIN",
        "PROFESSIONAL_NETWORK",
        "RECEIPTS_BILLING",
        "SAAS_TOOLS",
    ]
    confidence: float = Field(
        description="Confidence score from 0.0 to 1.0 for the chosen action.",
        ge=0.0,
        le=1.0,
    )
    suspicious_signals: list[str] = Field(
        default_factory=list,
        description="Concrete risk indicators found when action is SUSPICIOUS.",
    )
    reason: str = Field(description="Short explanation for the decision.")


def build_triage_agent() -> Agent[TriageDecision]:
    config = load_config()
    return Agent[TriageDecision](
        name="EmailTriageAgent",
        model=config.openai_model_triage,
        instructions=(
            "You are an email triage specialist for productivity workflows.\n\n"
            "You will receive exactly one email.\n\n"
            "Assign exactly one action:\n"
            "- IGNORE: no response needed.\n"
            "- REPLY: user should respond and we will draft a reply.\n"
            "- SUSPICIOUS: possible phishing/risky message; user must manually verify.\n\n"
            "Assign exactly one category:\n"
            "- PERSONAL_DIRECT\n"
            "- FINANCE\n"
            "- SALES_OUTREACH\n"
            "- EVENTS_CALENDAR\n"
            "- NEWSLETTERS\n"
            "- SECURITY_ADMIN\n"
            "- PROFESSIONAL_NETWORK\n"
            "- RECEIPTS_BILLING\n"
            "- SAAS_TOOLS\n\n"
            "Rules:\n"
            "- If action is SUSPICIOUS, category should usually be SECURITY_ADMIN.\n"
            "- If action is REPLY, category should typically be ACTION_REQUIRED, EVENTS_CALENDAR, "
            "PERSONAL_DIRECT, PROFESSIONAL_NETWORK, or SALES_OUTREACH.\n"
            "- Include confidence in [0.0, 1.0].\n"
            "- If action is SUSPICIOUS, provide suspicious_signals with concrete evidence (prefer >=2 items).\n\n"
            "Output JSON exactly with:\n"
            "{ \"action\": \"...\", \"category\": \"...\", \"confidence\": 0.0-1.0, "
            "\"suspicious_signals\": [\"...\"], \"reason\": \"...\" }\n"
            "Keep reason concise (one sentence max)."
        ),
        output_type=TriageDecision,
    )


def build_draft_agent() -> Agent[str]:
    config = load_config()
    return Agent[str](
        name="EmailDraftAgent",
        model=config.openai_model_draft,
        instructions=(
            "You are a professional email assistant.\n\n"
            "Given the original email details, write a short, clear, polite reply in plain text.\n"
            "Return only the reply body text.\n"
            "Do not include quoted original message.\n"
            "Do not include markdown.\n"
            "Do not call tools unless the user explicitly asks you to save a draft."
        ),
        tools=[save_reply_draft_tool],
        output_type=str,
    )
