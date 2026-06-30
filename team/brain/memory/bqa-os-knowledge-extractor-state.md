# BQA-OS Knowledge Extractor State

## Stable MVP Contract

`bqa build` expects normalized session input under `.bqa/input/sessions` and
writes exactly seven knowledge artifacts under `.bqa/knowledge`:

- `etl_patterns.yaml`
- `graphql_patterns.yaml`
- `api_patterns.yaml`
- `data_quality_patterns.yaml`
- `common_bugs.yaml`
- `successful_prompts.yaml`
- `project_profile.yaml`

## CLI Contract

The build command should preserve a concise summary containing:

- sessions processed;
- artifacts created;
- output directory.

## Safety Contract

- Do not write private logs, raw transcripts, or secrets into generated
  knowledge.
- Keep redaction in the core evidence cleanup path.
- Treat stale `.bqa/knowledge/droid_patterns.yaml` and
  `.bqa/knowledge/runtime_patterns.yaml` as old generated state, not current MVP
  output.

## Verification

- Use `go test ./...` for Go code changes.
- For smoke verification, create a synthetic `.bqa/input/sessions/index.json`
  and normalized markdown input, then run `go run ./cmd/bqa build`.

