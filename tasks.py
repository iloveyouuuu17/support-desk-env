"""Ticket datasets and ground-truth answers for each task."""
from __future__ import annotations
from typing import Any, Dict, List
from models import Ticket

# ── Task 1: ticket-classify (easy) ─────────────────────────────────────────
CLASSIFY_TICKETS: List[Ticket] = [
    Ticket(
        id="TCK-001",
        subject="Double charged on my invoice this month",
        body=(
            "Hello, I noticed my credit card was charged $99 twice this month for my "
            "Premium subscription. The first charge was on the 1st and another appeared "
            "on the 3rd. I checked my bank statement and both are clearly from your company. "
            "Please help me get a refund for the duplicate charge as soon as possible."
        ),
        customer_name="Alice Johnson",
        customer_tier="premium",
        account_age_days=365,
        previous_tickets=2,
        timestamp="2024-01-15T10:23:00Z",
    )
]

CLASSIFY_ANSWERS: Dict[str, Dict[str, str]] = {
    "TCK-001": {"category": "billing", "priority": "high"},
}

# ── Task 2: ticket-triage (medium) ─────────────────────────────────────────
TRIAGE_TICKETS: List[Ticket] = [
    Ticket(
        id="TCK-101",
        subject="URGENT: Production API completely down — all customers affected",
        body=(
            "Our entire production system is down. All API calls are returning 500 errors. "
            "We have 50,000 active users who cannot access the service right now. "
            "This started 20 minutes ago. We are an enterprise customer and this is causing "
            "massive revenue loss every minute. PLEASE ESCALATE IMMEDIATELY."
        ),
        customer_name="Bob Smith",
        customer_tier="enterprise",
        account_age_days=730,
        previous_tickets=15,
        timestamp="2024-01-15T09:00:00Z",
    ),
    Ticket(
        id="TCK-102",
        subject="How do I export my data to CSV?",
        body=(
            "Hi, I'm trying to export my data but I can't find the export button anywhere. "
            "I've looked in the dashboard and settings but no luck. "
            "Can you point me in the right direction? Thanks!"
        ),
        customer_name="Carol Davis",
        customer_tier="free",
        account_age_days=30,
        previous_tickets=0,
        timestamp="2024-01-15T09:05:00Z",
    ),
    Ticket(
        id="TCK-103",
        subject="Refund not received after 3 weeks",
        body=(
            "I requested a refund 3 weeks ago for order #ORD-789 totaling $250. "
            "I have sent 5 follow-up emails and nobody has responded. "
            "This is completely unacceptable. I need this resolved TODAY "
            "or I will dispute the charge with my bank."
        ),
        customer_name="David Wilson",
        customer_tier="premium",
        account_age_days=180,
        previous_tickets=8,
        timestamp="2024-01-15T09:10:00Z",
    ),
    Ticket(
        id="TCK-104",
        subject="Webhooks broken after your update yesterday",
        body=(
            "Since your platform update yesterday, our webhooks have completely stopped working. "
            "We are getting 403 Forbidden errors: [AuthError: Invalid signature on webhook payload]. "
            "This is blocking all our automated workflows. We are a premium customer and "
            "this needs to be fixed ASAP — our team is blocked."
        ),
        customer_name="Eve Martinez",
        customer_tier="premium",
        account_age_days=400,
        previous_tickets=6,
        timestamp="2024-01-15T09:15:00Z",
    ),
    Ticket(
        id="TCK-105",
        subject="Where can I find your pricing information?",
        body=(
            "Hello, I would like to learn more about your pricing plans. "
            "Could you send me a link to the pricing page or let me know the plans available? "
            "Thanks."
        ),
        customer_name="Frank Lee",
        customer_tier="free",
        account_age_days=1,
        previous_tickets=0,
        timestamp="2024-01-15T09:20:00Z",
    ),
]

TRIAGE_ANSWERS: Dict[str, Dict[str, str]] = {
    "TCK-101": {"priority": "critical", "department": "escalation"},
    "TCK-102": {"priority": "low",      "department": "tier1"},
    "TCK-103": {"priority": "high",     "department": "billing"},
    "TCK-104": {"priority": "high",     "department": "tier2"},
    "TCK-105": {"priority": "low",      "department": "tier1"},
}

