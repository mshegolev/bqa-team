# PRD: Demo Archive Upload Flow

## Objective

Build a static, browser-only BQA Demo Archive screen that proves the product workflow with synthetic data:

1. user opens a local static page;
2. user uploads or loads a synthetic marked archive;
3. the page validates the archive shape locally;
4. the page displays agents, workflows, specs, knowledge artifacts, and recommendations;
5. the user downloads a generated result archive.

## Source Backlog

- `team/backlog/001_static_site_app.md`
- `team/backlog/005_demo_archive_generator.md`
- `team/backlog/007_upload_flow.md`

## Users

- BQA-OS maintainer preparing a demo.
- QA Lead or QA Automation Lead evaluating what a BQA archive produces.
- Internal stakeholder reviewing the workflow without private data.

## Requirements

### Functional

- Provide a static page under `demo/site/` that works by opening `index.html` directly.
- Provide a synthetic JSON archive under `demo/fixtures/` with:
  - manifest metadata;
  - normalized sessions;
  - generated agents;
  - workflows;
  - specs;
  - knowledge artifacts;
  - recommendations.
- Let users load the bundled sample without backend access.
- Let users upload a JSON archive from disk with `FileReader`.
- Validate that required top-level archive sections exist.
- Render counts, validation status, artifact tabs, a table/list view, and a selected artifact detail panel.
- Generate a downloadable JSON result containing the manifest, validation result, summary counts, and recommendations.

### Non-Functional

- No backend service.
- No network calls.
- No private data, real customer logs, secrets, tokens, or credentials.
- No build step or dependency installation for the first slice.
- Keep UI code native HTML/CSS/JavaScript.
- Keep `make verify` green.

## UX Direction

Reference concept: `docs/design-assets/bqa-demo-archive-concept.png`.

The first slice should follow the concept direction:

- true white background;
- compact operational app shell;
- left validation rail;
- center artifact browser;
- right summary/actions rail;
- teal/green validation accent;
- subtle borders and radius no larger than 8px;
- dense but readable QA/productivity interface;
- no marketing hero and no decorative blobs.

## Acceptance Criteria

- `make verify` passes.
- `tests/test_demo_archive.py` verifies the synthetic fixture structure and screens for forbidden private-data terms.
- `tests/test_demo_site.py` verifies that `index.html`, `app.js`, and `styles.css` exist and that the app has no network primitives such as `fetch(` or `XMLHttpRequest`.
- The static page can load the bundled sample archive and render all required artifact categories.
- The static page can parse an uploaded JSON archive with the same schema.
- The download action produces a JSON file in the browser.

## Out of Scope

- ZIP parsing.
- Backend upload.
- Authentication.
- Real customer data.
- Multi-page app routing.
- Pixel-perfect implementation of every table row from the concept.
