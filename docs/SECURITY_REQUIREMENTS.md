# BQA Team Security Requirements

These requirements apply to BQA Team scripts, roles, prompts, validators, self-healing, and self-evolution workflows.

## 1. Consent gate

Before any self-healing or self-evolution workflow reads local logs, validation reports, safety reports, git status, or diffs, it must show a one-time notice and require explicit consent.

Consent is stored locally under:

```text
.bqa-team/consent/
```

If consent is not granted, the workflow must stop.

## 2. Local-first by default

BQA Team must assume local-first execution.

Allowed local inputs:

- local run logs;
- local validation reports;
- local safety reports;
- local generated artifacts;
- local git status and diffs.

Do not require remote services except explicitly invoked tools such as GitHub CLI or Codex CLI.

## 3. No sensitive data in public repos

Never commit:

- secrets;
- credentials;
- tokens;
- real customer data;
- unsanitized session logs;
- private company data;
- private brain knowledge.

## 4. Human-controlled mutation

Mutating operations must require explicit execution mode or an explicit user command.

Examples:

- git commit;
- git push;
- GitHub issue creation;
- GitHub label changes;
- self-evolution updates to bqa-team.

Dry-run must remain the default where practical.

## 5. Least privilege

Agents and scripts should receive the minimum data and permissions needed for the task.

Do not pass entire repos, large logs, or unrelated private files when a smaller context is enough.

## 6. Drift guard

Agent workflows must stop or warn when they detect:

- unrelated file edits;
- forgotten target goal;
- invalid output claims;
- repeated failed attempts;
- mismatch with acceptance criteria;
- missing validation;
- unsupported assumptions;
- tool output contradicting the agent summary.

## 7. Validation before success

A task is not done until validators or explicit checks pass.

For ETL QA Pack:

```bash
scripts/bqa_validate_etl_pack.sh
```

must pass before the pack is considered ready.

## 8. Self-healing boundaries

Self-healing may create, repair, or improve generated artifacts inside the expected output folder.

It must not rewrite unrelated product source code.

## 9. Self-evolution boundaries

Self-evolution may improve bqa-team roles, scripts, templates, validators, and runbooks.

It must not edit product code in the target repo.

It must not copy private log content into committed files.

## 10. Audit trail

Workflows must write useful reports:

- validation report;
- drift report;
- context snapshot;
- self-healing logs;
- self-evolution logs.

## 11. Critical thinking checkpoint

When blocked or uncertain, agents must answer:

- What is the exact goal?
- What evidence proves it is done?
- What assumptions are unsupported?
- What changed since the last safe state?
- What is the smallest reversible next step?

## 12. TRIZ recovery checkpoint

For persistent failures, agents may use TRIZ framing:

- useful function;
- harmful effect;
- contradiction;
- available resource;
- ideal final result;
- smallest experiment.

## 13. Multi-agent coordination

Multi-agent workflows must preserve:

- clear ownership;
- task state;
- decision records;
- issue/PR links;
- role boundaries;
- review gates.

## 14. Stop conditions

Stop rather than continue if:

- consent is missing;
- the agent edits unrelated sensitive files;
- output validation repeatedly fails;
- git diff is too broad;
- the agent cannot identify the current goal;
- the task would require private data.
