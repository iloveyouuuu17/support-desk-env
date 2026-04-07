"""Grading functions for each task type."""
from __future__ import annotations
from typing import Any, Dict, List, Tuple

PRIORITY_ORDER: Dict[str, int] = {"critical": 0, "high": 1, "medium": 2, "low": 3}
VALID_CATEGORIES = {"billing", "technical", "account", "general", "spam"}
VALID_PRIORITIES = {"critical", "high", "medium", "low"}
VALID_DEPARTMENTS = {"tier1", "tier2", "billing", "account_mgmt", "escalation"}

# Department alias normalization
DEPARTMENT_ALIASES: Dict[str, str] = {
    "tier_1": "tier1",
    "tier_2": "tier2",
    "tier 1": "tier1",
    "tier 2": "tier2",
    "tier1_support": "tier1",
    "tier2_support": "tier2",
    "account_management": "account_mgmt",
    "account management": "account_mgmt",
    "account mgmt": "account_mgmt",
}


def _normalize_department(dept: str) -> str:
    d = dept.lower().strip().replace("-", "_")
    return DEPARTMENT_ALIASES.get(d, d)


def grade_classify(
    ticket_id: str,
    category: str,
    priority: str,
    answers: Dict[str, Dict[str, str]],
) -> Tuple[float, Dict[str, Any]]:
    """Score a classify action. Max reward = 1.0."""
    if ticket_id not in answers:
        return 0.0, {"error": f"unknown ticket_id: {ticket_id}"}

    correct = answers[ticket_id]
    score = 0.0
    details: Dict[str, Any] = {}

    # Category: exact match = 0.6 pts
    cat_given = category.lower().strip()
    cat_correct = correct["category"]
    if cat_given == cat_correct:
        score += 0.6
        details["category"] = "correct"
    else:
        details["category"] = f"wrong (expected={cat_correct}, got={cat_given})"

    # Priority: exact = 0.4 pts; within 1 level = 0.2 pts
    pri_given = priority.lower().strip()
    pri_correct = correct["priority"]
    if pri_given == pri_correct:
        score += 0.4
        details["priority"] = "correct"
    elif (
        pri_given in PRIORITY_ORDER
        and pri_correct in PRIORITY_ORDER
        and abs(PRIORITY_ORDER[pri_given] - PRIORITY_ORDER[pri_correct]) == 1
    ):
        score += 0.2
        details["priority"] = "close (within 1 level)"
    else:
        details["priority"] = f"wrong (expected={pri_correct}, got={pri_given})"

    # Scores must be strictly (0, 1) — scale to [0.01, 0.99]
    score = round(0.01 + score * 0.98, 4)
    details["total_score"] = score
    return score, details


def grade_triage(
    ticket_id: str,
    priority: str,
    department: str,
    answers: Dict[str, Dict[str, str]],
) -> Tuple[float, Dict[str, Any]]:
    """Score a triage action. Max raw reward = 1.0 (normalized by caller)."""
    if ticket_id not in answers:
        return 0.0, {"error": f"unknown ticket_id: {ticket_id}"}

    correct = answers[ticket_id]
    score = 0.0
    details: Dict[str, Any] = {}

    # Priority: exact = 0.4; within 1 = 0.2
    pri_given = priority.lower().strip()
    pri_correct = correct["priority"]
    if pri_given == pri_correct:
        score += 0.4
        details["priority"] = "correct"
    elif (
        pri_given in PRIORITY_ORDER
        and pri_correct in PRIORITY_ORDER
        and abs(PRIORITY_ORDER[pri_given] - PRIORITY_ORDER[pri_correct]) == 1
    ):
        score += 0.2
        details["priority"] = "close (within 1 level)"
    else:
        details["priority"] = f"wrong (expected={pri_correct}, got={pri_given})"

    # Department: exact match (with normalization) = 0.6
    dept_given = _normalize_department(department)
    dept_correct = correct["department"]
    if dept_given == dept_correct:
        score += 0.6
        details["department"] = "correct"
    else:
        details["department"] = f"wrong (expected={dept_correct}, got={dept_given})"

    # Scores must be strictly (0, 1) — scale to [0.01, 0.99]
    score = round(0.01 + score * 0.98, 4)
    details["total_score"] = score
    return score, details


def grade_response(
    ticket_id: str,
    response_text: str,
    required_elements: Dict[str, Dict[str, List[str]]],
) -> Tuple[float, Dict[str, Any]]:
    """Score a drafted response. Max raw reward = 1.0 (normalized by caller)."""
    if ticket_id not in required_elements:
        return 0.0, {"error": f"unknown ticket_id: {ticket_id}"}

    text_lower = response_text.lower()
    elements = required_elements[ticket_id]

    weights: Dict[str, float] = {
        "greeting":       0.10,
        "acknowledgment": 0.25,
        "solution":       0.40,
        "next_steps":     0.15,
        "closing":        0.10,
    }

    score = 0.0
    details: Dict[str, Any] = {}

    for element, keywords in elements.items():
        found = any(kw.lower() in text_lower for kw in keywords)
        w = weights.get(element, 0.1)
        if found:
            score += w
            details[element] = "present"
        else:
            details[element] = f"missing (looked for: {keywords[:2]})"

    # Length penalty: a real response should be ≥80 chars
    length = len(response_text.strip())
    if length < 80:
        score *= 0.4
        details["length_penalty"] = f"too short ({length} chars) — 60% penalty applied"
    elif length < 150:
        score *= 0.8
        details["length_penalty"] = f"short ({length} chars) — 20% penalty applied"
    else:
        details["length_ok"] = f"{length} chars — adequate"

    # Scores must be strictly (0, 1) — scale to [0.01, 0.99]
    score = round(0.01 + min(score, 1.0) * 0.98, 4)
    details["total_score"] = score
    return score, details
