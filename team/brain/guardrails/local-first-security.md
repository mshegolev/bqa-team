# Local-First Security Guardrail

## Rule

BQA workflows are local-first unless a user explicitly invokes GitHub, Codex, or
another remote tool.

## Never Commit

- Secrets or tokens.
- Raw customer data.
- Production dumps.
- Unsanitized logs or transcripts.
- Local runtime folders such as `.bqa-team/logs/` and `.bqa-team/generated/`.

## Allowed

- Sanitized learnings.
- Generic workflows.
- Test patterns.
- Role prompts without private facts.
- Project profiles without secrets.
