"""
Inference script for SupportDeskEnv.

Runs an LLM agent against all 3 tasks and emits [START]/[STEP]/[END] logs.

Environment variables:
    API_BASE_URL   LLM endpoint  (default: HF Inference Router)
    MODEL_NAME     Model ID      (default: Qwen/Qwen2.5-72B-Instruct)
    HF_TOKEN       API key
    OPENAI_API_KEY Fallback API key
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import textwrap
from typing import Any, Dict, List, Optional

from openai import OpenAI

from environment import SupportDeskEnv
from models import Action

# ── Configuration ──────────────────────────────────────────────────────────
API_KEY: str = os.getenv("HF_TOKEN") or os.getenv("API_KEY") or ""
API_BASE_URL: str = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME: str = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
# Optional — only needed if using from_docker_image():
LOCAL_IMAGE_NAME: Optional[str] = os.getenv("LOCAL_IMAGE_NAME")
BENCHMARK = "support-desk-env"

TASKS = ["ticket-classify", "ticket-triage", "ticket-respond"]
MAX_STEPS: Dict[str, int] = {
    "ticket-classify": 5,
    "ticket-triage":   15,
    "ticket-respond":  15,
}
SUCCESS_THRESHOLD = 0.4

# ── Logging ────────────────────────────────────────────────────────────────

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    err = error if error else "null"
    # Collapse newlines in action string for single-line log
    action_oneline = action.replace("\n", " ").replace("\r", "")
    print(
        f"[STEP] step={step} action={action_oneline} reward={reward:.2f} "
        f"done={str(done).lower()} error={err}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


# ── System prompts ─────────────────────────────────────────────────────────

SYSTEM_PROMPTS: Dict[str, str] = {
    "ticket-classify": textwrap.dedent("""
        You are an expert customer support classifier with 10 years of experience.

        CATEGORIES (pick exactly one):
        - billing   → payment issues, charges, invoices, refunds, subscriptions, pricing
        - technical → bugs, errors, outages, API issues, integration problems, webhooks
        - account   → login, password, account access, profile, permissions, SSO
        - general   → how-to questions, feature requests, documentation, feedback
        - spam      → promotional, irrelevant, automated, test messages

        PRIORITY (pick exactly one):
        - critical  → production down, ALL users affected, data loss, enterprise SLA breach
        - high      → paying customer blocked, refund >2 weeks overdue, partial outage
        - medium    → non-blocking bug, degraded performance, frustrated but not blocked
        - low       → general question, info request, nice-to-have, free tier user

        DECISION RULES:
        1. When in doubt between billing/technical, check if money is mentioned → billing
        2. Enterprise customer + any outage = critical (even if minor)
        3. "Double charge", "charged twice", "wrong amount" = billing + high
        4. "Can't login", "locked out" = account + high
        5. Premium customer complaining about SLA breach = high minimum

        Output ONLY this JSON (no markdown, no explanation):
        {"action_type": "classify", "ticket_id": "TICKET_ID", "category": "CATEGORY", "priority": "PRIORITY"}
    """).strip(),

    "ticket-triage": textwrap.dedent("""
        You are a senior support operations manager. Route each ticket to the right team.

        DEPARTMENTS:
        - tier1        → General questions, how-to, documentation, pricing info, simple FAQs
        - tier2        → Complex bugs, API issues, webhook failures, technical debugging
        - billing      → Payments, refunds, invoices, subscription changes, charges
        - account_mgmt → Plan upgrades, enterprise sales, cancellations, account closures
        - escalation   → Critical outages, enterprise emergencies, SLA violations, exec escalations

        PRIORITY:
        - critical → Production down / all users affected → ALWAYS route to escalation
        - high     → Blocking issue OR frustrated paying customer OR overdue refund
        - medium   → Non-blocking but needs attention
        - low      → Informational, no urgency

        ROUTING RULES (follow in order):
        1. Enterprise + outage/critical = escalation + critical
        2. Any refund/payment/invoice mention = billing
        3. API/webhook/integration/technical error = tier2
        4. Plan upgrade/enterprise sales/SSO = account_mgmt
        5. General question/pricing/how-to = tier1

        Output ONLY this JSON:
        {"action_type": "triage", "ticket_id": "TICKET_ID", "priority": "PRIORITY", "department": "DEPARTMENT"}
    """).strip(),

    "ticket-respond": textwrap.dedent("""
        You are a senior customer support agent. Write professional, empathetic responses.

        MANDATORY ELEMENTS (ALL must be present):
        1. GREETING: "Dear [FirstName]," or "Hi [FirstName],"
        2. EMPATHY: Acknowledge their frustration/inconvenience explicitly
        3. SOLUTION: Provide specific, actionable steps using the policy KB
        4. NEXT STEPS: Tell them what happens next OR offer to help further
        5. CLOSING: "Best regards, Support Team | support@company.com"

        QUALITY RULES:
        - Use the customer's FIRST NAME (not full name)
        - Reference the specific issue they raised (not generic)
        - Be concise but complete (150-300 words is ideal)
        - Never say "I understand your frustration" alone — add the actual solution immediately after
        - For billing delays: acknowledge the specific amount and apologize
        - For technical issues: give exact steps or escalation path
        - For upgrades: route to sales with contact info

        Output ONLY this JSON (escape quotes in response_text with backslash):
        {"action_type": "respond", "ticket_id": "TICKET_ID", "response_text": "YOUR FULL RESPONSE HERE"}
    """).strip(),
}

# ── LLM helpers ────────────────────────────────────────────────────────────

def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Try to extract a JSON object from LLM output."""
    text = text.strip()
    # Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Find first {...}
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    # Find largest {...} block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return None


