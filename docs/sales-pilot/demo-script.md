# Internal Demo Script

## Duration

20 minutes.

## Audience

QA Lead, QA Automation Lead, Engineering Manager, and one security-minded
reviewer.

## Setup

Use a synthetic demo archive or public-safe sample. Keep the terminal and demo
browser local.

Pre-demo checklist:
- `make verify` passes in `bqa-team`.
- The demo archive contains synthetic content only.
- The browser demo does not upload data to a server.
- The presenter can show `.bqa-team/status/` and validation reports.

## Flow

1. State the problem.
   "QA context is expensive to reconstruct. BQA-OS turns evidence into reusable
   QA memory with validation and guardrails."

2. Show the input.
   Open the synthetic archive or sample folder. Point out test plans,
   acceptance criteria, and sanitized run evidence.

3. Run or show the generated pack.
   Highlight agents, workflows, specs, prompts, and validation reports.

4. Show guardrails.
   Show consent gate, local-first behavior, validation before success, and
   drift guard stop conditions.

5. Show output usage.
   Pick one generated workflow and explain how a QA engineer would adapt it to a
   real release.

6. Close with pilot plan.
   Ask the team to nominate one safe target area and one owner for validation.

## Demo Success Signals

- Buyer can name a real workflow this would improve.
- Buyer asks about onboarding a second module or pipeline.
- Security reviewer agrees the local-first boundary is clear.
- QA owner can define pilot acceptance criteria in one sentence.
