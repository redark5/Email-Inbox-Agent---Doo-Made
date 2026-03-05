from __future__ import annotations

import logging
from collections import Counter

from app.config import configure_openai_client, load_config, setup_logging
from app.workflows import run_drafting_for_replies, run_triage_and_print


LOGGER = logging.getLogger(__name__)


def main() -> None:
    config = load_config()
    setup_logging(config.log_level)

    try:
        configure_openai_client(config)
    except Exception as exc:
        LOGGER.exception("OpenAI configuration failed: %s", exc)
        raise

    triage_results = run_triage_and_print(max_results=config.max_emails_per_run)
    run_drafting_for_replies(triage_results)

    counts = Counter(item.get("action", "UNKNOWN") for item in triage_results)
    LOGGER.info(
        "Summary | total=%s | IGNORE=%s | REPLY=%s | SUSPICIOUS=%s",
        len(triage_results),
        counts.get("IGNORE", 0),
        counts.get("REPLY", 0),
        counts.get("SUSPICIOUS", 0),
    )


if __name__ == "__main__":
    main()
