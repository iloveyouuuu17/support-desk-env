---
title: SupportDeskEnv
emoji: 🎫
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
license: mit
short_description: OpenEnv customer support ticket triage environment
---

# SupportDeskEnv

An **OpenEnv-compatible benchmark** for evaluating AI agents on real-world customer support workflows. Agents must classify, prioritize, route, and draft responses to realistic support tickets — skills directly applicable to production customer service automation.

---

## Why This Benchmark Matters

Customer support is one of the highest-ROI applications for AI agents in enterprise settings. A production support desk handles hundreds of tickets daily; misrouting a critical enterprise outage to Tier 1, or failing to include a solution in a response, has direct business impact. This benchmark:

- Tests **multi-skill reasoning**: classification, routing logic, and long-form generation in one suite
- Uses **partial rewards** so agents receive signal on every step, enabling RL fine-tuning
- Includes **realistic edge cases**: enterprise SLA breaches, overdue refunds, locked-out users
- Is **grounded in real policies**: the knowledge base mirrors actual support runbooks
- Provides **three difficulty tiers** suitable for evaluating models across the capability spectrum

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         HTTP API (FastAPI)                       │
│   /reset  /step  /state  /health  /tasks  /validate             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                   ┌────────▼────────┐
                   │  SupportDeskEnv │  (environment.py)
                   │                 │
                   │  ┌───────────┐  │
                   │  │  tasks.py │  │  ← Ticket datasets + answers
                   │  └─────┬─────┘  │
                   │        │        │
                   │  ┌─────▼─────┐  │
                   │  │ graders.py│  │  ← Scoring logic
                   │  └───────────┘  │
                   │                 │
                   │  ┌───────────┐  │
                   │  │ models.py │  │  ← Pydantic schemas
                   │  └───────────┘  │
                   └─────────────────┘
                            │
                   ┌────────▼────────┐
                   │  inference.py   │  ← LLM agent runner
                   │  (OpenAI-compat │
                   │   client)       │
                   └─────────────────┘
```

**Data flow per step:**
1. Agent calls `POST /step` with a JSON action
2. `SupportDeskEnv._dispatch()` routes to the correct task handler
3. Grader scores the action and returns `(reward, details)`
4. `StepResult` is returned with scalar `reward`, structured `reward_info`, and next `observation`

---

## Tasks

| Task | Difficulty | Max Steps | Tickets | Description |
|------|-----------|-----------|---------|-------------|
| `ticket-classify` | Easy | 5 | 1 | Classify 1 ticket by **category** + **priority** |
| `ticket-triage` | Medium | 15 | 5 | Triage a mixed queue with **routing decisions** |
| `ticket-respond` | Hard | 15 | 3 | Draft professional **responses** using KB context |

---

## Reward Breakdown

Rewards are **partial** — agents receive per-step signal, enabling RL training without sparse episode-end rewards.

### ticket-classify

| Condition | Reward |
|-----------|--------|
| Correct category | +0.60 |
| Correct priority (exact) | +0.40 |
| Priority within 1 level | +0.20 |
| Wrong category | +0.00 |
| Invalid action_type | 0.00 + `penalty: true` in info |

### ticket-triage (per ticket, normalized ÷5)

| Condition | Raw Reward |
|-----------|-----------|
| Correct department | +0.60 |
| Correct priority (exact) | +0.40 |
| Priority within 1 level | +0.20 |
| Wrong action_type | 0.00 + `penalty: true` in info |

### ticket-respond (per ticket, normalized ÷3)

| Element | Weight |
|---------|--------|
| Personalized greeting | 0.10 |
| Issue acknowledgment | 0.25 |
| Solution / actionable steps | 0.40 |
| Next steps / follow-up offer | 0.15 |
| Professional closing | 0.10 |
| Length penalty (<80 chars) | ×0.40 |
| Length penalty (<150 chars) | ×0.80 |

---

## Baseline Scores

Measured with `Qwen/Qwen2.5-72B-Instruct` via HF Inference Router:

| Task | Score | Notes |
|------|-------|-------|
| `ticket-classify` | 0.85 | Occasional priority off-by-one |
| `ticket-triage` | 0.68 | Some confusion on billing vs. tier2 |
| `ticket-respond` | 0.62 | Solution element most often missing |
| **Average** | **0.72** | |

---

## Example Agent Interaction

```
[START] task=ticket-classify env=support-desk-env model=Qwen/Qwen2.5-72B-Instruct

[STEP] step=1 action={"action_type":"classify","ticket_id":"TCK-001","category":"billing","priority":"high"} reward=1.00 done=true error=null

[END] success=true steps=1 score=1.00 rewards=1.00


[START] task=ticket-triage env=support-desk-env model=Qwen/Qwen2.5-72B-Instruct

[STEP] step=1 action={"action_type":"triage","ticket_id":"TCK-101","priority":"critical","department":"escalation"} reward=0.20 done=false error=null
[STEP] step=2 action={"action_type":"triage","ticket_id":"TCK-102","priority":"low","department":"tier1"} reward=0.20 done=false error=null
[STEP] step=3 action={"action_type":"triage","ticket_id":"TCK-103","priority":"high","department":"billing"} reward=0.20 done=false error=null
[STEP] step=4 action={"action_type":"triage","ticket_id":"TCK-104","priority":"high","department":"tier2"} reward=0.20 done=false error=null
[STEP] step=5 action={"action_type":"triage","ticket_id":"TCK-105","priority":"low","department":"tier1"} reward=0.20 done=true error=null

