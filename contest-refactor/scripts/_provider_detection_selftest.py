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
STARTUP = SKILL_ROOT / "references" / "startup.md"
PREFLIGHT = SKILL_ROOT / "scripts" / "preflight.py"


def main() -> int:
    failures: list[str] = []

    adapters = ADAPTERS.read_text(encoding="utf-8")
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

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("OK: opencode detection is prefix-based; preflight warns on unknown, quiet otherwise")
    return 0


if __name__ == "__main__":
    sys.exit(main())
