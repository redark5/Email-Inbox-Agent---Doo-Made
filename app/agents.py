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


def build_triage_agent() -> Agent:
    config = load_config()
    profile = (
        f"\nContext: You are assisting {config.user_name}, {config.user_title}. "
        f"Their areas of expertise include {config.user_expertise}. "
        "Use this context when judging whether an email is relevant or requires a reply."
        if config.user_name else ""
    )
    # OpenAI models support structured output; Ollama small models do not
    use_structured = config.llm_provider == "openai"
    if use_structured:
        return Agent[TriageDecision](
            name="EmailTriageAgent",
            model=config.openai_model_triage,
            instructions=(
                "You are an email triage assistant. "
                "Classify the email and return a structured decision."
                + profile
            ),
            output_type=TriageDecision,
        )
    return Agent[str](
        name="EmailTriageAgent",
        model=config.openai_model_triage,
        instructions=(
            "You are an email triage assistant.\n\n"
            "Classify the email with action and category. Reply with JSON only, no extra text.\n\n"
            "Actions: IGNORE, REPLY, SUSPICIOUS\n"
            "Categories: PERSONAL_DIRECT, FINANCE, SALES_OUTREACH, EVENTS_CALENDAR, "
            "NEWSLETTERS, SECURITY_ADMIN, PROFESSIONAL_NETWORK, RECEIPTS_BILLING, SAAS_TOOLS\n\n"
            "Output format:\n"
            "{\"action\": \"REPLY\", \"category\": \"PERSONAL_DIRECT\", "
            "\"confidence\": 0.9, \"suspicious_signals\": [], \"reason\": \"short reason\"}"
            + profile
        ),
        output_type=str,
    )


def build_draft_agent() -> Agent[str]:
    config = load_config()
    profile_instructions = config.user_context or (
        f"You are writing on behalf of {config.user_name}, {config.user_title}. "
        f"Their expertise includes {config.user_expertise}."
        if config.user_name else ""
    )
    return Agent[str](
        name="EmailDraftAgent",
        model=config.openai_model_draft,
        instructions=(
            f"{profile_instructions}\n\n"
            "Write a short, clear, professional reply in plain text.\n"
            "Sign off with the sender's name and title.\n"
            "Return only the reply body text.\n"
            "Do not include quoted original message.\n"
            "Do not include markdown."
        ),
        output_type=str,
    )
