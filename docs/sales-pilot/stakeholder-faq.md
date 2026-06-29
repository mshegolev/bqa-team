# Stakeholder FAQ

## Is this replacing QA engineers?

No. The pilot packages QA context into reusable artifacts so QA engineers spend
less time reconstructing history and more time validating risk.

## Does it require production data?

No. The pilot should use synthetic, sanitized, or public-safe inputs. Real
runtime artifacts stay local and must not be committed.

## What does security need to review?

Security should review:
- local-first execution;
- consent gate;
- no secrets in committed files;
- drift guard reports;
- validation before success claims.

## What happens if generated output is wrong?

Generated output must pass validators or be treated as incomplete. The workflow
keeps validation reports and drift reports so reviewers can reject or repair the
output.

## What is the smallest useful pilot?

One release area with existing test notes and a clear validation command.

## What if the team has no clean input data?

Use a synthetic sample first. Do not start a real pilot with unsanitized private
data.

## Who owns the output?

The target team owns whether the generated workflows and specs are useful.
BQA-OS owns the tooling, templates, and guardrails.

## What is the expansion path?

If one workflow is useful, repeat on a second workflow. After two or three
successful repeats, consider controlled autonomy for issue routing, QA review,
and business acceptance.
