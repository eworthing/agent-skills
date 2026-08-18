#!/usr/bin/env python3
"""Extract measured token usage for a dispatched arm, for `paired_arm_run.py finish --usage`.

HOST-SPECIFIC PLUMBING, not part of the skill's portable contract: it reads Claude Code's
per-subagent transcripts under
`~/.claude/projects/<project>/<session>/subagents/agent-a<name>-<hash>.jsonl`. It exists because
the plan requires per-pair spend to be committed as the run proceeds -- at ~220 agents across an
unknown number of sessions, sweep #2's sum-everything-at-the-end method is not reproducible.

Two accounting rules, both learned the hard way:

  * **Dedup by `message.id`.** Claude Code writes a usage blob more than once for the same
    assistant message (a partial record, then the complete one). Summing every record inflates the
    figure. The complete record is the one with the larger `output_tokens`, so dedup keeps the max.
  * **`cache_read_input_tokens` are not fresh tokens.** They are reported separately rather than
    folded into one number, because a run that looks expensive on a combined total may be almost
    entirely cache reads. `context_tokens_processed` is reported too, since that is the figure
    sweep #2's total was assembled from and the plan compares against it.

Usage: paired_arm_usage.py <agent-name> [<agent-name> ...]   -> JSON on stdout
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"


def _transcripts(agent_name: str) -> list[Path]:
    return sorted(PROJECTS.glob(f"*/*/subagents/agent-a{agent_name}-*.jsonl"))


def usage_for(agent_name: str) -> dict:
    paths = _transcripts(agent_name)
    if not paths:
        return {"agent": agent_name, "error": "no transcript found", "measured": False}
    by_id: dict[str, dict] = {}
    model = None
    for path in paths:
        for line in path.read_text().splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = record.get("message") or {}
            usage = message.get("usage")
            mid = message.get("id")
            if not usage or not mid:
                continue
            model = message.get("model") or model
            prior = by_id.get(mid)
            if prior is None or usage.get("output_tokens", 0) > prior.get("output_tokens", 0):
                by_id[mid] = usage
    fields = (
        "input_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
        "output_tokens",
    )
    totals = {f: sum(u.get(f, 0) for u in by_id.values()) for f in fields}
    return {
        "agent": agent_name,
        "model": model,
        "measured": True,
        "assistant_messages": len(by_id),
        "transcripts": [str(p) for p in paths],
        **totals,
        "context_tokens_processed": sum(totals.values()),
    }


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: paired_arm_usage.py <agent-name> [...]", file=sys.stderr)
        return 2
    out = {name: usage_for(name) for name in argv}
    out["pair_total_context_tokens"] = sum(
        v.get("context_tokens_processed", 0) for v in out.values() if isinstance(v, dict)
    )
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
