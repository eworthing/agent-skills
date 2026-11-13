import { test } from "node:test"
import assert from "node:assert/strict"
import { REPORT_FINDINGS_SCHEMA, normalizeReportFindings } from "../.opencode/plugins/code-review-opencode/reportfindings.ts"
import {
  formatHuman,
  formatJson,
  formatOutcomeSummary,
  formatReportFindings,
  formatToolResult,
} from "../.opencode/plugins/code-review-opencode/format.ts"
import { engineResult } from "./helpers.ts"

const base = {
  file: "src/a.ts",
  line: 4,
  summary: "missing await",
  short_summary: "missing await",
  failure_scenario: "the promise rejects after the response is sent",
}

test("ReportFindings accepts the reference payload", () => {
  const r = normalizeReportFindings({ level: "high", findings: [base, { ...base, verdict: "CONFIRMED" }] })
  assert.equal(r.ok, true)
  if (r.ok) {
    assert.equal(r.level, "high")
    assert.equal(r.findings.length, 2)
    assert.equal(r.findings[1].verdict, "CONFIRMED")
  }
})

test("an all-dropped report names the finding error, not the level note", () => {
  const r = normalizeReportFindings({
    level: "ultra",
    findings: [{ ...base, verdict: "REFUTED" }],
  })
  assert.equal(r.ok, false)
  if (!r.ok) assert.match(r.error, /verdict "REFUTED" is invalid/)
})

test("ReportFindings rejects the whole call for an invalid finding", () => {
  const good = { ...base, summary: "valid finding" }
  const missing = { ...base, failure_scenario: undefined }
  const badVerdict = { ...base, verdict: "REFUTED" }
  const r = normalizeReportFindings({ findings: [missing, badVerdict, good] })
  assert.equal(r.ok, false)
  if (!r.ok) assert.match(r.error, /failure_scenario must be a string/)
  const verdict = normalizeReportFindings({ findings: [badVerdict, good] })
  assert.equal(verdict.ok, false)
  if (!verdict.ok) assert.match(verdict.error, /verdict "REFUTED" is invalid/)
  // An entirely unusable list is rejected for the same reason.
  assert.equal(normalizeReportFindings({ findings: [{ ...base, failure_scenario: undefined }] }).ok, false)
  assert.equal(normalizeReportFindings({ findings: [{ ...base, file: 42 }] }).ok, false)
  // The reference schema is `file: string` with no min-length, so "" is valid.
  assert.equal(normalizeReportFindings({ findings: [{ ...base, file: "" }] }).ok, true)
  // The schema is closed: unknown fields must be rejected, not carried through.
  assert.equal(normalizeReportFindings({ findings: [{ ...base, kind: "correctness" }] }).ok, false)
})

test("a capitalized level is normalized instead of dropped from typed metadata", () => {
  const r = normalizeReportFindings({ level: "High", findings: [base] })
  assert.equal(r.ok, true)
  if (r.ok) {
    assert.equal(r.level, "high")
    assert.equal(r.notes.length, 0)
  }
})

test("the typed report metadata carries the partial flag and warnings", () => {
  const payload = formatReportFindings(result(true))
  assert.equal(payload.partial, true)
  assert.deepEqual(payload.warnings, ["finder angle-B returned no usable result"])
})

