# Testing-Only Runner Skill

## Purpose

Apply only the QA test engineer persona to a target repository without running
the full GitHub team pipeline.

## Command

```bash
bash /opt/develop/bqa-team/scripts/bqa_test_only.sh \
  --target /path/to/target-repo \
  --task "Add or extend tests for the bounded target area"
```

Add `--execute` only when the target repo is ready for Codex to edit tests.

## Boundaries

- Only tests, fixtures, and test config may change.
- Product source code must not change.
- Existing framework conventions win.
- The final report must include exact test commands run or recommended.

## Persona Resolution

The runner prefers `<target>/.bqa/agents/etl-qa-agent.md` when available, then
falls back to the bundled `BQA_OS_QA_Test_Engineer` role.
