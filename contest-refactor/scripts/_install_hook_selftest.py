#!/usr/bin/env python3
"""Selftest for hooks/install-hook.sh (Tier-3 hook installer).

This is the only piece of the project that writes a user's agent config, so the
property under test is not "does it install" but "does it ever destroy
something it did not create". Those configs hold hooks this tool knows nothing
about; clobbering them would be a worse failure than never installing.

Every case runs against a temporary HOME. The real ~/.claude and ~/.codex are
never touched.

Run directly; exit 0 = pass.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
INSTALLER = SKILL_ROOT / "hooks" / "install-hook.sh"

FOREIGN = {
    "matcher": "Grep|Glob|Read|Search",
    "hooks": [{"type": "command", "command": "'/somewhere/cbm-code-discovery-gate'"}],
}


def run(args: list[str], home: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [str(INSTALLER), *args],
        capture_output=True,
        text=True,
        env={"HOME": str(home), "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"},
        check=False,
    )
    return proc.returncode, proc.stdout + proc.stderr


def codex_cfg(home: Path) -> Path:
    return home / ".codex" / "hooks.json"


def seed(home: Path, payload: dict) -> Path:
    p = codex_cfg(home)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return p


def entries(home: Path) -> list:
    return json.loads(codex_cfg(home).read_text(encoding="utf-8"))["hooks"]["PreToolUse"]


def main() -> int:
    assert INSTALLER.is_file(), f"installer missing: {INSTALLER}"
    checks = 0

    # 1. A foreign hook survives installation. This is the whole point.
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        seed(home, {"hooks": {"PreToolUse": [FOREIGN]}})
        rc, out = run(["codex"], home)
        assert rc == 0, f"install failed: {out}"
        got = entries(home)
        assert FOREIGN in got, "installer DESTROYED a pre-existing foreign hook"
        assert any("precommit-validator" in json.dumps(e) for e in got), "our hook missing"
        assert len(got) == 2, f"expected foreign + ours, got {len(got)}"
        checks += 1

        # 2. A backup is written before any modification.
        backups = list((home / ".codex").glob("hooks.json.bak-*"))
        assert backups, "no backup taken before writing"
        assert json.loads(backups[0].read_text())["hooks"]["PreToolUse"] == [FOREIGN], (
            "backup does not hold the pre-install state"
        )
        checks += 1

        # 3. Installing twice is idempotent -- no duplicate entry.
        rc, out = run(["codex"], home)
        assert rc == 0 and "already installed" in out, out
        assert len(entries(home)) == 2, "second install duplicated the entry"
        checks += 1

        # 4. Uninstall removes ONLY ours.
        rc, out = run(["--uninstall", "codex"], home)
        assert rc == 0, out
        got = entries(home)
        assert got == [FOREIGN], f"uninstall must leave the foreign hook alone, got {got}"
        checks += 1

    # 5. A config we cannot parse is refused, not overwritten.
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        p = codex_cfg(home)
        p.parent.mkdir(parents=True)
        p.write_text("{ this is not json", encoding="utf-8")
        rc, out = run(["codex"], home)
        assert rc == 2, "a malformed config must be refused"
        assert p.read_text(encoding="utf-8") == "{ this is not json", (
            "malformed config was modified"
        )
        checks += 1

    # 6. Dry run writes nothing at all.
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        seed(home, {"hooks": {"PreToolUse": [FOREIGN]}})
        before = codex_cfg(home).read_text(encoding="utf-8")
        rc, out = run(["--dry-run", "codex"], home)
        assert rc == 0 and "dry run" in out
        assert codex_cfg(home).read_text(encoding="utf-8") == before, "dry run modified the config"
        assert not list((home / ".codex").glob("*.bak-*")), "dry run took a backup"
        checks += 1

    # 7. Missing config is created from nothing.
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        rc, out = run(["codex"], home)
        assert rc == 0, out
        assert any("precommit-validator" in json.dumps(e) for e in entries(home))
        checks += 1

    # 8. An unsupported provider is refused and says why opencode is absent.
    with tempfile.TemporaryDirectory() as tmp:
        rc, out = run(["opencode"], Path(tmp))
        assert rc == 2, "unsupported provider must be refused"
        assert "not yet demonstrated" in out, "must explain opencode's absence"
        checks += 1

    print(f"_install_hook_selftest: OK ({checks} assertions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
