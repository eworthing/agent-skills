import { test } from "node:test"
import assert from "node:assert/strict"
import { runReview, type AgentRunner } from "../.opencode/plugins/code-review-opencode/engine.ts"
import { resolveCell, type Level, type VersionID } from "../.opencode/plugins/code-review-opencode/cells.ts"
import { CONFIRMED, PLAUSIBLE, REFUTED, candidate, scopeOf, scripted, type Script } from "./helpers.ts"

const cellOf = (version: VersionID, family: string, level: Level) => resolveCell(version, family, level)

async function review(opts: {
  version?: VersionID
  family?: string
  level?: Level
  script: Script
  files?: string[]
  limit?: number | "all"
  semanticMerge?: boolean
  finderBudget?: number
  signal?: AbortSignal
}) {
  const cell = cellOf(opts.version ?? "cc-2.1.318", opts.family ?? "claude-sonnet-5", opts.level ?? "high")
  const { runner, calls } = scripted(opts.script)
  const result = await runReview({
    level: opts.level ?? "high",
    cell,
    scope: scopeOf(opts.files ?? ["src/a.ts"]),
    runner,
    statedLimit: opts.limit,
    semanticMerge: opts.semanticMerge,
    finderBudget: opts.finderBudget,
    signal: opts.signal,
    concurrency: 4,
  })
  return { result, calls }
}

/* 1 */ test("one obvious deterministic bug is found and reported", async () => {
  const { result } = await review({
    script: {
      finder: (req) =>
        req.label === "angle-A"
          ? { candidates: [candidate("src/a.ts", 42, "guard is inverted")] }
          : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].file, "src/a.ts")
  assert.equal(result.findings[0].line, 42)
  assert.equal(result.findings[0].verdict, "CONFIRMED")
  assert.match(result.summary, /1 finding survived verification/)
})

/* 2 */ test("several independent bugs are all reported", async () => {
  const { result } = await review({
    script: {
      finder: (req) => {
        if (req.label === "angle-A")
          return { candidates: [candidate("src/a.ts", 10, "off by one"), candidate("src/a.ts", 20, "missing await")] }
        if (req.label === "angle-B") return { candidates: [candidate("src/b.ts", 5, "removed guard")] }
        if (req.label === "reuse") return { candidates: [candidate("src/c.ts", 7, "duplicate helper", "cost: duplicate")] }
        return { candidates: [] }
      },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 4)
})

/* 3 */ test("a false-positive candidate is rejected by verification", async () => {
  const { result } = await review({
    script: {
      finder: () => ({ candidates: [candidate("src/a.ts", 3, "looks wrong but is guarded")] }),
      verifier: () => REFUTED(),
    },
  })
  assert.equal(result.findings.length, 0)
  assert.equal(result.refuted.length, 1)
  assert.match(result.summary, /No findings survived verification/)
})

/* 4 */ test("an input-dependent defect survives as PLAUSIBLE", async () => {
  const { result } = await review({
    script: {
      finder: () => ({ candidates: [candidate("src/a.ts", 8, "race under load")] }),
      verifier: () => PLAUSIBLE(),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].verdict, "PLAUSIBLE")
})

/* 5 */ test("duplicates across finders are verified once", async () => {
  const dup = candidate("src/a.ts", 11, "same defect")
  const { result, calls } = await review({
    script: {
      finder: (req) =>
        req.label === "angle-A" || req.label === "angle-B" ? { candidates: [dup] } : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.stats.dupes, 1)
  assert.equal(calls.filter((c) => c.role === "verifier").length, 1)
})

/* 5b */ test("paraphrased findings at the same line merge; a distinct claim stays", async () => {
  const a = candidate(
    "src/a.ts",
    11,
    "the discount subtracts percent as an absolute amount instead of a percentage of total",
  )
  const b = candidate(
    "src/a.ts",
    11,
    "replaced percentage-based discount total * (1 - percent / 100) with absolute subtraction total - percent",
  )
  const c = candidate("src/a.ts", 11, "new validation guard for percent outside 0-100 is missing entirely")
  const { result } = await review({
    script: {
      finder: (req) =>
        req.label === "angle-A"
          ? { candidates: [a] }
          : req.label === "angle-B"
            ? { candidates: [b] }
            : req.label === "angle-C"
              ? { candidates: [c] }
              : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 2)
  assert.equal(result.stats.dupes, 1)
})

/* 5c */ test("a cleanup helper and its adjacent-line paraphrase merge; a convention claim stays", async () => {
  const helper = candidate(
    "src/format.ts",
    1,
    "A money-formatting helper was added but the existing call site still inlines `.toFixed(2)`, so the formatting rule now lives in two places instead of being routed through one mechanism.",
  )
  const paraphrase = candidate(
    "src/format.ts",
    2,
    "New formatMoney re-implements the 2-decimal money formatting already inlined in reportTotal, and report.ts is not switched to use it.",
  )
  const convention = candidate(
    "src/format.ts",
    1,
    "New formatMoney is a default export, violating the repo CLAUDE.md rule \"Never use default exports; always use named exports.\"",
  )
  const { result } = await review({
    script: {
      finder: (req) =>
        req.label === "reuse"
          ? { candidates: [helper] }
          : req.label === "simplification"
            ? { candidates: [paraphrase] }
            : req.label === "conventions"
              ? { candidates: [convention] }
              : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 2)
  assert.equal(result.stats.dupes, 1)
})

/* 5d */ test("semantic merge applies the synthesizer's index decisions", async () => {
  const a = candidate("src/a.ts", 1, "discount formula bug one")
  const b = candidate("src/a.ts", 2, "discount formula bug two")
  const { result, calls } = await review({
    semanticMerge: true,
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [a] } : req.label === "angle-B" ? { candidates: [b] } : { candidates: [] },
      verifier: () => CONFIRMED(),
      synthesize: (req) =>
        req.label === "dedup"
          ? { summary: "deduped", decisions: [{ index: 0 }, { index: 1 }] }
          : { summary: "merged by root cause", decisions: [{ index: 0, merge: [1] }] },
    },
  })
  assert.equal(result.findings.length, 1)
  assert.match(result.summary, /^merged by root cause/)
  assert.equal(calls.filter((c) => c.role === "synthesize" && c.label === "merge").length, 1)
})

/* 5e */ test("semantic merge failure falls back to the deterministic report", async () => {
  const a = candidate("src/a.ts", 1, "discount formula bug one")
  const b = candidate("src/a.ts", 2, "discount formula bug two")
  const { result } = await review({
    semanticMerge: true,
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [a] } : req.label === "angle-B" ? { candidates: [b] } : { candidates: [] },
      verifier: () => CONFIRMED(),
      synthesize: () => null,
    },
  })
  assert.equal(result.findings.length, 2)
  assert.match(result.warnings.join(" "), /semantic merge/)
})

/* 5h */ test("semantic pre-verify dedup merges before verification", async () => {
  const a = candidate("src/a.ts", 1, "missing await on save")
  const b = candidate("src/a.ts", 1, "currency symbol is wrong")
  const { result, calls } = await review({
    semanticMerge: true,
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [a] } : req.label === "angle-B" ? { candidates: [b] } : { candidates: [] },
      verifier: () => CONFIRMED(),
      synthesize: (req) =>
        req.label === "dedup"
          ? { summary: "deduped", decisions: [{ index: 0, merge: [1] }] }
          : { summary: "ranked", decisions: [{ index: 0 }] },
    },
  })
  assert.equal(calls.filter((c) => c.role === "synthesize" && c.label === "dedup").length, 1)
  assert.equal(calls.filter((c) => c.role === "verifier").length, 1)
  assert.equal(result.findings.length, 1)
})

/* 5h4 */ test("failed semantic pre-dedup falls back to the paraphrase merge", async () => {
  const a = candidate(
    "src/a.ts",
    11,
    "the discount subtracts percent as an absolute amount instead of a percentage of total",
  )
  const b = candidate(
    "src/a.ts",
    11,
    "replaced percentage-based discount total * (1 - percent / 100) with absolute subtraction total - percent",
  )
  const { result, calls } = await review({
    semanticMerge: true,
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [a] } : req.label === "angle-B" ? { candidates: [b] } : { candidates: [] },
      verifier: () => CONFIRMED(),
      synthesize: () => null,
    },
  })
  assert.equal(calls.filter((c) => c.role === "verifier").length, 1)
  assert.equal(result.findings.length, 1)
  assert.match(result.warnings.join(" "), /candidate dedup/)
})

/* 5f */ test("findings carry the producing angle as category", async () => {
  const { result } = await review({
    script: {
      finder: (req) =>
        req.label === "reuse" ? { candidates: [candidate("src/a.ts", 1, "duplicate helper")] } : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].category, "reuse")
})

/* 5g */ test("a merged same-line pair does not self-reference its location", async () => {
  const a = candidate("src/a.ts", 1, "missing await on save")
  const b = candidate("src/a.ts", 1, "currency symbol is wrong")
  const { result } = await review({
    semanticMerge: true,
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [a] } : req.label === "angle-B" ? { candidates: [b] } : { candidates: [] },
      verifier: () => CONFIRMED(),
      synthesize: (req) =>
        req.label === "dedup"
          ? { summary: "deduped", decisions: [{ index: 0 }, { index: 1 }] }
          : { summary: "merged", decisions: [{ index: 0, merge: [1] }] },
    },
  })
  assert.equal(result.findings.length, 1)
  assert.doesNotMatch(result.findings[0].summary, /also at: src\/a\.ts:1/)
})

/* 5h2 */ test("non-Latin summaries at the same line are not normalized to the same claim", async () => {
  const a = candidate("src/a.ts", 10, "null チェックが欠けている")
  const b = candidate("src/a.ts", 10, "ループ境界の誤り")
  const { result } = await review({
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [a] } : req.label === "angle-B" ? { candidates: [b] } : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 2)
})

/* 5h3 */ test("a canonicalized path never collapses an unchanged file onto a shorter in-scope name", async () => {
  const { result } = await review({
    files: ["a.ts"],
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [candidate("src/a.ts", 3, "caller passes the old shape")] } : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].file, "src/a.ts")
})