def build_user_prompt(task: str, obs_dict: Dict[str, Any]) -> str:
    tickets = obs_dict.get("tickets", [])
    current_id = obs_dict.get("current_ticket_id")
    step = obs_dict.get("step", 0)
    processed = obs_dict.get("processed_count", 0)
    context = obs_dict.get("context", {})

    # Find current ticket
    current_ticket = next((t for t in tickets if t["id"] == current_id), None)
    if current_ticket is None and tickets:
        current_ticket = tickets[0]

    lines = [f"Step: {step}  |  Processed: {processed}  |  Pending: {obs_dict.get('message', '')}"]

    if current_ticket:
        lines += [
            "",
            f"=== CURRENT TICKET: {current_ticket['id']} ===",
            f"Subject    : {current_ticket['subject']}",
            f"Customer   : {current_ticket['customer_name']} ({current_ticket['customer_tier']} tier, "
            f"{current_ticket['account_age_days']} days old, "
            f"{current_ticket['previous_tickets']} prior tickets)",
            f"Body       :\n{current_ticket['body']}",
        ]

    if task == "ticket-respond" and context.get("company_policy"):
        lines += ["", context["company_policy"]]

    lines += ["", "Output your JSON action now:"]
    return "\n".join(lines)


def get_model_action(
    client: OpenAI,
    task: str,
    obs_dict: Dict[str, Any],
    temperature: float = 0.3,
    max_tokens: int = 600,
) -> Dict[str, Any]:
    system_prompt = SYSTEM_PROMPTS[task]
    user_prompt = build_user_prompt(task, obs_dict)

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        raw = (completion.choices[0].message.content or "").strip()
        parsed = _extract_json(raw)
        if parsed:
            return parsed
        print(f"[DEBUG] Could not parse JSON from model output: {raw[:200]!r}", flush=True)
    except Exception as exc:
        print(f"[DEBUG] LLM call failed: {exc}", flush=True)

    # Fallback: return a default action for the current ticket
    current_id = obs_dict.get("current_ticket_id", "")
    if task == "ticket-classify":
        return {"action_type": "classify", "ticket_id": current_id,
                "category": "general", "priority": "medium"}
    if task == "ticket-triage":
        return {"action_type": "triage", "ticket_id": current_id,
                "priority": "medium", "department": "tier1"}
    return {"action_type": "respond", "ticket_id": current_id,
            "response_text": (
                f"Dear Customer, thank you for contacting us. "
                f"We apologize for the inconvenience and will resolve your issue promptly. "
                f"Please let us know if you need further assistance. "
                f"Best regards, Support Team | support@company.com"
            )}


# ── Task runner ────────────────────────────────────────────────────────────

def run_task(client: OpenAI, task: str) -> float:
    env = SupportDeskEnv(task=task)
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task, env=BENCHMARK, model=MODEL_NAME)

    try:
        reset_result = env.reset()
        obs_dict = reset_result.observation.model_dump()

        for step_num in range(1, MAX_STEPS[task] + 1):
            if obs_dict.get("current_ticket_id") is None:
                # All tickets processed
                break

            action_dict = get_model_action(client, task, obs_dict)
            # Compact JSON — no spaces — keeps [STEP] log on a single line
            action_str = json.dumps(action_dict, separators=(",", ":"))

            try:
                action = Action(**action_dict)
            except Exception as exc:
                action = Action(
                    action_type="classify",
                    ticket_id=obs_dict.get("current_ticket_id"),
                    category="general",
                    priority="low",
                )
                action_str = f"FALLBACK(err={exc})"

            step_result = env.step(action)
            reward = step_result.reward
            done = step_result.done
            error = step_result.info.get("error")

            rewards.append(reward)
            steps_taken = step_num

            log_step(step=step_num, action=action_str, reward=reward, done=done, error=error)

            obs_dict = step_result.observation.model_dump()

            if done:
                break

        score = round(min(max(sum(rewards), 0.0), 1.0), 4)
        success = score >= SUCCESS_THRESHOLD

    except Exception as exc:
        print(f"[DEBUG] Task {task!r} error: {exc}", flush=True)
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


# ── Main ───────────────────────────────────────────────────────────────────

async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    all_scores: List[float] = []
    for task in TASKS:
        score = run_task(client, task)
        all_scores.append(score)
        print("", flush=True)  # blank line between tasks

    avg = round(sum(all_scores) / len(all_scores), 4)
    print(
        f"[SUMMARY] tasks={len(all_scores)} "
        + " ".join(f"{t}={s:.2f}" for t, s in zip(TASKS, all_scores))
        + f" avg={avg:.2f}",
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
