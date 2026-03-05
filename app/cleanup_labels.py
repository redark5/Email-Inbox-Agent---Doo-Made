from __future__ import annotations

import argparse
import logging

from app.gmail_client import delete_label_if_exists, resolve_existing_label_name


LOGGER = logging.getLogger(__name__)

LEGACY_LABELS = (
    "AI/IGNORE",
    "AI/REPLY",
    "AI/SUSPICIOUS",
    "AI/Processed",
    "ORG/1-Action",
    "ORG/2-Waiting-For",
    "ORG/3-Calendar",
    "ORG/4-Reference",
    "ORG/5-Someday-Maybe",
    "ORG/9-Suspicious",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete legacy labels created by older versions of this repo."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without making changes.",
    )
    parser.add_argument(
        "--label",
        action="append",
        default=[],
        help="Additional label name to delete (can be provided multiple times).",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    args = parse_args()

    labels_to_check = [*LEGACY_LABELS, *(args.label or [])]
    checked = 0
    found = 0
    deleted = 0

    for label in labels_to_check:
        checked += 1
        existing = resolve_existing_label_name(label)
        if not existing:
            LOGGER.info("Not found: %s", label)
            continue

        found += 1
        if args.dry_run:
            LOGGER.info("[dry-run] Would delete: %s", existing)
            continue

        if delete_label_if_exists(existing):
            deleted += 1
            LOGGER.info("Deleted: %s", existing)
        else:
            LOGGER.info("Not deleted (already missing): %s", existing)

    LOGGER.info(
        "Cleanup summary | checked=%s | found=%s | deleted=%s | dry_run=%s",
        checked,
        found,
        deleted,
        args.dry_run,
    )


if __name__ == "__main__":
    main()
