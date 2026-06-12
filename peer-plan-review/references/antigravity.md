# Antigravity CLI Reference — peer-plan-review

Source: official docs (antigravity.google/docs/cli-using), public hands-on
guides, and google-antigravity/antigravity-cli issue tracker, May 2026.
Flags derived from documentation, not yet verified against a local binary —
run `--self-check --reviewer antigravity` plus one round before relying on it.

Antigravity (`agy`) is Google's successor to Gemini CLI. **Gemini CLI stops
serving Pro/Ultra and free users on 2026-06-18** — prefer this provider over
`gemini` after that date.

## Install

```bash
agy install        # self-managed binary; agy is NOT npm-distributed
agy update         # update to latest
```

## Binary

`agy`

## Headless exec

```bash
agy --sandbox --dangerously-skip-permissions \
  --print-timeout 600s \
  -p "PROMPT"
```

- `-p` / `--print` / `--prompt`: run one prompt non-interactively, response
  on stdout as **plain text** — there is NO `--output-format` flag
- `--sandbox`: terminal restrictions
- `--dangerously-skip-permissions`: auto-approve tool permission requests —
  required headless, otherwise permission prompts hang. The reviewer stays
  read-only by prompt contract (same model as opencode)
- `--print-timeout DURATION` (Go-style, e.g. `600s`; default `5m0s`): agy's
  internal print-mode timeout. The adapter pins it to the runner timeout so
  long reviews aren't cut short underneath the runner
- `--add-dir PATH`: add directories to the workspace (repeatable)

## Model

`-m MODEL` / `--model MODEL`, passed through raw — the skill defines no
shorthand aliases because public sources conflict on the accepted name form:

- Google's codelab shows display names: `agy --model "Gemini 3.5 Flash (Low)"`
- Hands-on guides show slugs in the TUI: `/model gemini-3.1-pro`

Run `agy --help` (or try one round) locally to confirm which form your build
accepts. Antigravity serves Gemini 3.5 Flash / 3.1 Pro plus third-party
models (Claude Sonnet/Opus, GPT-OSS).

## Reasoning effort

No headless effort flag exposed (May 2026) — effort appears to be folded
into model display-name variants instead (e.g. `"Gemini 3.5 Flash (Low)"`).
The runner warns and ignores `--effort` for this provider; pick an effort
variant via `--model` if your build uses display names.

## Resume

Not supported headless. `--conversation <id>` and `-c`/`--continue` exist,
but print mode never surfaces the conversation ID to callers
(google-antigravity/antigravity-cli#7), and `--continue` resumes the
machine-global most-recent conversation — cross-contamination risk for
concurrent runs. The adapter always runs fresh rounds; prior feedback is
carried in the prompt instead.

## Auth

`export ANTIGRAVITY_API_KEY=...` or interactive login. Headless API-key auth
for unattended environments is still being tracked upstream
(antigravity-cli#78); verify auth with `--self-check` before a review run.