/* 5h4 */ test("a wf162 re-emitted finding does not replace a verified anchor", async () => {
  const { result } = await review({
    version: "cc-workflow-2.1.162",
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [candidate("src/a.ts", 10, "missing null guard")] } : { candidates: [] },
      verifier: () => CONFIRMED(),
      synthesize: () => ({
        summary: "synthesized",
        findings: [{ file: "src/a.ts", line: 14, summary: "missing null guard", failure_scenario: "f" }],
      }),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].line, 10)
  assert.equal(result.findings[0].verdict, "CONFIRMED")
})

/* 5h5 */ test("an empty text synthesis returns verified findings and marks the run partial", async () => {
  const { result } = await review({
    version: "cc-workflow-2.1.162",
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [candidate("src/a.ts", 10, "real bug")] } : { candidates: [] },
      verifier: () => CONFIRMED(),
      synthesize: () => ({ summary: "omitted", findings: [] }),
    },
  })
  // With no replacement entry this is not a merge decision: silently returning
  // an empty report would hide a verified defect behind "No findings."
  assert.equal(result.findings.length, 1)
  assert.match(result.summary, /empty report/)
  assert.equal(result.partial, true)
})

test("text synthesis keeps a verified finding when it rewords the same line", async () => {
  const { result } = await review({
    version: "cc-workflow-2.1.162",
    script: {
      finder: (req) =>
        req.label === "angle-A"
          ? { candidates: [candidate("src/a.ts", 10, "missing null check before dereferencing profile")] }
          : { candidates: [] },
      verifier: () => CONFIRMED(),
      synthesize: () => ({
        summary: "reworded",
        findings: [
          candidate("src/a.ts", 10, "profile is accessed without validating the user object", "crash"),
        ],
      }),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].summary, "missing null check before dereferencing profile")
  assert.equal(result.findings[0].verdict, "CONFIRMED")
  assert.notEqual(result.partial, true)
})

/* 5i */ test("two file-level findings with different wording stay separate", async () => {
  const a = {
    file: "src/a.ts",
    summary: "validation for the discount percent is missing",
    failure_scenario: "a negative percent reaches the total",
  }
  const b = {
    file: "src/a.ts",
    summary: "discount percent is subtracted as an absolute amount",
    failure_scenario: "the total is wrong for every percent",
  }
  const { result } = await review({
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [a] } : req.label === "angle-B" ? { candidates: [b] } : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 2)
})

test("a single-lens finder's kind wins over a mislabeled candidate", async () => {
  const { result } = await review({
    script: {
      finder: (req) =>
        req.label === "angle-A"
          ? {
              candidates: [
                {
                  ...candidate("src/a.ts", 4, "dead helper retained", "the branch is unreachable"),
                  category: "dead-code",
                  kind: "cleanup",
                },
              ],
            }
          : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 1)
  // The correctness finder produced this candidate; a wrong `kind` must not
  // demote a crash to cleanup and rank it behind style findings.
  assert.equal(result.findings[0].kind, "correctness")
})

test("a cleanup category cannot demote a single-lens correctness finding", async () => {
  const { result } = await review({
    limit: 1,
    script: {
      finder: (req) => {
        if (req.label === "angle-A") {
          return {
            candidates: [
              {
                ...candidate("src/a.ts", 4, "null dereference", "the profile is null"),
                category: "cleanup",
              },
            ],
          }
        }
        if (req.label === "reuse") {
          return { candidates: [candidate("src/a.ts", 8, "duplicate helper", "cost: duplication")] }
        }
        return { candidates: [] }
      },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].summary, "null dereference")
  assert.equal(result.findings[0].kind, "correctness")
})

test("a grouped finder still attributes each candidate to its own lens", async () => {
  const { result } = await review({
    finderBudget: 2,
    script: {
      finder: (req) =>
        req.label === "angles-1"
          ? {
              candidates: [
                {
                  ...candidate("src/a.ts", 4, "dead helper retained", "the branch is unreachable"),
                  category: "dead-code",
                  kind: "cleanup",
                },
              ],
            }
          : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].kind, "cleanup")
})

test("a failed finder is counted separately from a finder that found nothing", async () => {
  const { result } = await review({
    script: {
      finder: (req) => (req.label === "angle-A" ? null : { candidates: [] }),
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.stats.finderFailures, 1)
  assert.equal(result.partial, true)
  assert.equal(result.stats.finders > 1, true)
})

test("paraphrased candidates are verified before the post-verify merge", async () => {
  const a = candidate("src/a.ts", 11, "the discount subtracts percent as an absolute amount")
  const b = candidate("src/a.ts", 11, "replaced percentage-based discount with absolute subtraction")
  const { result, calls } = await review({
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [a] } : req.label === "angle-B" ? { candidates: [b] } : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(calls.filter((c) => c.role === "verifier").length, 2)
  assert.equal(result.findings.length, 1)
})

test("a b/-prefixed candidate path maps to the changed file", async () => {
  const { result } = await review({
    script: {
      finder: (req) =>
        req.label === "angle-A"
          ? { candidates: [candidate("b/src/a.ts", 7, "missing await")] }
          : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings[0].file, "src/a.ts")
})

test("text synthesis does not attach a verified verdict to an invented finding", async () => {
  const { result } = await review({
    version: "cc-workflow-2.1.162",
    script: {
      finder: (req) =>
        req.label === "angle-A"
          ? { candidates: [candidate("src/a.ts", 10, "missing await on the save path")] }
          : { candidates: [] },
      verifier: () => CONFIRMED(),
      synthesize: () => ({
        summary: "invented",
        findings: [candidate("src/a.ts", 90, "an unrelated cache invalidation bug")],
      }),
    },
  })
  assert.equal(result.findings.length, 0)
  assert.match(result.warnings.join(" "), /did not match a verified candidate/)
  // The synthesizer may have reworded a real finding; the dropped entry means
  // the remainder cannot be presented as a complete review.
  assert.equal(result.partial, true)
})

test("text synthesis does not backfill a finding the synthesizer merged away", async () => {
  const a = candidate("src/a.ts", 10, "missing await on the save path")
  const b = candidate("src/a.ts", 20, "the save path never awaits the write")
  const { result } = await review({
    version: "cc-workflow-2.1.162",
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [a] } : req.label === "angle-B" ? { candidates: [b] } : { candidates: [] },
      verifier: () => CONFIRMED(),
      synthesize: () => ({
        summary: "merged",
        findings: [a],
      }),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].summary, a.summary)
})

/* 5j */ test("the deterministic merge does not override semantic merge decisions", async () => {
  const a = candidate("src/a.ts", 1, "missing await on the save path")
  const b = candidate("src/a.ts", 1, "missing validation on the save path")
  const { result } = await review({
    semanticMerge: true,
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [a] } : req.label === "angle-B" ? { candidates: [b] } : { candidates: [] },
      verifier: () => CONFIRMED(),
      synthesize: (req) =>
        req.label === "dedup"
          ? { summary: "deduped", decisions: [{ index: 0 }, { index: 1 }] }
          : { summary: "ranked", decisions: [{ index: 0 }, { index: 1 }] },
    },
  })
  assert.equal(result.findings.length, 2)
})

/* 5k */ test("a paraphrase that matches two clusters merges both", async () => {
  const a = candidate("src/a.ts", 10, "missing await on the save path")
  const b = candidate("src/a.ts", 10, "currency symbol is wrong in the formatter")
  const c = candidate("src/a.ts", 10, "missing await on the save path and currency symbol is wrong")
  const { result } = await review({
    script: {
      finder: (req) =>
        req.label === "angle-A"
          ? { candidates: [a, c] }
          : req.label === "angle-B"
            ? { candidates: [b] }
            : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 1)
})

/* 5l */ test("an empty grouped verdict list is a partial run, not a clean one", async () => {
  const { result } = await review({
    version: "cc-workflow-2.1.221",
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [candidate("src/a.ts", 1, "real bug")] } : { candidates: [] },
      verifier: () => ({ verdicts: [] }),
    },
  })
  assert.equal(result.partial, true)
  assert.match(result.warnings.join(" "), /usable verdicts/)
})

/* 5m */ test("wf162 synthesis cannot add an unverified finding", async () => {
  const { result } = await review({
    version: "cc-workflow-2.1.162",
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [candidate("src/a.ts", 1, "real bug")] } : { candidates: [] },
      verifier: () => CONFIRMED(),
      synthesize: () => ({
        summary: "synthesized",
        findings: [
          { file: "src/a.ts", line: 1, summary: "real bug", failure_scenario: "f" },
          { file: "src/b.ts", line: 9, summary: "invented bug", failure_scenario: "f" },
        ],
      }),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.match(result.warnings.join(" "), /did not match/)
})

/* 5n */ test("a grouped finder's cleanup candidate keeps the cleanup kind", async () => {
  const { result } = await review({
    finderBudget: 2,
    script: {
      finder: (req) =>
        req.label === "angles-2"
          ? {
              candidates: [
                {
                  file: "src/a.ts",
                  line: 1,
                  summary: "duplicate helper",
                  failure_scenario: "the two copies drift",
                  category: "reuse",
                },
              ],
            }
          : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].kind, "cleanup")
  assert.equal(result.findings[0].category, "reuse")
})

/* 6 */ test("two distinct defects on nearby lines survive the 2.1.162 line bucket", async () => {
  const a = candidate("src/a.ts", 10, "first defect")
  const b = candidate("src/a.ts", 12, "second defect")
  const finder = (req: { label: string }) =>
    req.label === "angle-A" ? { candidates: [a] } : req.label === "angle-B" ? { candidates: [b] } : { candidates: [] }

  const modern = await review({ script: { finder, verifier: () => CONFIRMED() } })
  assert.equal(modern.result.findings.length, 2)

  const legacy = await review({
    version: "cc-workflow-2.1.162",
    level: "high",
    script: { finder, verifier: () => CONFIRMED() },
  })
  // The claim is part of the dedup key: a nearby line alone must not collapse
  // a different defect.
  assert.equal(legacy.result.findings.length, 2)
  assert.equal(legacy.result.stats.dupes, 0)
})

/* 7 */ test("a deleted validation guard is found by Angle B", async () => {
  const { result } = await review({
    script: {
      finder: (req) => (req.label === "angle-B" ? { candidates: [candidate("src/a.ts", 30, "removed null guard")] } : { candidates: [] }),
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings[0].summary, "removed null guard")
})

/* 8 */ test("a cross-file contract regression is found by Angle C", async () => {
  const { result } = await review({
    script: {
      finder: (req) =>
        req.label === "angle-C" ? { candidates: [candidate("src/a.ts", 4, "caller still passes the old shape")] } : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 1)
})

/* 9 */ test("a CLAUDE.md violation is found by the conventions angle", async () => {
  const { result, calls } = await review({
    script: {
      finder: (req) =>
        req.label === "conventions"
          ? { candidates: [candidate("src/a.ts", 2, "uses default export; CLAUDE.md forbids it", "cost: rule broken")] }
          : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 1)
  const conventionsPrompt = calls.find((c) => c.label === "conventions")?.prompt ?? ""
  assert.match(conventionsPrompt, /### Conventions \(CLAUDE\.md\)/)
})

/* 10 */ test("a non-applicable CLAUDE.md produces nothing from conventions", async () => {
  const { result } = await review({
    script: { finder: () => ({ candidates: [] }), verifier: () => CONFIRMED() },
  })
  assert.equal(result.findings.length, 0)
  assert.equal(result.stats.candidates, 0)
})

/* 10a */ test("a budget-grouped finder keeps its lenses' combined candidate capacity", async () => {
  const { result } = await review({
    finderBudget: 2,
    script: {
      finder: (req) =>
        req.label === "angles-1"
          ? {
              candidates: Array.from({ length: 7 }, (_, i) =>
                candidate(`src/a${i}.ts`, i + 1, `bug ${i}`),
              ),
            }
          : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.stats.candidates, 7)
})

/* 10b */ test("a swept cleanup finding keeps its cleanup kind", async () => {
  const { result } = await review({
    level: "max",
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [candidate("src/a.ts", 1, "real bug")] } : { candidates: [] },
      verifier: () => CONFIRMED(),
      sweep: () => ({ candidates: [{ ...candidate("src/b.ts", 2, "duplicate helper"), category: "reuse" }] }),
    },
  })
  const swept = result.findings.find((f) => f.summary === "duplicate helper")
  assert.equal(swept?.kind, "cleanup")
})

/* 11 */ test("correctness outranks cleanup when the cap forces a cut", async () => {
  const { result } = await review({
    level: "high",
    limit: 1,
    script: {
      finder: (req) => {
        if (req.label === "angle-A") return { candidates: [candidate("src/a.ts", 1, "correctness bug")] }
        if (req.label === "reuse") return { candidates: [candidate("src/a.ts", 2, "cleanup idea", "cost: duplication")] }
        return { candidates: [] }
      },
      verifier: (req) => (req.prompt.includes("cleanup idea") ? CONFIRMED("cleanup evidence") : PLAUSIBLE("bug evidence")),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].summary, "correctness bug")
})

/* 12 */ test("an entirely correct diff reports no findings and does not pad", async () => {
  const { result } = await review({ script: { finder: () => ({ candidates: [] }) } })
  assert.equal(result.findings.length, 0)
  assert.match(result.summary, /No findings survived verification/)
})

/* 13 */ test("candidate and result limits hold on a large diff", async () => {
  const { result } = await review({
    level: "xhigh",
    script: {
      finder: (req) => ({
        candidates: Array.from({ length: 8 }, (_, i) =>
          candidate(`src/${req.label}-${i}.ts`, i + 1, `${req.label} defect ${i}`),
        ),
      }),
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.stats.finders, 10)
  assert.equal(result.stats.candidates, 80)
  assert.equal(result.findings.length, 15)
})

/* 13a */ test("the sweep's gaps are added without a second verification pass", async () => {
  const { result, calls } = await review({
    level: "max",
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [candidate("src/a.ts", 1, "finder bug")] } : { candidates: [] },
      verifier: () => CONFIRMED(),
      sweep: () => ({ candidates: [candidate("src/b.ts", 2, "sweep gap")] }),
    },
  })
  assert.equal(result.findings.length, 2)
  assert.equal(result.findings.find((f) => f.summary === "sweep gap")?.verdict, "PLAUSIBLE")
  assert.equal(calls.filter((c) => c.role === "verifier").length, 1)
})

test("a workflow sweep keeps a reworded gap at a known line", async () => {
  const confirmed = candidate("src/cache.ts", 40, "cache is never invalidated after a write")
  const gap = candidate("src/cache.ts", 40, "write path does not flush the cache to disk")
  const { result } = await review({
    version: "cc-workflow-2.1.162",
    level: "max",
    files: ["src/cache.ts"],
    script: {
      finder: (req) => (req.label === "angle-A" ? { candidates: [confirmed] } : { candidates: [] }),
      verifier: () => CONFIRMED(),
      sweep: () => ({ candidates: [gap] }),
      synthesize: () => ({ summary: "both defects", findings: [confirmed, gap] }),
    },
  })
  // Workflow sweep dedup is exact-claim only; the paraphrase heuristic used to
  // discard this second defect before the synthesizer ever saw it.
  assert.equal(result.partial, false)
  assert.equal(result.findings.length, 2)
  assert.ok(result.findings.some((f) => f.summary === gap.summary))
})

test("a current-mode sweep keeps a reworded gap at a known line", async () => {
  const confirmed = candidate("src/cache.ts", 40, "cache is never invalidated after a write")
  const gap = candidate("src/cache.ts", 40, "write path does not flush the cache to disk")
  const { result } = await review({
    level: "max",
    files: ["src/cache.ts"],
    semanticMerge: true,
    script: {
      finder: (req) => (req.label === "angle-A" ? { candidates: [confirmed] } : { candidates: [] }),
      verifier: () => CONFIRMED(),
      sweep: () => ({ candidates: [gap] }),
      synthesize: (req) =>
        req.label === "merge"
          ? { summary: "both defects", decisions: [{ index: 0 }, { index: 1 }] }
          : { candidates: [] },
    },
  })
  // v2.1.318 cells also use exact-claim dedup for the sweep; the paraphrase
  // heuristic silently dropped this distinct gap before the synthesizer.
  assert.equal(result.partial, false)
  assert.equal(result.findings.length, 2)
  assert.ok(result.findings.some((f) => f.summary === gap.summary))
})

/* 13b */ test("--max-findings raises the max-effort cap", async () => {
  const { result } = await review({
    level: "max",
    limit: 20,
    script: {
      finder: (req) => ({
        candidates: Array.from({ length: 4 }, (_, i) =>
          candidate(`src/${req.label}-${i}.ts`, i + 1, `${req.label} defect ${i}`),
        ),
      }),
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 20)
})

/* 14 */ test("the 2.1.162 verifier budget is hard: 25 verified, the rest recorded", async () => {
  const { result } = await review({
    version: "cc-workflow-2.1.162",
    level: "xhigh",
    script: {
      finder: (req) => ({
        candidates: Array.from({ length: 8 }, (_, i) =>
          candidate(`src/${req.label}-${i}.ts`, i + 1, `${req.label} defect ${i}`),
        ),
      }),
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.stats.finders, 9)
  assert.equal(result.stats.candidates, 72)
  assert.equal(result.stats.verified, 25)
  assert.equal(result.stats.budgetDropped, 47)
})

/* 15 */ test("a malformed finder response is dropped and marks the run incomplete", async () => {
  const { result } = await review({
    script: { finder: (req) => (req.label === "angle-A" ? "I found a bug, trust me" : { candidates: [] }) },
  })
  assert.equal(result.findings.length, 0)
  assert.equal(result.partial, true)
  assert.ok(result.warnings.some((w) => w.includes("angle-A")))
})

/* 16 */ test("a malformed verifier response drops the candidate and marks the run incomplete", async () => {
  const { result } = await review({
    script: {
      finder: () => ({ candidates: [candidate("src/a.ts", 1, "maybe")] }),
      verifier: () => ({}),
    },
  })
  assert.equal(result.findings.length, 0)
  assert.equal(result.partial, true)
})

/* 17 */ test("cancellation returns a partial result instead of hanging or claiming completeness", async () => {
  const controller = new AbortController()
  const { result } = await review({
    signal: controller.signal,
    script: {
      finder: (req) => {
        if (req.label === "angle-A") {
          controller.abort()
          return { candidates: [candidate("src/a.ts", 1, "bug")] }
        }
        return { candidates: [] }
      },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.partial, true)
  assert.ok(result.warnings.some((w) => w.includes("cancelled")))
})

/* 18 */ test("v2.1.221 groups candidates by location: one verifier, per-candidate verdicts", async () => {
  const { result, calls } = await review({
    version: "cc-workflow-2.1.221",
    level: "high",
    script: {
      finder: (req) => {
        if (req.label === "angle-A") return { candidates: [candidate("src/a.ts", 5, "first claim")] }
        if (req.label === "cleanup") return { candidates: [candidate("src/a.ts", 5, "second claim")] }
        return { candidates: [] }
      },
      verifier: () => ({
        verdicts: [
          { index: 0, verdict: "REFUTED", evidence: "line 6 guards it" },
          { index: 1, verdict: "CONFIRMED", evidence: "line 5 is wrong" },
        ],
      }),
    },
  })
  assert.equal(calls.filter((c) => c.role === "verifier").length, 1)
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].summary, "second claim")
})

/* 19 */ test("v2.1.221 index synthesis merges same-root-cause findings", async () => {
  const { result } = await review({
    version: "cc-workflow-2.1.221",
    level: "high",
    script: {
      finder: (req) =>
        req.label === "angle-A"
          ? { candidates: [candidate("src/a.ts", 1, "bug one"), candidate("src/a.ts", 2, "bug two"), candidate("src/a.ts", 3, "bug three")] }
          : { candidates: [] },
      verifier: () => ({
        verdicts: [0, 1, 2].map((index) => ({ index, verdict: "CONFIRMED", evidence: "line is wrong" })),
      }),
      synthesize: () => ({ summary: "merged", decisions: [{ index: 0, merge: [1] }, { index: 2 }] }),
    },
  })
  assert.equal(result.findings.length, 2)
  assert.match(result.findings[0].summary, /same root cause also at: src\/a\.ts:2/)
})

/* 20 */ test("v2.1.221 backfills verified findings the synthesizer omitted", async () => {
  const { result } = await review({
    version: "cc-workflow-2.1.221",
    level: "high",
    script: {
      finder: (req) =>
        req.label === "angle-A"
          ? { candidates: [candidate("src/a.ts", 1, "one"), candidate("src/a.ts", 2, "two"), candidate("src/a.ts", 3, "three")] }
          : { candidates: [] },
      verifier: () => ({
        verdicts: [0, 1, 2].map((index) => ({ index, verdict: "CONFIRMED", evidence: "line is wrong" })),
      }),
      synthesize: () => ({ summary: "partial", decisions: [{ index: 0 }] }),
    },
  })
  assert.equal(result.findings.length, 3)
  assert.match(result.summary, /2 additional verified findings appended unmerged/)
})

/* 21 */ test("v2.1.162 verifies as finders complete (no barrier)", async () => {
  const { calls } = await review({
    version: "cc-workflow-2.1.162",
    level: "high",
    script: {
      delay: (req) => (req.role === "finder" && req.label === "angle-B" ? 120 : 0),
      finder: (req) =>
        req.label === "angle-A"
          ? { candidates: [candidate("src/a.ts", 1, "a bug")] }
          : req.label === "angle-B"
            ? { candidates: [candidate("src/b.ts", 2, "b bug")] }
            : { candidates: [] },
      verifier: () => CONFIRMED(),
      synthesize: () => ({ summary: "ok", findings: [] }),
    },
  })
  const verifyA = calls.find((c) => c.role === "verifier" && c.prompt.includes("a bug"))
  const finderB = calls.find((c) => c.role === "finder" && c.label === "angle-B")
  assert.ok(verifyA && finderB)
  assert.ok(verifyA.at < finderB.at + 120, "verification of angle-A should start before angle-B finishes")
})

/* 22 */ test("v2.1.318 waits at a barrier before verifying", async () => {
  const { calls } = await review({
    version: "cc-2.1.318",
    level: "high",
    script: {
      delay: (req) => (req.role === "finder" && req.label === "angle-B" ? 120 : 0),
      finder: (req) =>
        req.label === "angle-A"
          ? { candidates: [candidate("src/a.ts", 1, "a bug")] }
          : req.label === "angle-B"
            ? { candidates: [candidate("src/b.ts", 2, "b bug")] }
            : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  const verifyA = calls.find((c) => c.role === "verifier" && c.prompt.includes("a bug"))
  const finderB = calls.find((c) => c.role === "finder" && c.label === "angle-B")
  assert.ok(verifyA && finderB)
  assert.ok(verifyA.at >= finderB.at + 110, "verification should not start before every finder returns")
})

/* 23 */ test("a refuted candidate cannot return as a sweep gap", async () => {
  const falsePositive = candidate("src/a.ts", 1, "looks like a bug but the caller guards it")
  const { result, calls } = await review({
    level: "max",
    script: {
      finder: (req) => (req.label === "angle-A" ? { candidates: [falsePositive] } : { candidates: [] }),
      verifier: () => REFUTED(),
      sweep: () => ({ candidates: [falsePositive] }),
    },
  })
  assert.equal(result.findings.length, 0)
  assert.equal(result.refuted.length, 1)
  const sweepPrompt = calls.find((c) => c.role === "sweep")?.prompt ?? ""
  assert.match(sweepPrompt, /refuted — do not re-report without new evidence/)
})

test("a reworded refuted claim stays out of the wf221 sweep", async () => {
  const { result } = await review({
    version: "cc-workflow-2.1.221",
    level: "max",
    script: {
      finder: (req) =>
        req.label === "angle-A"
          ? { candidates: [candidate("src/a.ts", 10, "missing null guard on request input")] }
          : { candidates: [] },
      verifier: () => ({ verdicts: [{ index: 0, verdict: "REFUTED", evidence: "line 12 guards it" }] }),
      sweep: () => ({ candidates: [candidate("src/a.ts", 10, "null guard missing on request input")] }),
    },
  })
  assert.equal(result.findings.length, 0)
  assert.equal(result.refuted.length, 1)
})

test("a reworded file-level refuted claim stays out of the sweep", async () => {
  const falsePositive = { file: "src/a.ts", summary: "validation for the discount percent is missing", failure_scenario: "f" }
  const { result } = await review({
    version: "cc-workflow-2.1.221",
    level: "max",
    script: {
      finder: (req) => (req.label === "angle-A" ? { candidates: [falsePositive] } : { candidates: [] }),
      verifier: () => ({ verdicts: [{ index: 0, verdict: "REFUTED", evidence: "the validator runs first" }] }),
      sweep: () => ({
        candidates: [{ file: "src/a.ts", summary: "the discount percent validation is missing", failure_scenario: "f" }],
      }),
    },
  })
  assert.equal(result.findings.length, 0)
  assert.equal(result.refuted.length, 1)
})

test("a genuine sweep finding at a refuted line survives when only one token is shared", async () => {
  const { result } = await review({
    version: "cc-workflow-2.1.221",
    level: "max",
    script: {
      finder: (req) =>
        req.label === "angle-A"
          ? { candidates: [candidate("src/a.ts", 10, "missing null guard on user input")] }
          : { candidates: [] },
      verifier: () => ({ verdicts: [{ index: 0, verdict: "REFUTED", evidence: "line 12 guards it" }] }),
      sweep: () =>
        ({ candidates: [candidate("src/a.ts", 10, "integer guard uses the wrong bounds")] }),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.match(result.findings[0].summary, /wrong bounds/)
})

/* 24 */ test("wf162 synthesis keeps a no-line finding and its CONFIRMED verdict", async () => {
  const fileLevel = { file: "src/a.ts", summary: "file-level defect", failure_scenario: "f" }
  const { result } = await review({
    version: "cc-workflow-2.1.162",
    level: "high",
    script: {
      finder: (req) => (req.label === "angle-A" ? { candidates: [fileLevel] } : { candidates: [] }),
      verifier: () => CONFIRMED(),
      synthesize: () => ({ summary: "synthesized", findings: [fileLevel] }),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].verdict, "CONFIRMED")
})

/* 25 */ test("the shared gate bounds in-flight agents in the streaming path", async () => {
  const cell = cellOf("cc-workflow-2.1.162", "claude-sonnet-5", "high")
  let active = 0
  let maxActive = 0
  const runner: AgentRunner = async (req) => {
    active++
    maxActive = Math.max(maxActive, active)
    await new Promise((resolve) => setTimeout(resolve, 10))
    active--
    if (req.role === "finder") return { candidates: [candidate(`src/${req.label}.ts`, 1, `${req.label} bug`)] }
    if (req.role === "verifier") return CONFIRMED()
    return { summary: "ok", findings: [] }
  }
  await runReview({
    level: "high",
    cell,
    scope: scopeOf(["src/a.ts"]),
    runner,
    concurrency: 2,
  })
  assert.ok(maxActive <= 2, `in-flight agents exceeded the shared gate: ${maxActive}`)
})

/* 26 */ test("the wf162 streaming path survives a refuted claim, a sweep duplicate, and a no-line synthesis", async () => {
  const cell = cellOf("cc-workflow-2.1.162", "claude-sonnet-5", "max")
  const refutedClaim = candidate("src/a.ts", 10, "looks like a bug but is guarded")
  const realClaim = candidate("src/a.ts", 20, "real defect")
  let active = 0
  let maxActive = 0
  const runner: AgentRunner = async (req) => {
    active++
    maxActive = Math.max(maxActive, active)
    await new Promise((resolve) => setTimeout(resolve, 5))
    active--
    if (req.role === "finder") {
      if (req.label === "angle-A") return { candidates: [refutedClaim] }
      if (req.label === "angle-B") return { candidates: [realClaim] }
      return { candidates: [] }
    }
    if (req.role === "verifier") {
      return req.prompt.includes("looks like a bug")
        ? { verdict: "REFUTED", evidence: "line 11 guards it" }
        : { verdict: "CONFIRMED", evidence: "line 20 is wrong" }
    }
    if (req.role === "sweep") return { candidates: [realClaim] }
    if (req.role === "synthesize") {
      return {
        summary: "one real defect",
        findings: [{ file: "src/a.ts", summary: "real defect", failure_scenario: "input X crashes" }],
      }
    }
    return null
  }
  const result = await runReview({
    level: "max",
    cell,
    scope: scopeOf(["src/a.ts"]),
    runner,
    concurrency: 2,
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].summary, "real defect")
  assert.equal(result.findings[0].verdict, "CONFIRMED")
  assert.equal(result.refuted.length, 1)
  assert.ok(result.stats.dupes >= 1, "the sweep duplicate should be counted")
  assert.ok(maxActive <= 2, `in-flight agents exceeded the shared gate: ${maxActive}`)
})

test("a partially malformed finder list keeps valid candidates and marks the run partial", async () => {
  const { result } = await review({
    script: {
      finder: (req) =>
        req.label === "angle-A"
          ? {
              candidates: [
                candidate("src/a.ts", 1, "real bug"),
                { file: "src/b.ts", summary: "missing failure scenario" },
              ],
            }
          : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.partial, true)
  assert.match(result.warnings.join(" "), /dropped 1 malformed candidate/)
})

test("a verifier verdict without evidence keeps the finding and marks the run partial", async () => {
  const { result } = await review({
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [candidate("src/a.ts", 1, "real bug")] } : { candidates: [] },
      verifier: () => ({ verdict: "CONFIRMED" }),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.partial, true)
  assert.match(result.warnings.join(" "), /without evidence/)
})

test("an absolute path to an unchanged file is not collapsed onto a shorter in-scope name", async () => {
  const { result } = await review({
    files: ["src/a.ts"],
    script: {
      finder: (req) =>
        req.label === "angle-A"
          ? { candidates: [candidate("/repo/lib/src/a.ts", 3, "unchanged file claim")] }
          : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].file, "/repo/lib/src/a.ts")
})

test("a distinct sweep gap survives two shared words with a refuted claim", async () => {
  const refutedClaim = candidate("src/cache.ts", 40, "cache is never invalidated after a write")
  const gap = candidate("src/cache.ts", 40, "write path does not flush the cache to disk")
  const { result } = await review({
    version: "cc-workflow-2.1.221",
    level: "max",
    files: ["src/cache.ts"],
    script: {
      finder: (req) => (req.label === "angle-A" ? { candidates: [refutedClaim] } : { candidates: [] }),
      verifier: () => ({ verdicts: [{ index: 0, verdict: "REFUTED", evidence: "the write path invalidates it" }] }),
      sweep: () => ({ candidates: [gap] }),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].summary, gap.summary)
})

test("a sweep gap with a refuted summary but a different failure survives", async () => {
  const refutedClaim = {
    ...candidate("src/cache.ts", 40, "cache entry is never invalidated after a write"),
    failure_scenario: "reads return stale data after a write",
  }
  const gap = {
    ...candidate("src/cache.ts", 40, "cache entry is never invalidated after a read"),
    failure_scenario: "the write path does not flush the cache to disk",
  }
  const { result } = await review({
    version: "cc-workflow-2.1.221",
    level: "max",
    files: ["src/cache.ts"],
    script: {
      finder: (req) => (req.label === "angle-A" ? { candidates: [refutedClaim] } : { candidates: [] }),
      verifier: () => ({ verdicts: [{ index: 0, verdict: "REFUTED", evidence: "the write path invalidates it" }] }),
      sweep: () => ({ candidates: [gap] }),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].summary, gap.summary)
})

test("a synthesis report that dropped a malformed finding marks the run partial", async () => {
  const real = candidate("src/a.ts", 10, "real defect")
  const { result } = await review({
    version: "cc-workflow-2.1.162",
    script: {
      finder: (req) => (req.label === "angle-A" ? { candidates: [real] } : { candidates: [] }),
      verifier: () => CONFIRMED(),
      synthesize: () => ({
        summary: "synthesized",
        findings: [
          real,
          { file: "src/b.ts", summary: "malformed finding without a scenario" },
        ],
      }),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.partial, true)
  assert.match(result.warnings.join(" "), /dropped 1 malformed finding/)
})

test("--no-semantic-merge disables workflow text synthesis", async () => {
  const { result, calls } = await review({
    version: "cc-workflow-2.1.162",
    semanticMerge: false,
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [candidate("src/a.ts", 10, "real bug")] } : { candidates: [] },
      verifier: () => CONFIRMED(),
      synthesize: () => ({ summary: "should not run", findings: [] }),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.partial, false)
  assert.equal(calls.some((c) => c.role === "synthesize"), false)
})

test("a single-lens cleanup finder keeps its angle slug when the candidate kind is wrong", async () => {
  const { result } = await review({
    script: {
      finder: (req) =>
        req.label === "reuse"
          ? {
              candidates: [
                {
                  ...candidate("src/a.ts", 1, "duplicated formatter"),
                  kind: "correctness",
                },
              ],
            }
          : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].kind, "cleanup")
  assert.equal(result.findings[0].category, "reuse")
})

test("distinct same-line defects with different failure scenarios stay separate", async () => {
  const a = candidate(
    "src/api.ts",
    10,
    "missing null check on response",
    "a null response crashes the parser",
  )
  const b = candidate(
    "src/api.ts",
    10,
    "missing await on response",
    "the promise rejection is unhandled",
  )
  const { result } = await review({
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [a] } : req.label === "angle-B" ? { candidates: [b] } : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 2)
})

test("a merged file-level finding inherits the line anchor of its merge partner", async () => {
  const fileLevel = { file: "src/a.ts", summary: "payload validation is missing", failure_scenario: "bad input reaches the writer" }
  const located = candidate("src/a.ts", 42, "payload validation is missing", "bad input reaches the writer")
  const { result } = await review({
    semanticMerge: true,
    limit: 5,
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [fileLevel] } : req.label === "angle-B" ? { candidates: [located] } : { candidates: [] },
      verifier: () => CONFIRMED(),
      synthesize: (req) =>
        req.label === "dedup"
          ? { summary: "deduped", decisions: [{ index: 0 }, { index: 1 }] }
          : { summary: "merged", decisions: [{ index: 0, merge: [1] }] },
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].line, 42)
  // The inherited anchor is the finding's own location; it must not also be
  // listed as an "also at" location.
  assert.doesNotMatch(result.findings[0].summary, /also at: src\/a\.ts:42/)
})

test("synthesis merging survivors down to the cap is not reported as cap truncation", async () => {
  const a = candidate("src/a.ts", 1, "session token never expires", "a stale token is accepted forever")
  const b = candidate("src/b.ts", 2, "request body is not size-limited", "a huge body exhausts memory")
  const { result } = await review({
    semanticMerge: true,
    limit: 1,
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [a] } : req.label === "angle-B" ? { candidates: [b] } : { candidates: [] },
      verifier: () => CONFIRMED(),
      synthesize: (req) =>
        req.label === "dedup"
          ? { summary: "deduped", decisions: [{ index: 0 }, { index: 1 }] }
          : { summary: "merged", decisions: [{ index: 0, merge: [1] }] },
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.truncatedFrom, undefined)
})

test("a strong same-line paraphrase merges even when the consequences differ", async () => {
  const a = candidate(
    "src/discount.ts",
    10,
    "discount total subtracts percent instead of percent of total",
    "the receipt shows a negative total when percent exceeds 100",
  )
  const b = candidate(
    "src/discount.ts",
    10,
    "discount calculation subtracts percent instead of percentage",
    "the checkout page throws before rendering any line item",
  )
  const { result } = await review({
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [a] } : req.label === "angle-B" ? { candidates: [b] } : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.stats.dupes, 1)
})

test("an unattributed candidate from a mixed grouped finder ranks as cleanup", async () => {
  const bare = { file: "src/a.ts", line: 10, summary: "reuse the existing helper", failure_scenario: "the same logic is duplicated" }
  const { result } = await review({
    finderBudget: 2,
    script: {
      finder: () => ({ candidates: [bare] }),
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].kind, "cleanup")
})

test("a capitalized or invented category on a mixed grouped finder ranks as cleanup", async () => {
  const { result } = await review({
    finderBudget: 2,
    script: {
      finder: () => ({
        candidates: [
          {
            file: "src/a.ts",
            line: 11,
            summary: "reuse the existing helper",
            failure_scenario: "the same logic is duplicated",
            category: "Efficiency",
          },
          {
            file: "src/a.ts",
            line: 12,
            summary: "invented category",
            failure_scenario: "the same logic is duplicated twice",
            category: "model-made-up",
          },
        ],
      }),
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 2)
  assert.ok(result.findings.every((f) => f.kind === "cleanup"))
})

test("file-level dedup does not merge two summaries sharing a 40-character prefix", async () => {
  const prefix = "the request handler does not validate the "
  const a = {
    file: "src/a.ts",
    summary: `${prefix}body before writing it to disk`,
    failure_scenario: "the request body is persisted unvalidated",
  }
  const b = {
    file: "src/a.ts",
    summary: `${prefix}query before using it as a key`,
    failure_scenario: "a crafted query reaches the lookup",
  }
  const { result } = await review({
    version: "cc-workflow-2.1.162",
    files: ["src/a.ts"],
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [a] } : req.label === "angle-B" ? { candidates: [b] } : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 2)
})

test("distinct same-line bugs at exactly 0.5 Jaccard stay separate", async () => {
  const a = candidate("src/api.ts", 10, "missing response check", "a null body crashes the parser")
  const b = candidate("src/api.ts", 10, "missing response await", "the rejection escapes the handler")
  const { result } = await review({
    files: ["src/api.ts"],
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [a] } : req.label === "angle-B" ? { candidates: [b] } : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 2)
})

test("text synthesis canonicalizes a b/-prefixed file path", async () => {
  const { result } = await review({
    version: "cc-workflow-2.1.162",
    files: ["src/a.ts"],
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [candidate("src/a.ts", 10, "missing await on the save path")] } : { candidates: [] },
      verifier: () => CONFIRMED(),
      synthesize: () => ({
        summary: "reworded",
        findings: [candidate("b/src/a.ts", 10, "missing await on the save path")],
      }),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].file, "src/a.ts")
  assert.notEqual(result.partial, true)
})

test("text synthesis does not attach a reworded same-line entry to the wrong finding", async () => {
  const confirmed = candidate("src/cache.ts", 40, "cache is never invalidated after a write")
  const gap = candidate("src/cache.ts", 40, "write path does not flush the cache to disk")
  const { result } = await review({
    version: "cc-workflow-2.1.162",
    level: "max",
    files: ["src/cache.ts"],
    script: {
      finder: (req) => (req.label === "angle-A" ? { candidates: [confirmed] } : { candidates: [] }),
      verifier: () => CONFIRMED(),
      sweep: () => ({ candidates: [gap] }),
      synthesize: () => ({
        summary: "reworded",
        findings: [candidate("src/cache.ts", 40, "the write path fails to flush the cache")],
      }),
    },
  })
  // Two verified findings share the line. The any-token anchor must not claim
  // the first one; the entry is ambiguous, so the run is marked partial.
  assert.equal(result.findings.length, 0)
  assert.equal(result.partial, true)
})

test("text synthesis matches the same summary at the reported line, not the first line", async () => {
  const first = candidate("src/a.ts", 10, "the same defect")
  const second = candidate("src/a.ts", 40, "the same defect")
  const { result } = await review({
    version: "cc-workflow-2.1.162",
    level: "max",
    files: ["src/a.ts"],
    script: {
      finder: (req) => {
        if (req.label === "angle-A") return { candidates: [first] }
        if (req.label === "angle-B") return { candidates: [second] }
        return { candidates: [] }
      },
      verifier: () => CONFIRMED(),
      sweep: () => ({ candidates: [] }),
      synthesize: () => ({
        summary: "line-specific",
        findings: [candidate("src/a.ts", 40, "the same defect")],
      }),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].line, 40)
})

test("a git-quoted diff-header path is canonicalized before verification", async () => {
  const { result } = await review({
    files: ["src/café.ts"],
    script: {
      finder: (req) =>
        req.label === "angle-A"
          ? { candidates: [candidate('"b/src/caf\\303\\251.ts"', 1, "missing guard")] }
          : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings[0].file, "src/café.ts")
})

test("a line-scoped refutation does not suppress a file-level sweep gap", async () => {
  const refuted = candidate("src/a.ts", 10, "missing null check on user name")
  const { result } = await review({
    level: "xhigh",
    script: {
      finder: (req) => (req.label === "angle-A" ? { candidates: [refuted] } : { candidates: [] }),
      verifier: () => REFUTED(),
      sweep: () => ({ candidates: [{ file: "src/a.ts", summary: "missing null check on user name", failure_scenario: "a profile without a name crashes the writer" }] }),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].verdict, "PLAUSIBLE")
  assert.equal(result.findings[0].line, undefined)
})

test("the sweep known list escapes control characters in a file path", async () => {
  const path = "src/a\nb.ts"
  const { calls } = await review({
    level: "max",
    family: "default",
    files: [path],
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [candidate(path, 1, "bad guard")] } : { candidates: [] },
      verifier: () => CONFIRMED(),
      sweep: () => ({ candidates: [] }),
    },
  })
  const prompt = calls.find((c) => c.role === "sweep")?.prompt ?? ""
  assert.match(prompt, /src\/a\\nb\.ts/)
  assert.doesNotMatch(prompt, /src\/a\nb\.ts/)
})

test("pre-verify dedup keeps a correctness representative over a longer cleanup claim", async () => {
  const cleanup = candidate(
    "src/a.ts",
    1,
    "duplicate helper",
    "a much longer cleanup scenario that would win a raw length comparison ".repeat(4),
  )
  const correctness = candidate("src/a.ts", 1, "missing guard", "short scenario")
  const { result } = await review({
    semanticMerge: true,
    script: {
      finder: (req) => {
        if (req.label === "reuse") return { candidates: [cleanup] }
        if (req.label === "angle-A") return { candidates: [correctness] }
        return { candidates: [] }
      },
      verifier: () => CONFIRMED(),
      synthesize: (req) =>
        req.label === "dedup"
          ? { summary: "deduped", decisions: [{ index: 0, merge: [1] }] }
          : { summary: "ranked", decisions: [{ index: 0 }] },
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].kind, "correctness")
  assert.equal(result.findings[0].summary, "missing guard")
})

test("a sweep candidate with no category ranks as cleanup", async () => {
  const { result } = await review({
    level: "max",
    family: "default",
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [candidate("src/b.ts", 2, "real bug")] } : { candidates: [] },
      verifier: () => CONFIRMED(),
      sweep: () => ({ candidates: [candidate("src/a.ts", 1, "unattributed sweep gap")] }),
    },
  })
  assert.equal(result.findings.length, 2)
  assert.equal(result.findings[0].kind, "correctness")
  assert.equal(result.findings[1].kind, "cleanup")
})

test("a quoted POSIX path with a literal backslash is preserved", async () => {
  const path = "src/a\\b.ts"
  const quoted = '"src/a\\\\b.ts"'
  const { result } = await review({
    files: [path],
    script: {
      finder: () => ({ candidates: [candidate(quoted, 1, "bad guard")] }),
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].file, path)
})

test("a truncated text-synthesis report records truncatedFrom", async () => {
  const finding = candidate("src/a.ts", 1, "bad guard")
  const { result } = await review({
    version: "cc-workflow-2.1.162",
    level: "high",
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [finding] } : { candidates: [] },
      verifier: () => CONFIRMED(),
      sweep: () => ({ candidates: [] }),
      synthesize: () => ({ summary: "text report", findings: [finding], truncated: true }),
    },
  })
  assert.equal(result.truncatedFrom, 1)
})

test("a 1-based synthesis plan is shifted before ranking", async () => {
  const a = candidate("src/a.ts", 1, "first bug")
  const b = candidate("src/b.ts", 2, "second bug")
  const { result } = await review({
    semanticMerge: true,
    limit: 1,
    script: {
      finder: (req) => {
        if (req.label === "angle-A") return { candidates: [a] }
        if (req.label === "angle-B") return { candidates: [b] }
        return { candidates: [] }
      },
      verifier: () => CONFIRMED(),
      synthesize: (req) =>
        req.label === "dedup"
          ? { summary: "deduped", decisions: [{ index: 0 }, { index: 1 }] }
          : { summary: "ranked", decisions: [{ index: 1 }, { index: 2 }] },
    },
  })
  assert.equal(result.findings.length, 1)
  assert.equal(result.findings[0].summary, "first bug")
})

test("a capped 1-based synthesis plan is shifted before the cap is applied", async () => {
  const a = candidate("src/a.ts", 1, "first bug")
  const b = candidate("src/b.ts", 2, "second bug")
  const c = candidate("src/c.ts", 3, "third bug")
  const { result } = await review({
    semanticMerge: true,
    limit: 2,
    script: {
      finder: (req) => {
        if (req.label === "angle-A") return { candidates: [a] }
        if (req.label === "angle-B") return { candidates: [b] }
        if (req.label === "angle-C") return { candidates: [c] }
        return { candidates: [] }
      },
      verifier: () => CONFIRMED(),
      synthesize: (req) =>
        req.label === "dedup"
          ? { summary: "deduped", decisions: [{ index: 0 }, { index: 1 }, { index: 2 }] }
          : { summary: "ranked", decisions: [{ index: 1 }, { index: 2 }] },
    },
  })
  assert.equal(result.findings.length, 2)
  assert.deepEqual(result.findings.map((f) => f.summary), ["first bug", "second bug"])
})

test("an exhausted v2.1.162 verifier budget marks the run partial", async () => {
  const { result } = await review({
    version: "cc-workflow-2.1.162",
    level: "high",
    script: {
      finder: (req) =>
        req.label.startsWith("angle") || req.label === "reuse" || req.label === "simplification" ||
        req.label === "efficiency" || req.label === "conventions"
          ? {
              candidates: Array.from({ length: 5 }, (_, i) =>
                candidate("src/a.ts", i + 1, `${req.label} bug ${i}`),
              ),
            }
          : { candidates: [] },
      verifier: () => CONFIRMED(),
    },
  })
  assert.equal(result.stats.budgetDropped > 0, true)
  assert.equal(result.partial, true)
  assert.match(result.warnings.join(" "), /verifier budget/)
})

test("an invented sweep category cannot claim correctness priority", async () => {
  const { result } = await review({
    level: "max",
    family: "default",
    script: {
      finder: (req) =>
        req.label === "angle-A" ? { candidates: [candidate("src/b.ts", 2, "real bug")] } : { candidates: [] },
      verifier: () => CONFIRMED(),
      sweep: () => ({
        candidates: [{ ...candidate("src/a.ts", 1, "invented cleanup"), category: "invented-slug" }],
      }),
    },
  })
  assert.equal(result.findings.length, 2)
  assert.equal(result.findings[0].kind, "correctness")
  assert.equal(result.findings[1].kind, "cleanup")
})
