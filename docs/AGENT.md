# Conversational agent design

CampusOps answers like a tutor that knows you — not a template engine.

## Pipeline per turn

1. **Onboarding?** → conversational setup, no agent involved.
2. **Small talk?** (`hi`, `thanks`, `bye`) → instant human one-liner.
3. **Actions** (reminder/task create, hide/show/delete) → execute against
   the DB first (facts must be exact), confirm in the reply context.
4. **Retrieve** — intents gather tight slices (today-only, deadlines-only…);
   open questions gather the full picture (plan, focus, updates, docs).
5. **Compose** — ONE model call with three inputs:
   - **system** = `SYSTEM_BASE` (grounding + honesty rules) + the per-turn
     **user card** (`docs/USER_CARD_SPEC.md`) + channel style (short/chatty
     on Telegram, structured on web);
   - **RETRIEVED CONTEXT** = only the facts this turn needs;
   - **history** = last ≤6 turns, so follow-ups ("and tomorrow?") resolve.
6. **Fallback** — provider 429/outage → `ResilientLLM` serves the same
   retrieved facts deterministically. Students always get truth, sometimes
   with less flourish.

## Why it doesn't repeat itself

- The model (temp 0.7) voices fresh wording over fresh data every turn;
- templates answer only greetings and action confirmations;
- history prevents "as a first answer" amnesia;
- the user card keeps every reply personal (name, batch, their classes).

## Cost control

- Small talk + onboarding: zero model calls.
- Targeted intents: small context (~20 lines), `max_tokens: 800`.
- Free-tier quota (50/day) is shared with vision OCR; heavy days degrade
  to the facts composer instead of erroring.