test("ReportFindings rejects above 32 and overlong fields, normalizes level, and rejects invalid outcome", () => {
  const capped = normalizeReportFindings({
    level: "ultra",
    findings: Array.from({ length: 33 }, (_, i) => ({ ...base, summary: `s${i}` })),
  })
  assert.equal(capped.ok, false)
  if (!capped.ok) assert.match(capped.error, /at most 32 entries; merge or rank/)

  const badLevel = normalizeReportFindings({ level: "ultra", findings: [base] })
  assert.equal(badLevel.ok, true)
  if (badLevel.ok) {
    assert.equal(badLevel.level, undefined)
    assert.match(badLevel.notes.join(" "), /level "ultra" is invalid/)
  }

  const longShort = normalizeReportFindings({
    findings: [{ ...base, short_summary: "x".repeat(61) }],
  })
  assert.equal(longShort.ok, false)
  if (!longShort.ok) assert.match(longShort.error, /short_summary must be at most 60/)

  const longCategory = normalizeReportFindings({
    findings: [{ ...base, category: "x".repeat(41) }],
  })
  assert.equal(longCategory.ok, false)
  if (!longCategory.ok) assert.match(longCategory.error, /category must be at most 40/)

  const normalizedOutcome = normalizeReportFindings({
    findings: [{ ...base, outcome: "FIXED" }],
  })
  assert.equal(normalizedOutcome.ok, true)
  if (normalizedOutcome.ok) assert.equal(normalizedOutcome.findings[0].outcome, "fixed")

  const invalid = normalizeReportFindings({ findings: [{ ...base, outcome: "fixed-later" }] })
  assert.equal(invalid.ok, false)
  if (!invalid.ok) assert.match(invalid.error, /outcome .* is invalid/)
})

test("short_summary maxLength counts code points, not UTF-16 units", () => {
  const sixty = "🔥".repeat(60)
  const accepted = normalizeReportFindings({
    findings: [{ ...base, short_summary: sixty }],
  })
  assert.equal(accepted.ok, true)
  if (accepted.ok) assert.equal(accepted.findings[0].short_summary, sixty)
  const rejected = normalizeReportFindings({
    findings: [{ ...base, short_summary: "🔥".repeat(61) }],
  })
  assert.equal(rejected.ok, false)
})

test("the adapter schema mirrors the recovered tool schema", () => {
  assert.equal(REPORT_FINDINGS_SCHEMA.properties.findings.maxItems, 32)
  assert.deepEqual(REPORT_FINDINGS_SCHEMA.properties.level.enum, ["low", "medium", "high", "xhigh", "max"])
  assert.deepEqual(REPORT_FINDINGS_SCHEMA.properties.findings.items.required, ["file", "summary", "failure_scenario"])
  assert.deepEqual(REPORT_FINDINGS_SCHEMA.properties.findings.items.properties.verdict.enum, ["CONFIRMED", "PLAUSIBLE"])
  // Published JSON schema (report-findings-tool.md) closes both objects and
  // gives `line` the JS safe-integer bounds.
  assert.equal(REPORT_FINDINGS_SCHEMA.additionalProperties, false)
  assert.equal(REPORT_FINDINGS_SCHEMA.properties.findings.items.additionalProperties, false)
  assert.equal(REPORT_FINDINGS_SCHEMA.properties.findings.items.properties.line.minimum, -9007199254740991)
  assert.equal(REPORT_FINDINGS_SCHEMA.properties.findings.items.properties.line.maximum, 9007199254740991)
})

function result(partial = false) {
  return engineResult({
    partial,
    warnings: partial ? ["finder angle-B returned no usable result"] : [],
  })
}

test("the host findings payload carries level, category, and short_summary", () => {
  const r = result()
  r.findings[0].category = "reuse"
  const payload = formatReportFindings(r)
  assert.equal(payload.level, "high")
  assert.equal(payload.findings[0].category, "reuse")
  assert.equal(payload.findings[0].short_summary, "missing await")
  assert.equal(payload.findings[0].verdict, "CONFIRMED")
})

test("the JSON contract carries exactly the four reference fields", () => {
  const parsed = JSON.parse(formatJson(result())) as Array<Record<string, unknown>>
  assert.deepEqual(Object.keys(parsed[0]).sort(), ["failure_scenario", "file", "line", "summary"])
})

test("a partial run keeps the JSON output a bare array", () => {
  const text = formatJson(result(true))
  assert.doesNotThrow(() => JSON.parse(text))
  assert.equal(text.trimStart()[0], "[")
  assert.doesNotMatch(text, /WARNING/)
})

