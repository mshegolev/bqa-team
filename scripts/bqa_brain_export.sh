#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRAIN_DIR="${BQA_BRAIN_DIR:-}"
REGISTRY="$ROOT/team/brain/registry.json"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --brain-dir) BRAIN_DIR="$2"; shift 2 ;;
    --registry) REGISTRY="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$BRAIN_DIR" ]]; then
  BRAIN_DIR="${HOME}/.bqa/brain"
fi

if [[ ! -f "$REGISTRY" ]]; then
  echo "ERROR: registry not found: $REGISTRY" >&2
  exit 2
fi

python3 - "$ROOT" "$BRAIN_DIR" "$REGISTRY" "$DRY_RUN" <<'PY'
import json
import pathlib
import shutil
import sys
from datetime import datetime, timezone

root = pathlib.Path(sys.argv[1])
brain_dir = pathlib.Path(sys.argv[2])
registry_path = pathlib.Path(sys.argv[3])
dry_run = sys.argv[4] == "1"

registry = json.loads(registry_path.read_text(encoding="utf-8"))
artifacts = registry.get("artifacts", [])
if registry.get("kind") != "BQATeamUnifiedRegistry":
    raise SystemExit(f"ERROR: unsupported registry kind: {registry.get('kind')}")
if not artifacts:
    raise SystemExit("ERROR: registry contains no artifacts")

seen = set()
allowed_roots = ("agents/", "skills/", "workflows/", "guardrails/", "project-profiles/", "memory/")
for artifact in artifacts:
    artifact_id = artifact["id"]
    if artifact_id in seen:
        raise SystemExit(f"ERROR: duplicate artifact id: {artifact_id}")
    seen.add(artifact_id)

    source = root / artifact["source"]
    destination = pathlib.PurePosixPath(artifact["destination"])
    if destination.is_absolute() or ".." in destination.parts:
        raise SystemExit(f"ERROR: unsafe destination for {artifact_id}: {destination}")
    if not str(destination).startswith(allowed_roots):
        raise SystemExit(f"ERROR: unsupported destination root for {artifact_id}: {destination}")
    if not source.is_file():
        raise SystemExit(f"ERROR: source missing for {artifact_id}: {source}")

    target = brain_dir / pathlib.Path(*destination.parts)
    print(f"{artifact_id}: {source.relative_to(root)} -> {target}")
    if dry_run:
        continue

    target.parent.mkdir(parents=True, exist_ok=True)
    content = source.read_text(encoding="utf-8")
    header = "\n".join(
        [
            "<!-- BQA_UNIFIED_ARTIFACT",
            f"id: {artifact_id}",
            f"type: {artifact['type']}",
            f"title: {artifact['title']}",
            f"source: {artifact['source']}",
            "-->",
            "",
        ]
    )
    target.write_text(header + content, encoding="utf-8")

if not dry_run:
    registry_dir = brain_dir / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    lines = [
        "version: 1",
        "kind: BQARegistry",
        "metadata:",
        "  name: bqa-brain",
        "  description: Private BQA knowledge and capability registry.",
        "  owner: mshegolev",
        f"  generated_at: {generated_at}",
        "  source_registry: team/brain/registry.json",
        "sources:",
        "  brain_repository: https://github.com/mshegolev/bqa-brain.git",
    ]
    for section in ["agents", "skills", "workflows", "rules", "guardrails", "memory_indexes"]:
        if section == "rules":
            lines.append("rules: []")
            continue
        registry_type = "memory_index" if section == "memory_indexes" else section[:-1]
        items = [a for a in artifacts if a["type"] == registry_type]
        lines.append(f"{section}:")
        if not items:
            lines.append("  []")
            continue
        for artifact in items:
            lines.extend(
                [
                    f"  - id: {artifact['id']}",
                    f"    title: {artifact['title']}",
                    f"    path: {artifact['destination']}",
                    f"    summary: {artifact['summary']}",
                    "    tags:",
                ]
            )
            for tag in artifact["tags"]:
                lines.append(f"      - {tag}")
    project_profiles = [a for a in artifacts if a["type"] == "project_profile"]
    lines.append("project_profiles:")
    for artifact in project_profiles:
        lines.extend(
            [
                f"  - id: {artifact['id']}",
                f"    title: {artifact['title']}",
                f"    path: {artifact['destination']}",
                f"    summary: {artifact['summary']}",
            ]
        )
    (registry_dir / "bqa_registry.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")

print(f"BQA Brain export complete: {len(artifacts)} artifact(s) -> {brain_dir}")
if dry_run:
    print("Dry run only; no files written.")
PY
