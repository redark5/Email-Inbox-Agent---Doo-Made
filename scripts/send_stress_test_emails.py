from __future__ import annotations

import base64
from datetime import datetime, timezone
from email.message import EmailMessage

from app.gmail_client import get_gmail_service


TO_EMAIL = "daniel.jindoo@doomade.com"
NOW_TAG = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
PREFIX = f"[AI-STRESS-{NOW_TAG}]"


def build_cases() -> list[dict[str, str]]:
    return [
        {
            "category": "Credit Card Statement",
            "subject": f"{PREFIX} Credit Card Statement Available - March 2026",
            "body": (
                "Hello Daniel,\n\n"
                "Your March 2026 statement is now available.\n"
                "Statement balance: $4,284.13\n"
                "Payment due date: March 22, 2026\n"
                "Minimum payment: $127.00\n\n"
                "You can review detailed transactions in your account portal.\n\n"
                "Banking Ops Team"
            ),
        },
        {
            "category": "Spam / Phishing",
            "subject": f"{PREFIX} Urgent: Confirm your mailbox within 30 minutes",
            "body": (
                "Dear user,\n\n"
                "Your mailbox will be permanently suspended unless you verify now.\n"
                "Click this unofficial link immediately: hxxp://mailbox-check-now.example\n\n"
                "Failure to act will result in data deletion.\n\n"
                "Mail Security Center"
            ),
        },
        {
            "category": "Ecommerce",
            "subject": f"{PREFIX} Your DooMade order DM-49382 has shipped",
            "body": (
                "Hi Daniel,\n\n"
                "Good news, your order DM-49382 is on the way.\n"
                "Carrier: UPS\n"
                "Tracking: 1Z84Y7XX0391821\n"
                "Estimated delivery: March 7, 2026\n\n"
                "Thanks for shopping with us."
            ),
        },
        {
            "category": "Events & Calendar",
            "subject": f"{PREFIX} Invite: Product Roadmap Sync (Fri 2:00 PM)",
            "body": (
                "Hi Daniel,\n\n"
                "Can you confirm attendance for Product Roadmap Sync?\n"
                "Date: Friday, March 6, 2026\n"
                "Time: 2:00 PM - 2:45 PM PT\n"
                "Agenda: Q2 priorities, launch risk review, hiring plan\n\n"
                "Please reply yes/no."
            ),
        },
        {
            "category": "Newsletter",
            "subject": f"{PREFIX} Weekly Growth Newsletter - 12 ideas for creators",
            "body": (
                "Hey Daniel,\n\n"
                "This week:\n"
                "- 3 short-form hooks that doubled engagement\n"
                "- A/B test framework for landing pages\n"
                "- Community retention checklist\n\n"
                "Read when you have time."
            ),
        },
        {
            "category": "Security/Admin",
            "subject": f"{PREFIX} Security alert: New admin login from unknown device",
            "body": (
                "Hello,\n\n"
                "We detected an admin login from a new device.\n"
                "Location: Bucharest, Romania\n"
                "Time: 2026-03-04 13:58 UTC\n\n"
                "If this wasn't you, reset your password and revoke sessions immediately."
            ),
        },
        {
            "category": "Receipts & Billing",
            "subject": f"{PREFIX} Receipt: Payment for DooMade Pro (Invoice #8452)",
            "body": (
                "Hi Daniel,\n\n"
                "Thanks for your payment.\n"
                "Amount: $49.00 USD\n"
                "Invoice: #8452\n"
                "Method: Visa ending 1029\n"
                "Date: March 4, 2026\n\n"
                "Attached invoice is available in your billing portal."
            ),
        },
        {
            "category": "SaaS & Tools",
            "subject": f"{PREFIX} [Status] API incident resolved - elevated latency",
            "body": (
                "Team,\n\n"
                "Today's API latency incident has been resolved.\n"
                "Impact window: 10:14-10:39 PT\n"
                "Root cause: cache node failover\n"
                "Action: no customer intervention required\n\n"
                "Postmortem tomorrow."
            ),
        },
        {
            "category": "Sales Outreach",
            "subject": f"{PREFIX} Quick idea to increase inbound demos by 30%",
            "body": (
                "Hi Daniel,\n\n"
                "I reviewed your site and found 3 funnel fixes that can improve demo conversion.\n"
                "If helpful, I can send a 5-minute teardown video.\n\n"
                "Open to it?"
            ),
        },
        {
            "category": "Professional Networking",
            "subject": f"{PREFIX} Partnership inquiry from Acme Media",
            "body": (
                "Hi Daniel,\n\n"
                "We'd like to discuss a co-marketing campaign for Q2.\n"
                "Could we set up a 20-minute call next week?\n\n"
                "Best,\n"
                "Maya\n"
                "Acme Media"
            ),
        },
        {
            "category": "Action Required",
            "subject": f"{PREFIX} Action required: Sign contractor agreement by Thursday",
            "body": (
                "Hi Daniel,\n\n"
                "Please review and sign the contractor agreement by Thursday EOD.\n"
                "Without signature, finance cannot release the next payment batch.\n\n"
                "Reply if you need redlines."
            ),
        },
        {
            "category": "Travel / Calendar",
            "subject": f"{PREFIX} Flight itinerary confirmed: YVR -> SFO (Mar 18)",
            "body": (
                "Hi Daniel,\n\n"
                "Your flight booking is confirmed.\n"
                "Departure: March 18, 2026 - 08:15 AM PT\n"
                "Return: March 20, 2026 - 06:40 PM PT\n"
                "Booking ref: R7Q9L2\n\n"
                "Please review baggage rules."
            ),
        },
        {
            "category": "SaaS Billing",
            "subject": f"{PREFIX} Renewal reminder: Figma Professional annual plan",
            "body": (
                "Hello Daniel,\n\n"
                "Your annual Figma Professional subscription renews in 5 days.\n"
                "Renewal amount: $192.00\n"
                "Renewal date: March 9, 2026\n\n"
                "No action required unless you want to change seats."
            ),
        },
        {
            "category": "Customer Support",
            "subject": f"{PREFIX} Customer issue: Cannot download invoice PDF",
            "body": (
                "Hi Daniel,\n\n"
                "A customer reports invoice downloads failing with a 500 error.\n"
                "Account: brightpath-studio\n"
                "First seen: 11:22 AM PT\n\n"
                "Can your team investigate and reply with ETA?"
            ),
        },
        {
            "category": "Security / Spear-Phish",
            "subject": f"{PREFIX} Urgent payroll update required before cutoff",
            "body": (
                "Daniel,\n\n"
                "Payroll processing is blocked. Please send your updated banking info now\n"
                "or your salary may be delayed.\n"
                "Use this form immediately: hxxp://secure-payroll-update.example\n\n"
                "HR Department"
            ),
        },
    ]


def send_case(service, case: dict[str, str]) -> str:
    msg = EmailMessage()
    msg["To"] = TO_EMAIL
    msg["Subject"] = case["subject"]
    msg.set_content(case["body"])

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return str(result.get("id", ""))


def main() -> None:
    service = get_gmail_service()
    cases = build_cases()
    print(f"Sending {len(cases)} stress-test emails to {TO_EMAIL} ...")

    sent_ids: list[str] = []
    for index, case in enumerate(cases, start=1):
        message_id = send_case(service, case)
        sent_ids.append(message_id)
        print(
            f"{index:02d}. [{case['category']}] sent | "
            f"subject={case['subject']} | message_id={message_id}"
        )

    print(f"Done. Sent {len(sent_ids)} emails with prefix {PREFIX}")


if __name__ == "__main__":
    main()

