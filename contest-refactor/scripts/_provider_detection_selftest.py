#!/usr/bin/env python3
"""Self-test: provider detection must not test for an environment variable that
does not exist, and preflight must warn when detection lands on `unknown`.

Found live 2026-08-19. A real opencode run reached HALT_SUCCESS at loop 1 under an
inline self-vetted challenger. The cause was NOT that opencode lacks subagent spawn --
provider-adapters.md documents `opencode run --model <m> '<prompt>'` as its spawn
command, and the binary ships it. The cause was the detection rule, which tested for
`OPENCODE_SESSION`. That variable appears NOWHERE in the opencode binary: a scan of
every `OPENCODE_*` string it references (80+, including OPENCODE_PID,
OPENCODE_WORKSPACE_ID, OPENCODE_CLIENT) has no SESSION entry. So opencode could never
be detected, every opencode run fell through to `unknown`, and every terminal success
it reached rested on a challenge the Critic administered to itself.

Two guards:

  1. `OPENCODE_SESSION` must not reappear in provider-adapters.md, and the rule must
     stay prefix-based (`OPENCODE_*`). A prefix rule survives upstream renaming the
     specific variable, which is exactly what bit us -- the section was dated
     "verified 2026-05-09" and had drifted since.
  2. preflight must WARN (never fail) on `provider == "unknown"`, and startup.md must
     actually pass it. A detection bug and a genuinely spawn-less host look identical
     from inside the loop, and both silently weaken the terminal verdict; the warning
     is the only place that difference is visible before tokens are spent.

Run: python3 scripts/_provider_detection_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
ADAPTERS = SKILL_ROOT / "references" / "provider-adapters.md"
# The reviewer-spawn profile and the read-only allow-list were split into their own
# file so Step 3 stops reloading the whole adapter set (DISPLACEMENT-2026-08-21.md
# candidate A). Both halves are still "the provider adapters" for the assertions
# below, so read them together -- otherwise this guard silently stops covering the
# reviewer profiles it exists to protect.
ADAPTERS_REVIEWER = SKILL_ROOT / "references" / "provider-adapters-reviewer.md"
STARTUP = SKILL_ROOT / "references" / "startup.md"
PREFLIGHT = SKILL_ROOT / "scripts" / "preflight.py"
RESUME = SKILL_ROOT / "references" / "resume-detection.md"
SKILL = SKILL_ROOT / "SKILL.md"
TRUST = SKILL_ROOT / "references" / "trust-model.md"


def main() -> int:
    failures: list[str] = []

    adapters = ADAPTERS.read_text(encoding="utf-8") + ADAPTERS_REVIEWER.read_text(encoding="utf-8")
    generic_dispatch_docs = {
        "SKILL.md": SKILL.read_text(encoding="utf-8"),
        "trust-model.md": TRUST.read_text(encoding="utf-8"),
    }
    for name, body in generic_dispatch_docs.items():
        if "subagent_type: general-purpose" in body:
            failures.append(
                f"{name} hardcodes Claude's `general-purpose` agent type; generic loop "
                "dispatch must route through provider-adapters.md"
            )
        if re.search(r"fresh `Agent` invocation", body):
            failures.append(
                f"{name} describes generic dispatch as a fresh `Agent` invocation; "
                "that provider-specific term belongs only in provider-adapters.md"
            )
        if "provider-adapters.md" not in body:
            failures.append(f"{name} no longer points generic dispatch at provider-adapters.md")
    if 'subagent_type: "general-purpose"' not in adapters:
        failures.append("the Claude-specific adapter lost its `general-purpose` agent type")
    unknown_section = adapters.split("### unknown", 1)[-1].split("\n## ", 1)[0]
    for host in ("Copilot CLI", "Gemini Antigravity CLI"):
        if host not in unknown_section:
            failures.append(
                f"the unknown-provider fallback does not explicitly classify {host} as inline"
            )
    if "OPENCODE_SESSION" in adapters:
        failures.append(
            "provider-adapters.md references OPENCODE_SESSION again -- that variable does not "
            "exist in the opencode binary, so the rule can never fire and every opencode run "
            "degrades to provider=unknown and an inline self-vetted challenger"
        )
    if "OPENCODE_*" not in adapters:
        failures.append(
            "the opencode detection rule is no longer prefix-based; a single-variable rule is "
            "what went stale last time (section dated 'verified 2026-05-09')"
        )

    # Guard 3 (found live 2026-08-23, codex): the predicates must live in EXACTLY ONE file.
    # resume-detection.md carried a second copy, and Step 0.5 reads THAT file -- so when the
    # 2026-08-19 OPENCODE_SESSION fix landed in provider-adapters.md, the stale copy is the
    # one that actually ran. Two runs (opencode 2026-08-23, codex 2026-08-23) fell through to
    # provider=unknown and lost their independent challenger to this drift.
    resume = RESUME.read_text(encoding="utf-8")
    for token in ("CLAUDECODE", "CODEX_", "OPENCODE_"):
        if token in resume:
            failures.append(
                f"resume-detection.md names {token!r} again -- Step 0.5 must POINT at "
                f"provider-adapters.md's table, never restate it; the restated copy is what "
                f"drifted and cost two runs their independent challenger"
            )

    # Guard 4 (same incident): detection must trigger on a session-scoped variable. CODEX_HOME
    # is a path override for ~/.codex (unset on a default install, and set whenever the tool is
    # merely installed), so a rule keyed on it can never fire for a real codex run. Scoped to
    # the Detection section -- CODEX_HOME is legitimate in $SKILL_DIR resolution further down.
    det = adapters.split("## Detection", 1)[-1].split("\n## ", 1)[0]
    # Check the TABLE ROWS, not the prose: the corrected section names CODEX_HOME in the
    # negative ("a path override never detects"), and a naive substring test cannot tell a
    # rationale from a trigger -- the same trap the --read-only guard above documents.
    det_rows = "\n".join(ln for ln in det.splitlines() if ln.strip().startswith("|"))
    if "CODEX_HOME" in det_rows:
        failures.append(
            "the codex detection rule keys on CODEX_HOME again -- that is a path override, "
            "unset on a default install, so the rule never fires and every codex run degrades "
            "to provider=unknown with an inline self-vetted challenger"
        )
    if not ("CODEX_SESSION_ID" in det_rows or "CODEX_THREAD_ID" in det_rows):
        failures.append(
            "the codex detection rule no longer names a session-scoped variable "
            "(CODEX_SESSION_ID / CODEX_THREAD_ID) -- those are what a live codex run actually "
            "exports, verified 2026-08-23"
        )

    # The reviewer is contractually read-only. Under opencode its documented
    # enforcement was `--read-only`, a flag that does not exist -- and opencode does
    # not reject unknown flags, so it was silently ignored and the reviewer spawned
    # with write allowed. A fictional safety control is worse than a missing one,
    # because it reads as covered.
    # Check the COMMAND, not the prose: the corrected text mentions --read-only in the
    # negative ("there is no --read-only flag"), and a naive substring test cannot tell
    # a warning from a prescription.
    spawn_cmds = [ln for ln in adapters.splitlines() if ln.strip().startswith("opencode run")]
    if not spawn_cmds:
        failures.append("no `opencode run` spawn command found in provider-adapters.md")
    for cmd in spawn_cmds:
        if "--read-only" in cmd:
            failures.append(
                f"a spawn command prescribes --read-only again: {cmd.strip()!r} -- opencode has "
                f"no such flag and silently ignores unknown ones, so the reviewer would spawn "
                f"with WRITE allowed while the doc claims enforcement"
            )
    if '"edit": "deny"' not in adapters:
        failures.append(
            "the opencode reviewer profile no longer names the real read-only mechanism "
            "(`permission` config, edit: deny) -- without it there is no way to actually "
            "constrain the reviewer on that provider"
        )
    # --model takes provider/model; a bare id fails the spawn, which falls back to inline
    # and quietly costs the run its independent challenger.
    if "opencode-go/deepseek-v4-flash" not in adapters:
        failures.append(
            "the opencode model id lost its provider prefix; `--model` requires provider/model "
            "and a bare id is not a valid model"
        )

    # codex hard-errors (exit 2) on unknown flags, unlike opencode which ignores them.
    # So every documented codex spawn command failed outright and fell back to inline --
    # the same lost-challenger outcome as the opencode bug, by a different mechanism.
    # Verified against codex-cli 0.147.0: --no-ask-user, --output-format and --deny-tool
    # do not exist; --json and --sandbox {read-only|workspace-write|danger-full-access} do.
    for phantom in ("--no-ask-user", "--deny-tool", "--output-format json"):
        if phantom in adapters:
            failures.append(
                f"provider-adapters.md prescribes {phantom!r} again -- codex exits 2 on it, so "
                f"the spawn fails and the run silently degrades to inline with no independent "
                f"challenger"
            )
    # Guard 5 (found live 2026-08-23): every codex spawn must PIN its reasoning effort.
    # An unpinned `codex exec` inherits model_reasoning_effort from the operator's
    # ~/.codex/config.toml -- a value set for interactive chat, not autonomous loops. The
    # same artifact could come from a `low` Critic on one machine and an `xhigh` Critic on
    # another, and CURRENT_REVIEW.json has no effort field to record which. Pinning is what
    # makes a run reproducible across machines.
    codex_cmds = [ln for ln in adapters.splitlines() if ln.strip().startswith("codex exec")]
    if not codex_cmds:
        failures.append("no `codex exec` spawn command found in the provider adapters")
    for cmd in codex_cmds:
        if "model_reasoning_effort=" not in cmd:
            failures.append(
                f"a codex spawn command does not pin reasoning effort: {cmd.strip()!r} -- it "
                f"would inherit the operator's interactive config, so the Critic's tier becomes "
                f"machine-dependent and is recorded nowhere"
            )

    if "--sandbox read-only" not in adapters:
        failures.append(
            "the codex reviewer profile no longer uses --sandbox read-only -- that is a REAL "
            "enforcement gate, and losing it drops the reviewer back to a prompt-only contract"
        )

    if "--provider" not in STARTUP.read_text(encoding="utf-8"):
        failures.append(
            "startup.md's preflight invocation no longer passes --provider, so a run that will "
            "have no independent challenger says nothing about it until halt"
        )

    unknown = subprocess.run(
        [sys.executable, str(PREFLIGHT), str(SKILL_ROOT), "--provider", "unknown"],
        capture_output=True,
        text=True,
        check=False,
    )
    if unknown.returncode != 0:
        failures.append(
            f"preflight must WARN, not fail, on provider=unknown (running anywhere is "
            f"deliberate); got exit {unknown.returncode}"
        )
    if "WARNING" not in unknown.stderr or "provisional" not in unknown.stderr:
        failures.append(
            f"preflight gave no usable warning for provider=unknown; stderr={unknown.stderr!r}"
        )

    known = subprocess.run(
        [sys.executable, str(PREFLIGHT), str(SKILL_ROOT), "--provider", "opencode"],
        capture_output=True,
        text=True,
        check=False,
    )
    if "WARNING" in known.stderr:
        failures.append(
            f"a known provider must not warn -- noise on the normal path trains readers to "
            f"ignore it; stderr={known.stderr!r}"
        )

    # --- the validator's default-model table matches the prose ---------------
    # G19 fails a loop whose *_model_source == "default" but whose model does not
    # equal _PROVIDER_DEFAULTS. That makes the table a second copy of the prose,
    # and on 2026-08-19 the two disagreed: the opencode profile had moved to the
    # qualified `opencode-go/...` id (a bare id is rejected by the CLI) while the
    # table still held the bare one -- so a correctly-spawned opencode loop
    # tripped G19 on every emit, twice, on a live run. Derived from the prose
    # headings rather than a hand-copied list, so a provider is covered the
    # moment it is documented.
    sys.path.insert(0, str(SKILL_ROOT / "scripts"))
    import _artifact_core

    section_re = re.compile(r"^### (?P<name>[a-z_]+)\b")
    default_re = re.compile(r"^- \*\*Default model\*\*: `(?P<model>[^`]+)`")
    pairs: list[tuple[str, str]] = []
    provider: str | None = None
    for line in adapters.splitlines():
        m = section_re.match(line)
        if m:
            provider = m.group("name")
            continue
        d = default_re.match(line)
        if d and provider:
            pairs.append((provider, d.group("model")))
    if len(pairs) < 3:
        failures.append(
            f"expected to parse >=3 documented default models, parsed {len(pairs)} -- the "
            "prose heading or bullet shape changed and this guard has gone blind"
        )
    for provider_name, model in pairs:
        expected = _artifact_core._PROVIDER_DEFAULTS.get(provider_name)
        if expected != model:
            failures.append(
                f"provider-adapters.md documents {provider_name} default {model!r} but "
                f"_artifact_core._PROVIDER_DEFAULTS says {expected!r} -- G19 would fire on "
                "every loop of a correctly-spawned run"
            )

    # --- no bare opencode model id survives anywhere ------------------------
    # opencode's --model requires provider/model; a bare id is rejected by the CLI.
    # The qualified form landed in the loop and reviewer profiles first, leaving the
    # helper tier and a descriptive line behind -- three sites, fixed one at a time
    # across two days. A class guard is cheaper than finding the fourth.
    for lineno, line in enumerate(adapters.splitlines(), 1):
        for hit in re.finditer(r"(?<![\w/-])deepseek-v4-flash", line):
            if not line[: hit.start()].endswith("opencode-go/"):
                failures.append(
                    f"provider-adapters.md:{lineno} names a BARE `deepseek-v4-flash`; "
                    "opencode's --model requires provider/model and rejects a bare id"
                )

    # --- opencode native-task adapter (Instrumented run #7, 2026-08-24) ---------
    # opencode has no `general-purpose` task type -- a run that tried it before
    # falling back to the real type `general` proves the mistake is one prompt
    # away from recurring. And the honest inline fallback (no subprocess, no
    # native task) must say so in the recorded metadata, not be inferred later.
    opencode_section = adapters.split("### opencode", 1)[-1].split("\n### ", 1)[0]
    if "general-purpose" in opencode_section:
        failures.append(
            "the opencode section names `general-purpose` -- that task type does not exist "
            "on opencode (claude-code vocabulary); the native task type is `general`"
        )
    if 'spawn_isolation: "inline"' not in opencode_section:
        failures.append(
            "the opencode section lost its honest inline-fallback recording "
            '(`spawn_isolation: "inline"`) -- without it a failed native-task/subprocess '
            "spawn has nowhere honest to record what actually ran"
        )
    if "inherited" not in adapters.split("## Model overrides", 1)[-1].split("\n## ", 1)[0]:
        failures.append(
            "the Model overrides section's source enumeration lost `inherited` -- the G19 "
            "gate (_artifact_history.py) accepts it, so omitting it here is a doc/gate split "
            "that reintroduces the run-2026-08-24 attribution defect"
        )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("OK: opencode detection is prefix-based; preflight warns on unknown, quiet otherwise")
    return 0


if __name__ == "__main__":
    sys.exit(main())
