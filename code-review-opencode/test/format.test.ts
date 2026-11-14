import { test } from "node:test"
import assert from "node:assert/strict"
import { formatHuman, formatReportFindings } from "../.opencode/plugins/code-review-opencode/format.ts"
import { engineFinding, engineResult } from "./helpers.ts"

test("the truncation notice calls the pre-cap count findings, not verified findings", () => {
  const result = engineResult({
    findings: [
      engineFinding({ file: "src/a.ts", line: 1 }),
      engineFinding({ file: "src/b.ts", line: 2, verdict: "PLAUSIBLE" }),
    ],
    truncatedFrom: 5,
  })
  const human = formatHuman(result)
  assert.match(human, /Showing 2 of 5 findings/)
  assert.doesNotMatch(human, /verified findings/)
  const report = formatReportFindings(result)
  assert.ok(report.warnings?.some((w) => w.includes("truncated from 5 findings")))
  assert.equal(report.warnings?.some((w) => w.includes("verified findings")), false)
})
