# Definition of Done (BQA-OS autopilot)

An issue is **done** only when it is mergeable. Every implementer/builder role
must meet this before handing a task to QA. This is the standard the autopilot
relies on — when it is not met, cycles stall as `missing_pr` (a branch left
without a pull request) or `qa_failed` (acceptance criteria / tests not actually
met) and nothing ships.

## Required for every task

1. **Cover every acceptance criterion** in the issue — implement the whole
   slice the issue asks for, not a partial one.
2. **Make tests green.** Run the project's test/validation command
   (`go test ./...` for Go; HTML/JS validation for static-site work) and fix
   failures. Include the final result in your summary.
3. **Always produce a pull request.** Commit, push the branch, and open a PR
   with `gh pr create` (base `main`). **Never leave a branch without an open
   PR.** If you cannot finish, do not go silent — emit a `QUESTION_STATUS: OPEN`
   block so the blocker is explicit and routable.
4. **Summarize** in the PR/output: files changed, tests run + result,
   acceptance criteria covered, and remaining risks.

## Why

Autopilot QA and business-acceptance gates can only pass work that is complete
and tested. Meeting this Definition of Done is what lets a cycle move
`ready-dev → ready-qa → ready-business → done` instead of blocking.
