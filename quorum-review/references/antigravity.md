# Antigravity CLI (`agy`) Reference — quorum-review

Source: binary help + live `--print` probing of `agy` v1.0.7, verified 2026-06-14.

Antigravity is Google's successor to the Gemini CLI (EOL 2026-06-18 — see [`gemini.md`](gemini.md)). It is a Go binary invoked as `agy`; its home is `~/.gemini/antigravity-cli/`. quorum-review accepts `agy` (alias `antigravity`) as a panel reviewer or external verifier.

> ⚠️ **EXPERIMENTAL — NOT a guaranteed read-only reviewer.** Unlike the other
> providers, `agy --print` **auto-approves all tools and can create/modify
> files and run shell commands**. `--sandbox` only contains terminal commands;
> the workspace stays writable. There is no read-only flag. The adapter
> mitigates with `--sandbox` plus a read-only directive prepended to every
> prompt, but it is best-effort. **Only include agy in a panel for trusted
> plans, and commit or stash your working tree first.**

## Binary

`agy` (verify with `agy --version`; update with `agy update`).

## Headless exec

```bash
printf 'PROMPT' | agy --print --sandbox --print-timeout 600s \
  --model "Gemini 3.5 Flash (High)" --log-file=/tmp/agy-run.log
```

- `--print` reads the prompt from **stdin**; **stdout is plain text** (no JSON mode). quorum's text/`VERDICT:`/`VERIFIED|INVALIDATED` parsing reads it directly.
- `--sandbox` sandboxes terminal commands only (not a read-only workspace).
- `--print-timeout <dur>` set to the adapter `--timeout`.

## Models

`agy models` lists Flash and Pro variants, but **only `Gemini 3.5 Flash (Low|Medium|High)` returns output in headless `--print`** (verified 2026-06-14); Pro and bare `Gemini 3 Flash` exit 0 with empty output on the tested enterprise/Vertex account. Effort is encoded in the model name (no `--effort` flag); the adapter maps portable effort → variant (`xhigh`→`High`) and defaults to `Gemini 3.5 Flash (High)`. Spec models with `agy:flash` or `agy:"Gemini 3.5 Flash (Low)"`.

## Resume

`--conversation <uuid>` / `--continue`. The UUID is not on stdout and not in `history.jsonl`; it is in the CLI log (`Print mode: conversation=<uuid>`). The adapter captures it via a dedicated per-run `--log-file=<path>` (equals form), which is race-free under quorum's parallel fan-out.

## Auth, footprint, cost

Auth via local Google/GCP (Vertex) credentials; runs consume Vertex quota. Each run persists a SQLite conversation + log under `~/.gemini/antigravity-cli/` (not auto-cleaned). Unentitled models exit 0 empty; the adapter's empty-output handling surfaces that as a failure.
