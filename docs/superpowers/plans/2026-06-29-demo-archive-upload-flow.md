# Demo Archive Upload Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static browser-only demo that loads a synthetic BQA archive, validates it locally, displays generated artifacts, and downloads a generated result JSON.

**Architecture:** The first slice uses plain HTML, CSS, and JavaScript under `demo/site/` so it can be opened directly without a build step. A synthetic JSON archive under `demo/fixtures/` is the stable demo input. Python `unittest` checks the fixture schema, private-data guardrails, static app files, and no-network constraint.

**Tech Stack:** Static HTML/CSS/JavaScript, browser `FileReader`, browser `Blob` downloads, Python `unittest`.

---

### Task 1: Demo Fixture Contract

**Files:**
- Create: `tests/test_demo_archive.py`
- Create: `demo/fixtures/bqa-demo-archive.json`

- [ ] **Step 1: Write failing fixture tests**

Add tests that require the fixture to contain `manifest`, `sessions`, `agents`, `workflows`, `specs`, `knowledge`, and `recommendations`, and that scan serialized fixture text for forbidden private-data terms.

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python3 -m unittest tests.test_demo_archive -v
```

Expected before the fixture exists: failure because `demo/fixtures/bqa-demo-archive.json` is missing.

- [ ] **Step 3: Add synthetic fixture**

Create a JSON fixture with fake BQA sessions, generated agents, workflows, specs, knowledge artifacts, and recommendations.

- [ ] **Step 4: Run test to verify pass**

Run:

```bash
python3 -m unittest tests.test_demo_archive -v
```

Expected after implementation: all fixture tests pass.

### Task 2: Static App Contract

**Files:**
- Create: `tests/test_demo_site.py`
- Create: `demo/site/index.html`
- Create: `demo/site/styles.css`
- Create: `demo/site/app.js`

- [ ] **Step 1: Write failing static app tests**

Add tests that require the three static files, required UI labels, the bundled fixture path, and no network primitives.

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python3 -m unittest tests.test_demo_site -v
```

Expected before app files exist: failure for missing `demo/site/index.html`.

- [ ] **Step 3: Add static app**

Implement a three-column app matching `docs/design-assets/bqa-demo-archive-concept.png` direction:

- left upload and validation rail;
- center artifact tabs and detail panel;
- right summary and download actions.

Use `FileReader` for uploaded JSON and a bundled sample loader that reads `../fixtures/bqa-demo-archive.json` only when served over HTTP. If direct file access blocks sample loading, show instructions and keep upload fully functional.

- [ ] **Step 4: Run test to verify pass**

Run:

```bash
python3 -m unittest tests.test_demo_site -v
```

Expected after implementation: all static app tests pass.

### Task 3: Verification

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Include Serena ignore**

Keep `.serena/` ignored as local tool state.

- [ ] **Step 2: Run full verification**

Run:

```bash
make verify
```

Expected: py_compile succeeds, shell syntax succeeds, and all unit tests pass.

- [ ] **Step 3: Inspect workspace**

Run:

```bash
git status --short
```

Expected: only intentional files are modified or new.
