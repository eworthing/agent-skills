# Antigravity CLI (`agy`) Reference — peer-plan-review

Source: binary help + live `--print` probing of `agy` v1.0.7, verified 2026-06-14.

Antigravity is Google's successor to the Gemini CLI (which is EOL 2026-06-18 — see [`gemini.md`](gemini.md)). It is a Go binary invoked as `agy`; its home is `~/.gemini/antigravity-cli/`.

> ⚠️ **EXPERIMENTAL — NOT a guaranteed read-only reviewer.** Unlike every other
> provider (claude `--permission-mode plan`, codex `--sandbox read-only`,
> copilot `--deny-tool=write,shell`), `agy --print` **auto-approves all tools
> and can create/modify files and run shell commands**. `--sandbox` only
> contains terminal commands; the workspace stays writable. There is no
> read-only flag. The adapter mitigates with `--sandbox` plus a read-only
> directive prepended to every prompt, but this is best-effort. **Run agy only
> on trusted plans, and commit or stash your working tree first.**

## Install

Ships with Google Antigravity. Verify with `agy --version`; update with `agy update`. (`agy install` configures PATH/shell.)

## Binary

`agy`

## Headless exec

```bash
printf 'PROMPT' | agy \
  --print \
  --sandbox \
  --print-timeout 600s \
  --model "Gemini 3.5 Flash (High)" \
  --log-file=/tmp/agy-run.log
```

- `--print` / `-p` / `--prompt`: run a single prompt non-interactively. **Prompt is read from stdin** (the flag takes no inline value).
- **stdout is plain text** — there is no JSON output mode. The response is written verbatim; the skill parses the structured review / `VERDICT:` line from it directly (no unwrap).
- `--print-timeout <dur>`: Go duration (default `5m`). The adapter sets it to its own `--timeout` so the adapter's process-tree kill stays the single source of truth.
- `--sandbox`: runs terminal commands in a sandbox (`proceed-in-sandbox`). Does **not** make the workspace read-only.
- `--add-dir <path>`: add a directory to the workspace (repeatable).

## Models

`agy models` lists: `Gemini 3.5 Flash (Low|Medium|High)`, `Gemini 3.1 Pro (Low|High)`, `Gemini 3 Flash`.

**Only the `Gemini 3.5 Flash` family returns output in headless `--print`** (verified 2026-06-14). The Pro variants and bare `Gemini 3 Flash` exit 0 with **empty** output on the tested enterprise/Vertex account (entitlement-dependent). The adapter therefore defaults to the Flash family and maps effort to its variant.

- `--model "<exact string>"`: pass one of the `agy models` strings verbatim.
- Effort is **encoded in the model name** — there is no `--effort` flag. The skill maps portable effort → variant: `low`→`(Low)`, `medium`→`(Medium)`, `high`→`(High)`, `xhigh`→`(High)` (agy's highest).
- Alias: `flash` → `Gemini 3.5 Flash` (combined with `--effort`). Raw model IDs pass through unchanged.
- **Default (no `--model`):** `Gemini 3.5 Flash (High)`.

## Resume

`--conversation <uuid>`: resume a specific conversation. `--continue` / `-c`: most recent.

The conversation UUID is **not** printed to stdout and **not** recorded in `history.jsonl` (that logs interactive sessions only). It appears in the CLI log as `Print mode: conversation=<uuid>` (also `Created conversation <uuid>`). The adapter hands agy a dedicated per-run `--log-file=<path>` (the **equals form** — the space form is ignored in print mode) and parses the id from it, which is race-free under parallel fan-out.

## Auth, footprint, cost

- Auth uses the local Google/GCP (Vertex) credentials; runs consume Vertex quota.
- Every run persists the prompt+response as a SQLite conversation under `~/.gemini/antigravity-cli/conversations/*.db` plus a log — these are **not** auto-cleaned (unlike the skill's temp files).

## Empty-output behavior

An unentitled/unavailable model exits 0 with empty stdout. The adapter's empty-output guard converts that to a non-zero result so it surfaces as a failure rather than a phantom success.
