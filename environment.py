"""Core SupportDeskEnv environment."""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple

from graders import grade_classify, grade_response, grade_triage
from models import Action, Observation, ResetResult, StateResult, StepResult, Ticket
from tasks import (
    CLASSIFY_ANSWERS,
    CLASSIFY_TICKETS,
    COMPANY_CONTEXT,
    RESPOND_REQUIRED_ELEMENTS,
    RESPOND_TICKETS,
    TRIAGE_ANSWERS,
    TRIAGE_TICKETS,
)

VALID_TASKS = ["ticket-classify", "ticket-triage", "ticket-respond"]

MAX_STEPS: Dict[str, int] = {
    "ticket-classify": 5,
    "ticket-triage":   15,
    "ticket-respond":  15,
}


class SupportDeskEnv:
    """
    OpenEnv-compatible customer support ticket environment.

    Tasks
    -----
    ticket-classify : Easy  — classify 1 ticket by category + priority
    ticket-triage   : Medium — triage queue of 5 tickets (priority + routing)
    ticket-respond  : Hard   — draft professional responses to 3 tickets
    """

    def __init__(self, task: str = "ticket-classify") -> None:
        if task not in VALID_TASKS:
            raise ValueError(f"task must be one of {VALID_TASKS}, got {task!r}")
        self.task = task
        self._step: int = 0
        self._total_reward: float = 0.0
        self._done: bool = False
        self._processed: List[Dict[str, Any]] = []
        self._tickets: List[Ticket] = []
        self._pending: List[str] = []

    # ── Public API ─────────────────────────────────────────────────────────

    def reset(self) -> ResetResult:
        self._step = 0
        self._total_reward = 0.0
        self._done = False
        self._processed = []

        if self.task == "ticket-classify":
            self._tickets = copy.deepcopy(CLASSIFY_TICKETS)
        elif self.task == "ticket-triage":
            self._tickets = copy.deepcopy(TRIAGE_TICKETS)
        else:  # ticket-respond
            self._tickets = copy.deepcopy(RESPOND_TICKETS)

        self._pending = [t.id for t in self._tickets]
        obs = self._make_obs("Environment ready. Process the ticket(s).")
        return ResetResult(observation=obs)

    def step(self, action: Action) -> StepResult:
        if self._done:
            return StepResult(
                observation=self._make_obs("Episode already finished."),
                reward=0.0,
                done=True,
                info={"error": "episode_done"},
            )

        self._step += 1
        reward, info = self._dispatch(action)
        self._total_reward = round(self._total_reward + reward, 6)

        # Termination checks
        if not self._pending:
            self._done = True
            info.setdefault("message", "All tickets processed.")
        elif self._step >= MAX_STEPS[self.task]:
            self._done = True
            info["timeout"] = f"{len(self._pending)} ticket(s) unprocessed at step limit"

        return StepResult(
            observation=self._make_obs(info.get("message", "")),
            reward=round(reward, 4),
            done=self._done,
            info=info,
        )

    def state(self) -> StateResult:
        return StateResult(
            task=self.task,
            step=self._step,
            total_reward=self._total_reward,
            done=self._done,
            tickets=self._tickets,
            processed=self._processed,
        )

    # ── Internal helpers ───────────────────────────────────────────────────

    def _make_obs(self, message: str) -> Observation:
        context: Dict[str, Any] = {}
        if self.task == "ticket-respond":
            context["company_policy"] = COMPANY_CONTEXT

        return Observation(
            task=self.task,
            step=self._step,
            max_steps=MAX_STEPS[self.task],
            tickets=self._tickets,
            current_ticket_id=self._pending[0] if self._pending else None,
            processed_count=len(self._processed),
            message=message,
            context=context,
        )

    def _dispatch(self, action: Action) -> Tuple[float, Dict[str, Any]]:
        if self.task == "ticket-classify":
            return self._do_classify(action)
        if self.task == "ticket-triage":
            return self._do_triage(action)
        return self._do_respond(action)

    # ── Task handlers ──────────────────────────────────────────────────────

    def _do_classify(self, action: Action) -> Tuple[float, Dict[str, Any]]:
        if action.action_type != "classify":
            return 0.0, {"error": f"expected action_type='classify', got {action.action_type!r}"}
        if not action.ticket_id or not action.category or not action.priority:
            return 0.0, {"error": "classify requires ticket_id, category, and priority"}
        if action.ticket_id not in self._pending:
            return 0.0, {"error": f"ticket {action.ticket_id!r} not in pending queue"}

        score, details = grade_classify(
            action.ticket_id, action.category, action.priority, CLASSIFY_ANSWERS
        )
        self._pending.remove(action.ticket_id)
        self._processed.append(
            {"ticket_id": action.ticket_id, "action": "classify",
             "category": action.category, "priority": action.priority,
             "score": score, "details": details}
        )
        return score, {"message": f"Ticket {action.ticket_id} classified (score={score:.2f})", "details": details}

    def _do_triage(self, action: Action) -> Tuple[float, Dict[str, Any]]:
        if action.action_type != "triage":
            return 0.0, {"error": f"expected action_type='triage', got {action.action_type!r}"}
        if not action.ticket_id or not action.priority or not action.department:
            return 0.0, {"error": "triage requires ticket_id, priority, and department"}
        if action.ticket_id not in self._pending:
            return 0.0, {"error": f"ticket {action.ticket_id!r} not in pending queue"}

        raw_score, details = grade_triage(
            action.ticket_id, action.priority, action.department, TRIAGE_ANSWERS
        )
        # Normalize: 5 tickets each worth 1/5 of total episode score
        n = max(len(TRIAGE_TICKETS), 1)
        norm_score = round(raw_score / n, 6)

        self._pending.remove(action.ticket_id)
        self._processed.append(
            {"ticket_id": action.ticket_id, "action": "triage",
             "priority": action.priority, "department": action.department,
             "raw_score": raw_score, "score": norm_score, "details": details}
        )
        remaining = len(self._pending)
        return norm_score, {
            "message": (
                f"Ticket {action.ticket_id} triaged (raw={raw_score:.2f}, "
                f"norm={norm_score:.2f}). {remaining} ticket(s) remaining."
            ),
            "details": details,
        }

    def _do_respond(self, action: Action) -> Tuple[float, Dict[str, Any]]:
        if action.action_type != "respond":
            return 0.0, {"error": f"expected action_type='respond', got {action.action_type!r}"}
        if not action.ticket_id or not action.response_text:
            return 0.0, {"error": "respond requires ticket_id and response_text"}
        if action.ticket_id not in self._pending:
            return 0.0, {"error": f"ticket {action.ticket_id!r} not in pending queue"}

        raw_score, details = grade_response(
            action.ticket_id, action.response_text, RESPOND_REQUIRED_ELEMENTS
        )
        # Normalize: 3 tickets each worth 1/3 of total episode score
        n = max(len(RESPOND_TICKETS), 1)
        norm_score = round(raw_score / n, 6)

        self._pending.remove(action.ticket_id)
        self._processed.append(
            {"ticket_id": action.ticket_id, "action": "respond",
             "response_length": len(action.response_text),
             "raw_score": raw_score, "score": norm_score, "details": details}
        )
        remaining = len(self._pending)
        return norm_score, {
            "message": (
                f"Response for {action.ticket_id} evaluated (raw={raw_score:.2f}, "
                f"norm={norm_score:.2f}). {remaining} ticket(s) remaining."
            ),
            "details": details,
        }
