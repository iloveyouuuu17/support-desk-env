# SupportDeskEnv

A real-world **customer support ticket triage and response** environment for AI agents, built to the [OpenEnv](https://github.com/openenv/openenv) specification.

Agents must classify, prioritize, route, and draft responses to realistic support tickets — skills directly applicable to production customer service automation.

---

## Environment Description

### Domain
Customer support operations — a domain where AI agents can deliver real business value by automating first-line triage and response drafting.

### Tasks

| Task | Difficulty | Steps | Description |
|------|-----------|-------|-------------|
| `ticket-classify` | Easy | ≤5 | Classify 1 ticket by **category** + **priority** |
| `ticket-triage` | Medium | ≤15 | Triage a queue of **5 tickets** with routing decisions |
| `ticket-respond` | Hard | ≤15 | Draft professional **responses** to 3 complex tickets |

---

## Action Space

All actions are JSON objects sent to the `/step` endpoint:

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
  "task": "ticket-classify",
  "step": 1,
  "max_steps": 5,
  "tickets": [{ "id": "...", "subject": "...", "body": "...", ... }],
  "current_ticket_id": "TCK-001",
  "processed_count": 0,
  "message": "Environment ready.",
  "context": {}
}
```

For `ticket-respond`, `context.company_policy` contains the support knowledge base.

---

## Reward Function

Rewards are **partial** — agents receive signal on each action, not just at episode end.

### ticket-classify
| Condition | Reward |
|-----------|--------|
| Correct category | +0.60 |
| Correct priority (exact) | +0.40 |
| Priority within 1 level | +0.20 |
| Wrong category | +0.00 |

### ticket-triage (per ticket, normalized by ÷5)
| Condition | Raw reward |
|-----------|-----------|
| Correct department | +0.60 |
| Correct priority (exact) | +0.40 |
| Priority within 1 level | +0.20 |

### ticket-respond (per ticket, normalized by ÷3)
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

## Setup & Running

### Prerequisites
- Python 3.11+
- Docker

### Local Development

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

### API Usage

```bash
# Reset (start new episode)
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task": "ticket-classify"}'

# Step
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action": {"action_type": "classify", "ticket_id": "TCK-001", "category": "billing", "priority": "high"}}'

# State
curl http://localhost:7860/state
```

---

## Inference Script

```bash
export HF_TOKEN=your_token_here
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct

python inference.py
```

Expected output format:
```
[START] task=ticket-classify env=support-desk-env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action={"action_type":"classify",...} reward=1.00 done=true error=null
[END] success=true steps=1 score=1.00 rewards=1.00

[START] task=ticket-triage env=support-desk-env model=Qwen/Qwen2.5-72B-Instruct
...
[END] success=true steps=5 score=0.72 rewards=0.20,0.12,0.20,0.12,0.08
```

---

## Validation

```bash
# Install validator
pip install openenv-core

# Run validation
openenv validate

# Run submission validator script
./validate-submission.sh https://your-space.hf.space .
```

---

## HuggingFace Spaces Deployment

1. Create a new HF Space (Docker SDK)
2. Push this repository to the Space
3. The Space will automatically build and deploy using the `Dockerfile`
4. The `/reset` endpoint will be available at `https://your-space.hf.space/reset`

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HF_TOKEN` | HuggingFace / API key | — |
| `API_BASE_URL` | LLM API endpoint | `https://router.huggingface.co/v1` |
| `MODEL_NAME` | Model identifier | `Qwen/Qwen2.5-72B-Instruct` |
| `PORT` | Server port | `7860` |

---

## Baseline Scores

Typical scores with `Qwen/Qwen2.5-72B-Instruct`:

| Task | Expected Score |
|------|---------------|
| ticket-classify | 0.80 – 1.00 |
| ticket-triage | 0.60 – 0.80 |
| ticket-respond | 0.50 – 0.75 |

---

## License

MIT
