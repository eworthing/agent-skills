#!/usr/bin/env python3
"""Run cost accounting from opencode's sqlite store (opencode >= 1.18, db-backed).

Reads ~/.local/share/opencode/opencode.db READ-ONLY (sqlite URI mode=ro).
Message ids are the table's primary key, so records are already deduplicated —
unlike Claude Code JSONL transcripts (see the CC transcript accounting rule:
dedup by message.id there). Reading rules embedded in every report:
cache_read tokens are NOT fresh tokens; billed cost ≈ per-message resident
context x messages, so `resident` (Σ input+cache_read over assistant messages)
is the number that tracks spend, not the input total alone.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_DB = Path.home() / ".local" / "share" / "opencode" / "opencode.db"


def _ms(iso: str) -> int:
    return int(datetime.fromisoformat(iso).timestamp() * 1000)


def query(db: Path, dir_like: str, since: str | None, until: str | None) -> list[dict]:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    q = (
        "SELECT id,title,directory,parent_id,time_created,time_updated,model,cost,"
        "tokens_input,tokens_output,tokens_reasoning,tokens_cache_read,tokens_cache_write "
        "FROM session WHERE directory LIKE ?"
    )
    params: list = [f"%{dir_like}%"]
    if since:
        q += " AND time_created >= ?"
        params.append(_ms(since))
    if until:
        q += " AND time_created <= ?"
        params.append(_ms(until))
    q += " ORDER BY time_created"
    sessions = [dict(r) for r in con.execute(q, params)]
    for s in sessions:
        per_model: dict[str, dict] = defaultdict(
            lambda: {
                "messages": 0,
                "input": 0,
                "output": 0,
                "reasoning": 0,
                "cache_read": 0,
                "cache_write": 0,
                "resident": 0,
                "cost": 0.0,
            }
        )
        n_msgs = 0
        for (data,) in con.execute("SELECT data FROM message WHERE session_id=?", (s["id"],)):
            n_msgs += 1
            try:
                m = json.loads(data)
            except json.JSONDecodeError:
                continue
            if m.get("role") != "assistant":
                continue
            t = m.get("tokens") or {}
            cache = t.get("cache") or {}
            key = f"{m.get('providerID')}/{m.get('modelID')}"
            agg = per_model[key]
            agg["messages"] += 1
            agg["input"] += t.get("input", 0) or 0
            agg["output"] += t.get("output", 0) or 0
            agg["reasoning"] += t.get("reasoning", 0) or 0
            agg["cache_read"] += cache.get("read", 0) or 0
            agg["cache_write"] += cache.get("write", 0) or 0
            agg["resident"] += (t.get("input", 0) or 0) + (cache.get("read", 0) or 0)
            agg["cost"] += m.get("cost", 0) or 0
        s["message_rows"] = n_msgs
        s["per_model"] = dict(per_model)
    con.close()
    return sessions


def to_markdown(sessions: list[dict]) -> str:
    out = [
        "# opencode run cost accounting",
        "",
        "> Reading rules: cache_read ≠ fresh tokens; billed cost ≈ per-message resident",
        "> context x messages — `resident` = Σ(input + cache_read) over assistant messages.",
        "> Message ids are primary keys in the store: already deduplicated.",
        "",
    ]
    totals: dict[str, dict] = defaultdict(
        lambda: {
            "messages": 0,
            "input": 0,
            "output": 0,
            "reasoning": 0,
            "cache_read": 0,
            "cache_write": 0,
            "resident": 0,
            "cost": 0.0,
        }
    )
    for s in sessions:
        ts = datetime.fromtimestamp(s["time_created"] / 1000, UTC).isoformat()[:16]
        parent = " (child)" if s["parent_id"] else ""
        out.append(f"## {s['id']}{parent} — {s['title'][:70]}")
        out.append(f"- dir: `{s['directory']}` · created {ts}Z · {s['message_rows']} message rows")
        for model, a in s["per_model"].items():
            out.append(
                f"- `{model}`: {a['messages']} msgs · in {a['input']:,} · out {a['output']:,}"
                f" · reason {a['reasoning']:,} · cache r/w {a['cache_read']:,}/{a['cache_write']:,}"
                f" · resident {a['resident']:,} · cost {a['cost']:.4f}"
            )
            for k, v in a.items():
                totals[model][k] += v
        out.append("")
    out += ["## Totals by model", ""]
    for model, a in sorted(totals.items()):
        out.append(
            f"- `{model}`: {a['messages']} msgs · in {a['input']:,} · out {a['output']:,}"
            f" · reason {a['reasoning']:,} · cache r/w {a['cache_read']:,}/{a['cache_write']:,}"
            f" · resident {a['resident']:,} · cost {a['cost']:.4f}"
        )
    out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--dir-like", required=True, help="substring of session.directory")
    ap.add_argument("--since", help="ISO date/datetime (local) lower bound")
    ap.add_argument("--until", help="ISO date/datetime (local) upper bound")
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--out-md", type=Path)
    args = ap.parse_args()
    sessions = query(args.db, args.dir_like, args.since, args.until)
    md = to_markdown(sessions)
    if args.out_json:
        args.out_json.write_text(json.dumps(sessions, indent=1, default=str) + "\n")
    if args.out_md:
        args.out_md.write_text(md)
    else:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