[END] success=true steps=5 score=1.00 rewards=0.20,0.20,0.20,0.20,0.20


[START] task=ticket-respond env=support-desk-env model=Qwen/Qwen2.5-72B-Instruct

[STEP] step=1 action={"action_type":"respond","ticket_id":"TCK-201","response_text":"Hi Grace, ..."} reward=0.30 done=false error=null
[STEP] step=2 action={"action_type":"respond","ticket_id":"TCK-202","response_text":"Dear Henry, ..."} reward=0.27 done=false error=null
[STEP] step=3 action={"action_type":"respond","ticket_id":"TCK-203","response_text":"Dear Iris, ..."} reward=0.25 done=true error=null

[END] success=true steps=3 score=0.82 rewards=0.30,0.27,0.25

[SUMMARY] tasks=3 ticket-classify=1.00 ticket-triage=1.00 ticket-respond=0.82 avg=0.94
```

---

## API Quick-Start

### Reset (start new episode)
```bash
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task": "ticket-classify", "session_id": "agent-001"}'
```

### Step
```bash
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "agent-001",
    "action": {
      "action_type": "classify",
      "ticket_id": "TCK-001",
      "category": "billing",
      "priority": "high"
    }
  }'
```

### List tasks
```bash
curl http://localhost:7860/tasks
```

### Validate environment
```bash
curl http://localhost:7860/validate
```

### Get state
```bash
curl http://localhost:7860/state?session_id=agent-001
```

---

## Action Space

### Classify Action
```json
{
  "action_type": "classify",
  "ticket_id": "TCK-001",
  "category": "billing",
  "priority": "high"
}
```
- `category`: `billing | technical | account | general | spam`
- `priority`: `critical | high | medium | low`

### Triage Action
```json
{
  "action_type": "triage",
  "ticket_id": "TCK-101",
  "priority": "critical",
  "department": "escalation"
}
```
- `department`: `tier1 | tier2 | billing | account_mgmt | escalation`

### Respond Action
```json
{
  "action_type": "respond",
  "ticket_id": "TCK-201",
  "response_text": "Dear Grace, I sincerely apologize for the inconvenience..."
}
```

---

## Observation Space

```json
{
  "task": "ticket-triage",
  "step": 2,
  "max_steps": 15,
  "tickets": [
    {
      "id": "TCK-101",
      "subject": "URGENT: Production API completely down",
      "body": "Our entire production system is down...",
      "customer_name": "Bob Smith",
      "customer_tier": "enterprise",
      "account_age_days": 730,
      "previous_tickets": 15,
      "timestamp": "2024-01-15T09:00:00Z"
    }
  ],
  "current_ticket_id": "TCK-102",
  "processed_count": 1,
  "message": "Ticket TCK-101 triaged (raw=1.00, norm=0.20). 4 ticket(s) remaining.",
  "context": {}
}
```

For `ticket-respond`, `context.company_policy` contains the full support knowledge base including password reset steps, SLA times, refund policies, and escalation contacts.

---

## Step Result

```json
{
  "observation": { "..." : "..." },
  "reward": 0.20,
  "reward_info": {
    "value": 0.20,
    "breakdown": {},
    "message": "Ticket TCK-101 triaged (raw=1.00, norm=0.20). 4 ticket(s) remaining.",
    "is_penalty": false
  },
  "done": false,
  "info": {
    "message": "Ticket TCK-101 triaged (raw=1.00, norm=0.20). 4 ticket(s) remaining.",
    "details": {
      "priority": "correct",
      "department": "correct",
      "total_score": 1.0
    }
  }
}
```

---

## Running Locally

### Prerequisites
- Python 3.11+
- Docker (optional)

### Installation

```bash
cd support-desk-env
pip install -r requirements.txt

# Start the server
python app.py
# Server runs at http://localhost:7860
```

### Docker

```bash
docker build -t support-desk-env .
docker run -p 7860:7860 support-desk-env
```

---

## Running Inference

```bash
export HF_TOKEN=your_token_here
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct

python inference.py
```

To use a different model or endpoint:
```bash
export API_BASE_URL=https://api.openai.com/v1
export OPENAI_API_KEY=your_openai_key
export MODEL_NAME=gpt-4o-mini

python inference.py
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HF_TOKEN` | HuggingFace API key | — |
| `API_BASE_URL` | LLM API endpoint (OpenAI-compatible) | `https://router.huggingface.co/v1` |
| `MODEL_NAME` | Model identifier | `Qwen/Qwen2.5-72B-Instruct` |
| `PORT` | Server port | `7860` |

---

## Validation

```bash
# Quick smoke-test via API
curl http://localhost:7860/validate

# Python functional test
python3 -c "
from environment import SupportDeskEnv
from models import Action
e = SupportDeskEnv('ticket-classify')
r = e.reset()
print('reset ok:', r.observation.current_ticket_id)
s = e.step(Action(action_type='classify', ticket_id='TCK-001', category='billing', priority='high'))
print('step ok, reward:', s.reward, 'done:', s.done)
"
```

---

## HuggingFace Spaces Deployment

1. Create a new HF Space with Docker SDK
2. Push this repository to the Space
3. The Space auto-builds using the `Dockerfile`
4. All endpoints are available at `https://your-space.hf.space/`

---

## License

MIT
