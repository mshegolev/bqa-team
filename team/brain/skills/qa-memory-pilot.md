# QA Memory Pilot Skill

## Purpose

Create a local-first QA memory pack from sanitized evidence for one bounded
module, release area, or ETL pipeline.

## Inputs

- Sanitized issue descriptions and acceptance criteria.
- Existing test commands and validation commands.
- Public-safe QA checklists or synthetic session summaries.
- Known risks and repeated failure patterns.

## Outputs

- QA workflows and checklists.
- Test spec templates.
- Validation report.
- Missing-evidence report.
- Next-step recommendations for the target team.

## Rules

- Keep all real runtime artifacts local under `.bqa/` or `.bqa-team/`.
- Never commit credentials, raw customer data, production dumps, or unsanitized logs.
- Prefer synthetic examples when a real artifact is not safe.
- Run validators before calling the pack ready.

## Verification

Run the relevant target validator first. For `bqa-team`, run:

```bash
make verify
```
