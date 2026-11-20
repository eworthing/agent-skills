# Project profile

Open this when no profile exists or a profile field is missing. The project keeps one profile: a Markdown file with a single fenced YAML block, so any CLI's model can read it without a parser. The skill never holds project specifics; it reads them from here.

## Finding it

1. The invoker passes `profile=<path>`.
2. Else the environment variable `SCREEN_AUDIT_PROFILE`.
3. Else the single file matching `*screen-audit-agent-profile*.md` in the current repository, skipping dot-prefixed artifact folders, `node_modules/`, `.build/` and `DerivedData/`. Zero or several hits: stop and ask.

Never guess a ledger path, bundle ID or author ID that the profile does not give. A missing field that the run needs is a stop-and-ask, not a default.

## Schema

```yaml
profile_version: 1
home_app: <name>
product_context: <one sentence: who uses the app and the core task>
tool: {cli: <path to compare.py>, readme: <path>, rubric: <path to rubric json>}
ledger: {project: <dir>, asset_root: <dir>, snapshots: <dir>, viewer_build_parent: <dir>}
cases: <path to cases.json>
apps_registry: <path to project.json>
session_root: <dir pattern, e.g. <root>/<lane>-YYYY-MM-DD/>
disposable_fixtures: {team: <name>, board: <name>, player: <name>, playlist: <name>}
authors: {capture: <agent id>}
helpers: {<name>: <command>}
session_caps: {batch_size: <n>}
writer_claims: <dir or file where an agent claims a scope before writing>
channels:
  simulator: {command: <capture command>, sims: [<names>], forbidden_sims: ["* Copy"], notes: <caveats>}
  device_xcuitest: {helper: <test class and run command, or "none">, devices: [<names>]}
  mirroring: {allowed: <owner-approved yes/no>, window_pixels: <WxH>}
  mac: {capture: <command>, ipad_on_mac_window_points: {landscape: <WxH>, portrait: <WxH>}, expected_pixels: {landscape: <WxH>, portrait: <WxH>}}
expected_pixels: {<device model + orientation>: <WxH>}
id_patterns: {capture_id: <pattern>, filename: <pattern>}
vocabulary: <where the ledger's exact device and layout spellings are listed>
authorised_prompts: []
```

## Field meanings and what capture needs

| Field | Meaning | Capture needs it |
| --- | --- | --- |
| `profile_version` | Schema version | yes |
| `home_app` | The app the audit is about | yes |
| `product_context` | Who uses the app and the task; frames which screens matter | no (useful) |
| `tool` | CLI, README and rubric paths; the CLI is what `sc` calls | yes (`cli`, `readme`) |
| `ledger` | Project dir, asset root (both passed to every CLI call), snapshots dir, parent for viewer builds | yes |
| `cases` | `cases.json` with the task text per case; read, never copied | yes |
| `apps_registry` | App names, groups and bundle IDs; match apps by bundle ID | yes |
| `session_root` | Where capture sessions live | yes |
| `disposable_fixtures` | Names the agent may create and enter | yes |
| `authors.capture` | Author ID for notes the capture run writes | yes |
| `helpers` | Commands the run may execute besides the CLI | when a channel uses one |
| `session_caps` | Batch limits | no (review skill uses them) |
| `writer_claims` | Where to claim a scope before writing; live claim means stop | yes |
| `channels` | Per-channel commands, devices, simulators (and forbidden ones), caveats | yes |
| `expected_pixels` | Pixel size per device model and orientation | yes |
| `id_patterns` | Capture-ID and filename patterns | yes |
| `vocabulary` | Where exact spellings are listed | yes |
| `authorised_prompts` | Empty by default; a run's own authorisations go in its session log, never here | no (never a source of authorisation) |

Fields in the schema that only the review skill uses (`authors.findings`, `helpers` for batching and ingest, `session_caps.findings_frames` and `rating_frames`) may be present and are ignored here.