# ── Task 3: ticket-respond (hard) ──────────────────────────────────────────
RESPOND_TICKETS: List[Ticket] = [
    Ticket(
        id="TCK-201",
        subject="Cannot reset my password — locked out for 2 days",
        body=(
            "I have been trying to reset my password for 2 days now. "
            "The password reset email never arrives — I checked spam too. "
            "I am completely locked out of my account and have important project data there. "
            "Please help urgently."
        ),
        customer_name="Grace Kim",
        customer_tier="premium",
        account_age_days=200,
        previous_tickets=1,
        timestamp="2024-01-15T08:00:00Z",
    ),
    Ticket(
        id="TCK-202",
        subject="Want to upgrade our team to Enterprise plan",
        body=(
            "Our team has grown to 50 people and we need the Enterprise plan features, "
            "specifically SSO, dedicated support SLA, and volume pricing. "
            "Can someone help us get started with the upgrade? "
            "We would also like to discuss custom contract terms."
        ),
        customer_name="Henry Brown",
        customer_tier="free",
        account_age_days=90,
        previous_tickets=2,
        timestamp="2024-01-15T08:30:00Z",
    ),
    Ticket(
        id="TCK-203",
        subject="Extremely disappointed — 4th attempt to resolve billing issue",
        body=(
            "This is my fourth attempt to get help with my billing issue (original ticket #TCK-198). "
            "I have been waiting over a week with no resolution. "
            "Your SLA promises 24-hour response for Premium customers. "
            "This is completely unacceptable and I am seriously considering switching to a competitor."
        ),
        customer_name="Iris Chen",
        customer_tier="premium",
        account_age_days=500,
        previous_tickets=12,
        timestamp="2024-01-15T08:45:00Z",
    ),
]

COMPANY_CONTEXT: str = """
=== COMPANY SUPPORT POLICY & KNOWLEDGE BASE ===

PASSWORD RESET:
- Instruct customer to check spam/junk folder first.
- If not received within 10 minutes, support can manually trigger a reset via admin panel.
- Direct URL: /account/reset-password
- Escalate to engineering if manual trigger also fails.

PLAN UPGRADES TO ENTERPRISE:
- Enterprise upgrades are handled by the Sales team.
- Contact: sales@company.com or 1-800-555-COMPANY
- Enterprise includes: SSO, dedicated account manager, 4-hour SLA, volume pricing.
- A discovery call is required before finalizing Enterprise contracts.

SLA RESPONSE TIMES:
- Free tier: 72 hours
- Premium: 24 hours
- Enterprise: 4 hours

REFUNDS:
- Standard refunds: 5–7 business days after approval.
- If >14 days since request: escalate to billing@company.com with urgency flag.
- Offer sincere apology and expedited processing commitment.

TONE GUIDELINES:
- Always address customer by first name.
- Acknowledge the issue and any frustration empathetically.
- Provide clear, actionable next steps.
- Offer to follow up or escalate if needed.
- Sign off: "Best regards, [Support Agent Name] | Customer Support Team | support@company.com"
"""

# Required elements graders check for (keywords per element per ticket)
RESPOND_REQUIRED_ELEMENTS: Dict[str, Dict[str, List[str]]] = {
    "TCK-201": {
        "greeting":        ["grace", "hi grace", "hello grace", "dear grace"],
        "acknowledgment":  ["understand", "sorry", "apologize", "frustrat", "locked out", "inconvenience", "2 days", "two days"],
        "solution":        ["spam", "reset", "/account/reset", "manual", "trigger", "admin", "10 min", "10 minutes", "re-send", "resend"],
        "next_steps":      ["let us know", "contact", "reply", "reach out", "follow up", "help you", "anything else"],
        "closing":         ["regards", "sincerely", "support team", "best regards", "support@"],
    },
    "TCK-202": {
        "greeting":        ["henry", "hi henry", "hello henry", "dear henry"],
        "acknowledgment":  ["enterprise", "congratulat", "great news", "excited", "team has grown", "50"],
        "solution":        ["sales", "sales@", "1-800", "discovery call", "sso", "volume pricing", "dedicated"],
        "next_steps":      ["contact sales", "email", "call", "schedule", "get in touch", "reach out to"],
        "closing":         ["regards", "sincerely", "support team", "best regards", "support@"],
    },
    "TCK-203": {
        "greeting":        ["iris", "hi iris", "hello iris", "dear iris"],
        "acknowledgment":  ["apologize", "sincerely sorry", "unacceptable", "understand your frustrat", "sla", "24-hour", "24 hour"],
        "solution":        ["escalat", "billing", "priorit", "immedi", "resolve", "tck-198", "expedit"],
        "next_steps":      ["within", "hours", "today", "personally", "follow up", "update you", "update by"],
        "closing":         ["regards", "sincerely", "support team", "best regards", "support@"],
    },
}