test("the human renderer mirrors the reference terminal format", () => {
  const text = formatHuman(result())
  assert.match(text, /^1 finding:\n/)
  // jt() renders `file:line: summary`; verdict is not part of the terminal text.
  assert.match(text, /1\. src\/a\.ts:4: missing await/)
  assert.doesNotMatch(text, /\[CONFIRMED\]/)
  assert.match(text, /Failure scenario: the promise rejects/)
})

test("the human renderer sanitizes control characters", () => {
  const r = result()
  r.findings[0].summary = "bad\u0000summary"
  const text = formatHuman(r)
  assert.doesNotMatch(text, /\u0000/)
  assert.match(text, /bad␀summary/)

  // CRLF from a Windows-formatted source is normalized to a clean newline; a
  // lone CR is rendered so it cannot overwrite a previous terminal line.
  r.findings[0].summary = "line one\r\nline two"
  const carriage = formatHuman(r)
  assert.doesNotMatch(carriage, /\r/)
  assert.match(carriage, /line one\n {3}line two/)
  r.findings[0].summary = "before\rafter"
  assert.match(formatHuman(r), /before␍after/)

  // A git-quoted filename may decode to a real newline. The report must show
  // it escaped; otherwise the filename can forge a numbered finding line.
  const file = result()
  file.findings[0].file = "x\n3. src/pay.ts:61: balance can go negative"
  const rendered = formatHuman(file)
  assert.doesNotMatch(rendered, /x\n3\. src\/pay\.ts/)
  assert.match(rendered, /x\\n3\. src\/pay\.ts/)
})

test("no findings renders as the reference's 'No findings.'", () => {
  const empty = engineResult({ findings: [], summary: "No findings survived verification." })
  assert.equal(formatHuman(empty), "No findings.")
  assert.equal(formatJson(empty), "[]")
})

test("partial runs are never presented as complete", () => {
  const text = formatHuman(result(true))
  assert.match(text, /INCOMPLETE REVIEW/)
  assert.match(text, /finder angle-B returned no usable result/)
})

test("ReportFindings tool result text matches the reference", () => {
  assert.equal(formatToolResult(0), "No findings reported.")
  assert.equal(formatToolResult(1), "1 finding reported.")
  assert.equal(formatToolResult(3), "3 findings reported.")
})

test("a non-positive line is omitted from every output contract", () => {
  const r = result()
  r.findings[0].line = 0
  const human = formatHuman(r)
  assert.match(human, /src\/a\.ts: missing await/)
  assert.doesNotMatch(human, /:0:/)
  const json = JSON.parse(formatJson(r)) as Array<Record<string, unknown>>
  assert.equal(json[0].line, undefined)
  const payload = formatReportFindings(r)
  assert.equal(payload.findings[0].line, undefined)

  const normalized = normalizeReportFindings({ findings: [{ ...base, line: 0 }] })
  assert.equal(normalized.ok, true)
  if (normalized.ok) {
    assert.equal(normalized.findings[0].line, undefined)
    assert.match(normalized.notes.join(" "), /not a positive integer/)
  }
})

test("fix outcomes render a summary and stay silent without outcomes", () => {
  const findings = [
    { ...base, outcome: "fixed" as const },
    { ...base, file: "src/b.ts", line: 9, outcome: "skipped" as const },
    { ...base, file: "src/c.ts", line: 2, outcome: "no_change_needed" as const },
  ]
  const text = formatOutcomeSummary(findings)
  assert.match(text, /Fix outcomes: 1 fixed, 1 skipped, 1 no change needed/)
  assert.match(text, /src\/a\.ts:4 — fixed/)
  assert.match(text, /src\/c\.ts:2 — no change needed/)
  assert.equal(formatOutcomeSummary([base]), "")
})
