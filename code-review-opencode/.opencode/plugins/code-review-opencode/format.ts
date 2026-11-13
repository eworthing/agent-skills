/**
 * Output contracts.
 *
 * `formatJson` is the reference's Yt contract: a bare JSON array whose objects
 * carry exactly file/line/summary/failure_scenario.
 * `formatReportFindings` is the argument the reference passes to the
 * ReportFindings tool.
 * `formatHuman` mirrors the reference's terminal renderer (`jt`).
 */
import type { EngineResult } from "./engine.ts"
import type { ReportedFinding } from "./reportfindings.ts"
import { lineOf, renderedLocation, pluralize, shortSummary } from "./finding.ts"

export function formatJson(result: EngineResult): string {
  return JSON.stringify(
    result.findings.map((f) => ({
      file: f.file,
      line: lineOf(f),
      summary: f.summary,
      failure_scenario: f.failure_scenario,
    })),
    null,
    2,
  )
}

export function formatReportFindings(result: EngineResult): {
  level: string
  findings: Array<Record<string, unknown>>
  partial: boolean
  warnings?: string[]
} {
  return {
    level: result.level,
    partial: result.partial,
    ...(result.warnings.length > 0 ? { warnings: result.warnings } : {}),
    findings: result.findings.map((f) => ({
      file: f.file,
      line: lineOf(f),
      summary: f.summary,
      short_summary: f.short_summary ?? shortSummary(f.summary),
      failure_scenario: f.failure_scenario,
      category: f.category ?? (f.kind === "cleanup" ? "cleanup" : "correctness"),
      ...(f.verdict ? { verdict: f.verdict } : {}),
    })),
  }
}

/** jt()'s nM(): render control characters instead of emitting them raw. */
function sanitizeControl(s: string): string {
  // Normalize CRLF first so a model's Windows line endings stay readable, then
  // render a lone CR. Leaving it raw lets a child overwrite earlier terminal
  // lines (or the indentation added below).
  return s.replace(/\r\n/g, "\n").replace(/[\u0000-\u0008\u000B-\u001F\u007F-\u009F]/g, (c) => {
    const code = c.codePointAt(0) ?? 0
    if (code === 27) return "␛"
    if (code < 32) return String.fromCodePoint(0x2400 + code)
    if (code === 127) return "␡"
    return `\\u{${code.toString(16).toUpperCase()}}`
  })
}

/**
 * The reference's terminal renderer (`jt`): a count line, then one numbered
 * `file:line: summary` block per finding with an optional failure scenario.
 * Continuation lines are indented to the number prefix, exactly as `jt` does.
 * Stats/refuted lists are reconstruction-only diagnostics behind `verbose`.
 */
export function formatHuman(result: EngineResult, opts: { includeRefuted?: boolean; verbose?: boolean } = {}): string {
  let out: string
  if (result.findings.length === 0) {
    out = "No findings."
  } else {
    const n = result.findings.length
    const suffix = n > 1 ? ", most severe first" : ""
    const body = result.findings
      .map((f, i) => {
        const loc = renderedLocation(f)
        const prefix = `${i + 1}. `
        const scenario = f.failure_scenario ? `\n\nFailure scenario: ${f.failure_scenario}` : ""
        return sanitizeControl(`${prefix}${loc}: ${f.summary}${scenario}`).replace(
          /\n(?=[^\n])/g,
          `\n${" ".repeat(prefix.length)}`,
        )
      })
      .join("\n\n")
    out = `${pluralize(n, "finding")}${suffix}:\n\n${body}`
  }

  if (result.partial) {
    out += `\n\nINCOMPLETE REVIEW: at least one review agent failed or was cancelled. Findings above are not the result of a complete run.`
    for (const w of result.warnings) out += `\n  - ${sanitizeControl(w)}`
  }

  if (opts.verbose) {
    out += `\n\nstats: cell=${result.cell} finders=${result.stats.finders} candidates=${result.stats.candidates} verifierAgents=${result.stats.verifierAgents} verified=${result.stats.verified} refuted=${result.stats.refuted} dupes=${result.stats.dupes} budgetDropped=${result.stats.budgetDropped} reported=${result.stats.reported}`
  }

  if (opts.includeRefuted && result.refuted.length > 0) {
    out += `\n\nRefuted (for transparency):`
    for (const r of result.refuted) {
      out += `\n  - ${sanitizeControl(`${renderedLocation(r)} — ${r.summary}`)}`
    }
  }

  return out
}

/** The reference's ReportFindings tool result text. */
export function formatToolResult(count: number): string {
  return count === 0 ? "No findings reported." : `${pluralize(count, "finding")} reported.`
}

/**
 * Per-finding outcomes after `--fix`. The reference re-reports findings through
 * `ReportFindings` and marks each one fixed/skipped/no change needed; a host
 * renders that list. OpenCode's command path has no findings card, so this
 * summary is posted as a synthetic message when the tool receives outcomes.
 */
export function formatOutcomeSummary(findings: ReportedFinding[]): string {
  const withOutcome = findings.filter((f) => f.outcome !== undefined)
  if (withOutcome.length === 0) return ""
  const count = (outcome: ReportedFinding["outcome"]) =>
    findings.filter((f) => f.outcome === outcome).length
  const unreported = findings.length - withOutcome.length
  const header =
    `Fix outcomes: ${count("fixed")} fixed, ${count("skipped")} skipped, ${count("no_change_needed")} no change needed` +
    (unreported > 0 ? `, ${unreported} outcome not reported` : "")
  // List every finding, including the ones whose outcome the model omitted. A
  // partial re-report must not present its subset as the complete fix status.
  const lines = findings.map((f) => {
    const outcome =
      f.outcome === undefined
        ? "outcome not reported"
        : f.outcome === "no_change_needed"
          ? "no change needed"
          : f.outcome
    return `- ${renderedLocation(f)} — ${outcome}`
  })
  return `${header}\n${lines.join("\n")}`
}
