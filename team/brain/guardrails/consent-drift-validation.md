# Consent, Drift, and Validation Guardrail

## Consent

Self-healing and self-evolution must require consent before reading local logs,
validation reports, safety reports, git status, or diffs.

## Drift

Stop or warn when work expands beyond the current goal, edits unrelated files,
or cannot identify the evidence needed for completion.

## Validation

Do not call work complete until the appropriate validator or verification
command has passed in the current run.

## Recovery

When blocked, answer:

- What is the exact goal?
- What evidence proves it is done?
- What assumptions are unsupported?
- What changed since the last safe state?
- What is the smallest reversible next step?
