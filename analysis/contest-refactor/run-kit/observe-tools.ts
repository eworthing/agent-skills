// SPDX-License-Identifier: MIT
// contest-refactor run-kit: OBSERVE-ONLY tool telemetry (Tier-3 design data).
//
// Logs tool.execute.before/after payload shapes to JSONL. Never blocks, never
// throws, never mutates output — a buggy observer must not perturb the run, so
// every handler body is wrapped and failures are swallowed.
//
// Install (run time only, remove after the run):
//   cp observe-tools.ts ~/.config/opencode/plugins/
// Log: $CONTEST_REFACTOR_HOME/observe/tool-events.jsonl (default ~/.contest-refactor).
//
// What each record answers for the Tier-3 build:
//  - which tools fire, how often, at which commit boundaries (bash git commands)
//  - the after-hook payload shape: metadata keys + whether an exit code appears
//    (the Item-14 table's "uncertain" cell for opencode).

import { appendFileSync, mkdirSync } from "node:fs"
import { dirname, join } from "node:path"
import type { Plugin } from "@opencode-ai/plugin"

const LOG = join(
  process.env["CONTEST_REFACTOR_HOME"] ?? join(process.env["HOME"] ?? "/tmp", ".contest-refactor"),
  "observe",
  "tool-events.jsonl",
)
let dirReady = false

function log(rec: Record<string, unknown>): void {
  try {
    if (!dirReady) {
      mkdirSync(dirname(LOG), { recursive: true })
      dirReady = true
    }
    appendFileSync(LOG, JSON.stringify(rec) + "\n")
  } catch {
    // observe-only: never disturb the session
  }
}

function clip(v: unknown, n = 400): string {
  try {
    const s = typeof v === "string" ? v : JSON.stringify(v)
    return s === undefined ? "<undefined>" : s.length > n ? s.slice(0, n) + "..." : s
  } catch {
    return "<unserializable>"
  }
}

export const ObserveTools: Plugin = async ({ directory }) => ({
  "tool.execute.before": async (input, output) => {
    try {
      const args = (output.args ?? {}) as Record<string, unknown>
      log({
        ts: new Date().toISOString(),
        hook: "before",
        dir: directory,
        tool: input.tool,
        sessionID: input.sessionID,
        callID: input.callID,
        argKeys: Object.keys(args),
        command: input.tool === "bash" ? clip(args["command"]) : undefined,
      })
    } catch {
      /* observe-only */
    }
  },
  "tool.execute.after": async (input, output) => {
    try {
      const meta = (output.metadata ?? {}) as Record<string, unknown>
      const exitLike: Record<string, string> = {}
      for (const [k, v] of Object.entries(meta)) {
        if (/exit|status|code|signal/i.test(k)) exitLike[k] = clip(v, 60)
      }
      log({
        ts: new Date().toISOString(),
        hook: "after",
        dir: directory,
        tool: input.tool,
        sessionID: input.sessionID,
        callID: input.callID,
        title: clip(output.title, 200),
        outputBytes: (output.output ?? "").length,
        metadataKeys: Object.keys(meta),
        exitLike,
      })
    } catch {
      /* observe-only */
    }
  },
})
