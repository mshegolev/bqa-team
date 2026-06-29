# Pilot Onboarding Checklist

## Scope

- [ ] One target module, service, release area, or ETL pipeline selected.
- [ ] QA owner named.
- [ ] Engineering contact named.
- [ ] Security or data-boundary reviewer named.
- [ ] Success criteria written in one paragraph.

## Inputs

- [ ] Sanitized issue or release notes.
- [ ] Public-safe acceptance criteria.
- [ ] Test command list.
- [ ] Existing QA checklist or test plan.
- [ ] Synthetic sample data if needed.
- [ ] Known risks or repeated failure modes.

## Safety

- [ ] No credentials.
- [ ] No raw customer data.
- [ ] No production dumps.
- [ ] No unsanitized logs.
- [ ] Real artifacts stay local under `.bqa/` or `.bqa-team/`.
- [ ] Consent gate accepted before self-healing or self-evolution reads local
      runtime artifacts.

## Execution

- [ ] Install or update BQA Team.
- [ ] Run local verification: `make verify`.
- [ ] Generate or load synthetic input archive.
- [ ] Run validator for generated pack.
- [ ] Review drift report before commit or handoff.

## Review

- [ ] QA owner reviews generated workflows.
- [ ] Engineering contact reviews repo commands.
- [ ] Security reviewer confirms local-first boundary.
- [ ] Team decides expand, repeat, or stop.
