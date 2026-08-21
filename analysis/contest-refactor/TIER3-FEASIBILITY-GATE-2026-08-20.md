# Tier-3 Feasibility Gate — Five-Phase Validator + Host Hook (2026-08-20)

## Verdict: GO, for the automatic-invocation threat model

The register's Tier-3 entry (`docs/contest-refactor-review-register.md` § "Tier 3 — the big
build") requires this gate before the project is priced: pick the threat model, reuse the
Item-14 host analysis, and demonstrate **one qualifying interception point** — "Hook
implementation is not priced until one qualifying interception point is demonstrated." All
three are done below. The five-phase validator build is now priceable on the register's
standing estimate (~250–400k validator side); both of its stated prerequisites have shipped
since the estimate was written ([I1] ruleset-epoch classifier at `60e1294`; G29 version
enforcement at `d46360b`), so nothing upstream blocks it.

## 1. Threat model: automatic invocation, not tamper resistance

Decided on the register's own evidence, not preference:

- **The measured failure is forgetting, not evasion.** The prose instruction "run
  `validate-artifact.py`" fired 0/6 across two production runs and completed its full
  lifecycle — added (`ee21bc8`), measured dead, withdrawn (`a9ad8f3`) — in under 40 hours.
  A hook the model never has to remember closes exactly that gap.
- **Tamper resistance is not buildable today.** Item-14
  (`ITEM14-HOST-ATTESTATION-DESIGN-2026-08-18.md` § Verdict) verified that on all five
  supported harnesses the hook process runs as the same OS user as the agent's own shell,
  from agent-writable config; no harness offers privilege separation. The two
  enterprise/policy layers that would close this (Claude Code MDM-managed settings, Copilot
  `policy.d`) require organizational deployment a solo user does not have.

**Honest downgrade carried forward (Item-14 § 4):** the hook is a same-privilege control. It
defeats the everyday failure mode — a loop that never invokes the validator — and does NOT
defeat a deliberately adversarial model that edits or bypasses agent-writable hook config.
Any shipped design must state this in its installation doc and health check, per Item-14's
honest-downgrade field.

## 2. Demonstrated qualifying interception point (claude_code, `PreToolUse`)

Isolated scratch git repo; project-scoped `.claude/settings.json`; no user-level or global
config touched. A headless `claude -p` session (claude-haiku-4-5, `--max-turns 4`) was
instructed simply to run `git commit -m 'demo: hook interception test'` on a staged change.

Hook config (project `.claude/settings.json`):

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash",
        "hooks": [ { "type": "command",
                     "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/precommit-validator.sh" } ] }
    ]
  }
}
```

Hook script (validator stub at the commit boundary):

```bash
INPUT=$(cat)
CMD=$(printf '%s' "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)
case "$CMD" in
  *"git commit"*)
    printf '%s | intercepted: %s\n' "$(date -u +%H:%M:%S)" "$CMD" >> "$CLAUDE_PROJECT_DIR/hook-fired.log"
    echo "validator stub: G-stub FAIL on drafted subject; commit blocked (fail-closed demo)" >&2
    exit 2 ;;
esac
exit 0
```

Observed, mechanically (2026-08-20):

| Capability the validator needs | Evidence |
| --- | --- |
| **Automatic invocation** — fires with zero model cooperation | Hook fired on the session's first `git commit` attempt; the model was given no instruction about hooks or validators |
| **Commit-draft input** — sees the drafted subject *before* the commit exists | `hook-fired.log`: `23:59:50 \| intercepted: git commit -m 'demo: hook interception test'` — the exact input G22 needs pre-commit |
| **Fail-closed blocking** | Exit 2 blocked the tool call: `git log` unchanged (no commit landed), staged change intact, nothing destroyed |
| **Diagnostic round-trip** — model receives the validator's reason | Session output quoted the stub's stderr verbatim and stopped, as instructed |

## 3. Named interception point per provider (from Item-14, verified there)

| Provider | Interception point | Status |
| --- | --- | --- |
| claude_code | `PreToolUse` / `PostToolUse` hooks | **Demonstrated above** |
| codex | `PreToolUse` / `PostToolUse` hooks | Documented, undemonstrated |
| opencode | `tool.execute.before` / `tool.execute.after` plugin | Documented, undemonstrated — **first to demonstrate in the build phase: it is the actual production runner** (both instrumented runs) |
| gemini / agy | `BeforeTool` / `AfterTool` | Documented, undemonstrated |
| copilot | `preToolUse` / `postToolUse` | Documented, undemonstrated |
| `unknown` | **none** | Declared behavior: no interception exists; the installation health check must surface "no hook active for this provider" so validation failure is distinguishable from a missing hook (register design item) |

## 4. What this gate deliberately did not do

- No validator was built — the stub proves the interception point, not the phases. The
  five-phase validator (`step1-post-write | step3-prearchive | postarchive |
  postchallenge-precommit | postcommit`, per-phase gate sets, commit-draft input) remains
  the expensive half and the actual project.
- Only claude_code was demonstrated. One qualifying point is the gate's stated bar; the
  opencode demonstration belongs at the top of the build phase, not here — launching
  opencode sessions while a production opencode run is live on this machine adds risk for
  no gate-level information.
- No hook configuration was installed anywhere outside the isolated scratch repo. This
  repo still ships zero hook config, unchanged from Item-14's finding.

## 5. What the owner decides next

Price and schedule the build. The register's sequencing stands: validator first (the piece
that makes the 27 mechanized gates execute), hook per provider second, opencode first among
providers. Prerequisites are cleared; the threat model is fixed by this gate; the
interception mechanism is proven.
