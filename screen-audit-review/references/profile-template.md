# Profile template (fields the review skill uses)

Open when: no profile was found, or a field the workflow needs is missing.

The project keeps one Markdown profile with a single fenced YAML block. The capture skill reads a larger version of the same file; this page lists only what review uses. Never guess a field: if it is absent, say which one and stop that step.

## Discovery order

1. `profile=<path>` in the request.
2. The environment variable `SCREEN_AUDIT_PROFILE`.
3. A search of the current repository for `*screen-audit-agent-profile*.md`, skipping hidden artifact-output folders, `node_modules/`, `.build/` and `DerivedData/`. Exactly one hit is used; none or several: stop and ask.

## Fields

```yaml
profile_version: 1
home_app: <name>                  # the app the audit is about; the home-app group in counts
product_context: <one sentence: who uses the app and the core task>
tool: {cli: <path to compare.py>, readme: <path>, rubric: <path to rubric json>, harness: <path to rating harness>}
ledger: {project: <dir>, asset_root: <dir>, snapshots: <dir>}
cases: <path to cases.json>       # task text per case; read it, never copy it
apps_registry: <path to project.json>
authors: {findings: {deepseek: audit-deepseek, sonnet: audit-sonnet}, ratings: <agent id per family>, adjudicator: <agent id>}
helpers: {batch: <command>, ingest_findings: <command>, ingest_ratings: <command>, calib_report: <command>, adjudicator_record: <command>}
session_caps: {findings_frames: <n>, rating_frames: <n>, batch_size: <n>}
writer_claims: <dir or file where an agent claims a scope before writing>
endpoint_files: <where the harness endpoint files are; they name an environment variable, never a key>
authorised_prompts: []            # empty by default; a run's authorisations go in its log, never here
```

| Field | What review does with it |
| --- | --- |
| `home_app` | splits counts into home app and competitors; `--home` and `--competitors` batches |
| `product_context` | the operator and task behind every rating question |
| `tool.cli`, `ledger.*` | define the `sc` function (`--project` and `--asset-root` before the subcommand) |
| `tool.readme`, `tool.rubric` | the authority for tags, scale, anchors, caps and rulings; read, never copy |
| `tool.harness`, `endpoint_files` | rating v2 and adjudication routes |
| `cases` | the task text you read for each frame |
| `apps_registry` | exact app names |
| `authors` | the auditor tag (`audit-<family>`) and the real author ID for each family |
| `helpers` | batch, ingest and calibration commands; flags as documented there |
| `session_caps` | frames per session and per batch |
| `writer_claims` | where to claim a scope and refuse a held one |
| `authorised_prompts` | normally empty; never a source of authorisation |

A profile can hold more fields than these. Ignore the ones not listed. The capture skill's template describes channels, devices and naming; review does not touch them.
