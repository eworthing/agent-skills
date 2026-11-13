import type { AgentRequest, AgentRunner, EngineResult, Finding } from "../.opencode/plugins/code-review-opencode/engine.ts"
import type { Scope } from "../.opencode/plugins/code-review-opencode/scope.ts"

export type Call = { role: string; label: string; prompt: string; at: number }

export type Script = {
  finder?: (req: AgentRequest) => unknown | Promise<unknown>
  verifier?: (req: AgentRequest) => unknown | Promise<unknown>
  sweep?: (req: AgentRequest) => unknown | Promise<unknown>
  synthesize?: (req: AgentRequest) => unknown | Promise<unknown>
  delay?: (req: AgentRequest) => number
}

export function scripted(script: Script): { runner: AgentRunner; calls: Call[] } {
  const calls: Call[] = []
  const runner: AgentRunner = async (req) => {
    calls.push({ role: req.role, label: req.label, prompt: req.prompt, at: Date.now() })
    const wait = script.delay?.(req) ?? 0
    if (wait > 0) await new Promise((r) => setTimeout(r, wait))
    const fn =
      req.role === "finder"
        ? script.finder
        : req.role === "verifier"
          ? script.verifier
          : req.role === "sweep"
            ? script.sweep
            : script.synthesize
    return fn ? await fn(req) : req.role === "verifier" ? { verdict: "CONFIRMED", evidence: "line 1" } : { candidates: [] }
  }
  return { runner, calls }
}

export function candidate(file: string, line: number, summary: string, failure = "input X reaches the bad branch") {
  return { file, line, summary, failure_scenario: failure }
}

export function scopeOf(files: string[], extra: Partial<Scope> = {}): Scope {
  return {
    diffCommand: "git diff main...HEAD",
    files,
    claudeMdFiles: [],
    summary: `${files.length} changed files`,
    conventions: "(none noted)",
    root: "/repo",
    diffLines: 0,
    // A PR-number review pins the captured head; tests that exercise posting
    // get one by default unless they explicitly clear it.
    ...(extra.pr !== undefined && !("prHeadOid" in extra) ? { prHeadOid: "abc" } : {}),
    ...extra,
  }
}

export const CONFIRMED = (evidence = "the guard is missing at line 42") => ({ verdict: "CONFIRMED", evidence })
export const PLAUSIBLE = (evidence = "race is reachable under load") => ({ verdict: "PLAUSIBLE", evidence })
export const REFUTED = (evidence = "line 43 guards this") => ({ verdict: "REFUTED", evidence })

/** One verified finding for renderer/engine-result fixtures. */
export function engineFinding(overrides: Partial<Finding> = {}): Finding {
  return {
    file: "src/a.ts",
    line: 4,
    summary: "missing await",
    failure_scenario: "the promise rejects after the response is sent",
    verdict: "CONFIRMED",
    kind: "correctness",
    short_summary: "missing await",
    ...overrides,
  }
}

/** The shared EngineResult fixture; tests override only what they exercise. */
export function engineResult(overrides: Partial<EngineResult> = {}): EngineResult {
  return {
    level: "high",
    summary: "1 finding survived verification (high-effort review).",
    findings: [engineFinding()],
    refuted: [],
    stats: { finders: 8, candidates: 1, verifierAgents: 1, verified: 1, refuted: 0, dupes: 0, budgetDropped: 0, reported: 1 },
    partial: false,
    warnings: [],
    cell: "high",
    ...overrides,
  }
}
