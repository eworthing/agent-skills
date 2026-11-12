import { test } from "node:test"
import assert from "node:assert/strict"
import { mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import {
  artifactFileName,
  buildReportArtifact,
  writeReportArtifact,
} from "../.opencode/plugins/code-review-opencode/artifact.ts"
import { engineFinding, engineResult } from "./helpers.ts"

test("the report artifact carries the run identity and engine result", () => {
  const artifact = buildReportArtifact({
    result: engineResult({
      level: "max",
      summary: "1 finding survived verification (max-effort review).",
      findings: [engineFinding({ summary: "missing guard" })],
      refuted: [{ file: "src/b.ts", line: 3, summary: "false positive" }],
      stats: { finders: 10, candidates: 4, verifierAgents: 4, verified: 4, refuted: 1, dupes: 0, budgetDropped: 0, reported: 1 },
      cell: "max",
      truncatedFrom: 18,
    }),
    files: ["src/a.ts", "src/b.ts"],
    id: "report-1",
    generatedAt: new Date("2026-11-11T12:00:00.000Z"),
  })
  assert.equal(artifact.report_id, "report-1")
  assert.equal(artifact.generated_at, "2026-11-11T12:00:00.000Z")
  assert.equal(artifact.level, "max")
  assert.equal(artifact.cell, "max")
  assert.equal(artifact.summary, "1 finding survived verification (max-effort review).")
  assert.deepEqual(artifact.files_changed, ["src/a.ts", "src/b.ts"])
  assert.equal(artifact.fanned_out, 10)
  assert.equal(artifact.refuted.length, 1)
  assert.equal(artifact.stats.verified, 4)
  assert.equal(artifact.truncated_from, 18)
  assert.equal(artifact.findings[0].verdict, "CONFIRMED")
  assert.equal(artifactFileName("report-1", new Date("2026-11-11T12:00:00.000Z")), "2026-11-11T12-00-00-000Z-report-1.json")
})

test("the artifact is written atomically with private permissions", async () => {
  const root = mkdtempSync(join(tmpdir(), "code-review-artifact-"))
  const path = await writeReportArtifact({ root, result: engineResult(), files: ["src/a.ts"] })
  assert.ok(path)
  const payload = JSON.parse(readFileSync(path!, "utf8")) as { report_id: string; files_changed: string[] }
  assert.ok(payload.report_id)
  assert.deepEqual(payload.files_changed, ["src/a.ts"])
  assert.equal(statSync(path!).mode & 0o777, 0o600)
  rmSync(root, { recursive: true, force: true })
})

test("an artifact write failure does not fail the review", async () => {
  const root = mkdtempSync(join(tmpdir(), "code-review-artifact-fail-"))
  const blocked = join(root, "reports")
  writeFileSync(blocked, "not a directory")
  const path = await writeReportArtifact({ root, result: engineResult(), files: [], directory: blocked })
  assert.equal(path, undefined)
  rmSync(root, { recursive: true, force: true })
})
