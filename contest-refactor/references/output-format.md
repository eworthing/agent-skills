# Output Format

Each loop produces two files at repo root, plus a mid-loop checkpoint and two cross-loop persistent state files:

- `CURRENT_REVIEW.md` — human-readable per-loop review. Section schema in [output-format-markdown.md](output-format-markdown.md).
- `CURRENT_REVIEW.json` — machine-readable mirror. JSON schema in [output-format-json.md § CURRENT_REVIEW.json Schema](output-format-json.md#current_reviewjson-schema).
- `LOOP_STATE.json` — mid-Step-3 checkpoint; present only between Step 3 sub-step 0 and sub-step 11.f. Schema in [output-format-state-schemas.md § LOOP_STATE.json schema](output-format-state-schemas.md#loop_statejson-schema-own-track-schema_version-1).
- `REVIEW_HISTORY.md` / `.json` — per-loop archive. Compression rules in [output-format-markdown-archive.md § Per-loop archive format](output-format-markdown-archive.md#per-loop-archive-format-pr-5-schema_version--2); JSON schema in [output-format-state-schemas.md § REVIEW_HISTORY.json schema](output-format-state-schemas.md#review_historyjson-schema).
- `findings_registry.json` — cross-loop finding identity. Schema in [output-format-state-schemas.md § findings_registry.json schema](output-format-state-schemas.md#findings_registryjson-schema); fuzzy-match rules at [output-format-state-schemas.md § Fuzzy-match rules](output-format-state-schemas.md#fuzzy-match-rules-method-step-15--bootstrap).

Previous `CURRENT_REVIEW.md` is appended to `REVIEW_HISTORY.md` (preceded by `--- Loop N (UTC timestamp) ---`) before being overwritten. This preserves cross-loop deltas without keeping multiple live files.

## See also

- [output-format-markdown.md](output-format-markdown.md) — CURRENT_REVIEW.md section schema (Discovery, Verdict, Scorecard, Authority Map, Strengths, Findings, Simplification Check, Improvement Backlog, Deepening Candidates, Builder Notes, Final Judge Narrative, Loop N Result) + per-loop archive compression rules.
- [output-format-json.md](output-format-json.md) — per-loop JSON schemas: CURRENT_REVIEW.json, embedded `halt_handoff` and `re_validation_context` objects, Per-Loop Progress Line Format, canonical Deepening Keywords, Schema version 3 changelog, 27 schema validation rules.
- [output-format-state-schemas.md](output-format-state-schemas.md) — persistent state file schemas: LOOP_STATE.json, findings_registry.json, REVIEW_HISTORY.json, Fuzzy-match rules.

## Optional render — HTML / markdown dashboard

`python3 scripts/render_report.py CURRENT_REVIEW.json [--history REVIEW_HISTORY.json] [--format html|markdown]` renders a self-contained dashboard: the 9-dimension scorecard plus a per-dimension score *trend* across loops (inline-SVG sparklines from REVIEW_HISTORY.json). The HTML form is fully **offline** — inline CSS, no d3, no CDN — so a committed report opens with no network. Read-only; never mutates artifacts, scores, or gates. Template: `assets/report-skeleton.html` (`{{TOKEN}}` substitution).

## Optional export — SARIF

At HALT, the findings that *survive* the loop (registry entries terminally `unresolvable`, plus `accepted` scorecard residuals when a review is supplied) can be exported to SARIF 2.1.0 for IDE/CI triage: `python3 scripts/export_sarif.py findings_registry.json [--review CURRENT_REVIEW.json]`. Read-only; never mutates state, scores, or gates, and fabricates no findings (a fully-resolved registry yields an empty-results log).
