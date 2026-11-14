import { test } from "node:test"
import assert from "node:assert/strict"
import {
  asCandidatesResult,
  asDecisions,
  asGroupVerdicts,
  asReport,
  asVerdict,
  extractJson,
  isSchemaEcho,
  normalizeCandidatesCall,
  normalizeDecisionsCall,
  normalizeGroupVerdictsCall,
  normalizeReportCall,
  normalizeVerdictCall,
} from "../.opencode/plugins/code-review-opencode/json.ts"
import { schemaExample } from "../.opencode/plugins/code-review-opencode/schemas.ts"

test("every generated schema example is detected as an echo", () => {
  for (const name of ["candidates", "verdict", "groupVerdicts", "report", "decisions"]) {
    const example = JSON.parse(schemaExample(name)) as unknown
    assert.equal(isSchemaEcho(example), true, name)
  }
})

test("a filled-in example that kept the sentinel is a real result", () => {
  const filled = {
    __example: true,
    candidates: [
      {
        file: "src/real.ts",
        line: 7,
        summary: "the guard is inverted",
        failure_scenario: "a negative input reaches the branch and throws",
      },
    ],
  }
  assert.equal(isSchemaEcho(filled), false)
  // Two distinctive placeholders are still an echo even without the sentinel.
  assert.equal(
    isSchemaEcho({
      candidates: [
        {
          file: "path/to/file.ts",
          summary: "one sentence",
          failure_scenario: "a real scenario",
        },
      ],
    }),
    true,
  )
})

test("real grouped verdicts are not mistaken for an example echo", () => {
  assert.equal(
    isSchemaEcho({
      verdicts: [
        { index: 0, verdict: "CONFIRMED", evidence: "line 4 guards the call" },
        { index: 1, verdict: "CONFIRMED", evidence: "line 9 guards the call" },
      ],
    }),
    false,
  )
})

test("extractJson prefers a JSON fence over an earlier code fence", () => {
  const text =
    'the guard is here:\n```ts\nconst re = /[a-z/\n```\n```json\n[{"file":"a.ts"}]\n```'
  assert.deepEqual(extractJson(text), [{ file: "a.ts" }])
})

test("extractJson preserves valid escaped backslashes in prose output", () => {
  const text =
    'Here is the result:\n{"candidates":[{"file":"a.ts","summary":"Windows path C:\\\\data is rejected","failure_scenario":"f"}]}'
  const parsed = extractJson(text) as { candidates: Array<{ summary: string }> }
  assert.match(parsed.candidates[0].summary, /C:\\data/)
})

test("normalizeCandidatesCall rejects a list with any malformed candidate", () => {
  const r = normalizeCandidatesCall({
    candidates: [
      { file: "a.ts", summary: "missing scenario" },
      { file: "a.ts", summary: "valid", failure_scenario: "f", line: 3 },
    ],
  })
  // Keeping only the valid entries hides the lost candidate from the engine;
  // reject so the child is told to re-emit the complete list.
  assert.equal(r.ok, false)
  if (!r.ok) assert.match(r.error, /candidates\[0\] dropped/)
  const valid = normalizeCandidatesCall({
    candidates: [{ file: "a.ts", summary: "valid", failure_scenario: "f", line: "3" }],
  })
  assert.equal(valid.ok, true)
  if (valid.ok) assert.equal(valid.value.candidates[0].line, 3)
  assert.equal(normalizeCandidatesCall({ candidates: [{ file: "a.ts" }] }).ok, false)
})

test("extractJson rejects a whole-body schema echo with no real payload", () => {
  const text =
    '{"candidates":[{"file":"path/to/file.ts","line":1,"summary":"one sentence","failure_scenario":"concrete input/state -> wrong output"}]}'
  assert.equal(extractJson(text), null)
  const withReal =
    text +
    "\n```json\n{\"candidates\":[{\"file\":\"src/a.ts\",\"summary\":\"real\",\"failure_scenario\":\"f\"}]}\n```"
  const parsed = extractJson(withReal) as { candidates: Array<{ file: string }> }
  assert.equal(parsed.candidates[0].file, "src/a.ts")
})

test("extractJson keeps a real finding that happens to use the sample file", () => {
  const text =
    '{"candidates":[{"file":"path/to/file.ts","summary":"real bug in the reviewer","failure_scenario":"the parser drops it"}]}'
  const parsed = extractJson(text) as { candidates: Array<{ summary: string }> }
  assert.equal(parsed.candidates[0].summary, "real bug in the reviewer")
})

test("extractJson ignores an unlabeled decisions schema echo", () => {
  const text =
    '{"summary":"real","decisions":[{"index":0},{"index":1}]}\n' +
    '{"summary":"one sentence","decisions":[{"index":0,"merge":[1]}]}'
  const parsed = extractJson(text) as { summary: string; decisions: unknown[] }
  assert.equal(parsed.summary, "real")
  assert.equal(parsed.decisions.length, 2)
})

test("extractJson ignores an unlabeled grouped-verdict schema echo", () => {
  const text =
    '{"verdicts":[{"index":0,"verdict":"REFUTED","evidence":"real"}]}\n' +
    '{"verdicts":[{"index":0,"verdict":"CONFIRMED","evidence":"line 12: ..."}]}'
  const parsed = extractJson(text) as { verdicts: Array<{ verdict: string }> }
  assert.equal(parsed.verdicts[0].verdict, "REFUTED")
})

test("extractJson prefers a real bare array over an echoed schema object", () => {
  const text =
    'Expected shape: {"candidates":[{"file":"path/to/file.ts","summary":"one sentence","failure_scenario":"concrete input/state -> wrong output"}]}\n' +
    '```json\n[{"file":"src/a.ts","summary":"real","failure_scenario":"f"}]\n```'
  const parsed = extractJson(text) as Array<{ file: string }>
  assert.equal(parsed[0].file, "src/a.ts")
})

test("asDecisions raises the cap and reports truncation", () => {
  const many = Array.from({ length: 300 }, (_, i) => ({ index: i }))
  const r = normalizeDecisionsCall({ summary: "s", decisions: many })
  assert.equal(r.ok, true)
  if (r.ok) {
    assert.equal(r.value.decisions.length, 256)
    assert.equal(r.value.truncated, true)
  }
  const seventy = Array.from({ length: 70 }, (_, i) => ({ index: i }))
  const fit = normalizeDecisionsCall({ summary: "s", decisions: seventy })
  assert.equal(fit.ok, true)
  if (fit.ok) {
    assert.equal(fit.value.decisions.length, 70)
    assert.equal(fit.value.truncated, undefined)
  }
})

test("a tolerated malformed decision does not reject the valid plan", () => {
  const r = normalizeDecisionsCall(
    { summary: "s", decisions: [{ index: 0 }, { index: 1, merge: "2" }] },
    undefined,
    { tolerateDropped: true },
  )
  assert.equal(r.ok, true)
  if (r.ok) assert.deepEqual(r.value.decisions, [{ index: 0, merge: [] }])
})

test("extractJson skips prose bracket fragments and returns the structured result", () => {
  const text =
    'Candidates [0] and [1] were refuted. {"candidates":[{"file":"a.ts","summary":"s","failure_scenario":"f"}]}'
  const parsed = extractJson(text) as { candidates: Array<{ file: string }> }
  assert.equal(parsed.candidates[0].file, "a.ts")
})

test("extractJson finds a payload after a long code quote with an unmatched bracket", () => {
  const quote = `Here is the hunk:\n\`\`\`ts\n${"const rows = [\n".repeat(1200)}`
  const text = `${quote}\`\`\`\n{"candidates":[{"file":"src/a.ts","summary":"s","failure_scenario":"f"}]}`
  const parsed = extractJson(text) as { candidates: Array<{ file: string }> }
  assert.equal(parsed.candidates[0].file, "src/a.ts")
})

test("extractJson finds a bare array after an unmatched prose bracket", () => {
  const text =
    'the check `items[0` is wrong\n[{"file":"src/a.ts","summary":"s","failure_scenario":"f"}]'
  const parsed = extractJson(text) as Array<{ file: string }>
  assert.equal(parsed[0].file, "src/a.ts")
})

test("normalizeGroupVerdictsCall requires evidence, keeps valid verdicts, drops duplicates", () => {
  const r = normalizeGroupVerdictsCall({
    verdicts: [
      { index: 0, verdict: "confirmed", evidence: "line 1" },
      { index: 0, verdict: "REFUTED", evidence: "duplicate index" },
      { index: 1, verdict: "MAYBE", evidence: "bad verdict" },
      { index: 2, verdict: "plausible" },
    ],
  })
  // A missing-evidence verdict must be re-emitted, not promoted to CONFIRMED.
  assert.equal(r.ok, false)
  if (!r.ok) assert.match(r.error, /evidence is required/)
  // The tool boundary rejects a payload with any invalid entry so the
  // verifier can correct it instead of silently losing that candidate.
  const withoutMissing = normalizeGroupVerdictsCall({
    verdicts: [
      { index: 0, verdict: "confirmed", evidence: "line 1" },
      { index: 0, verdict: "REFUTED", evidence: "duplicate index" },
      { index: 1, verdict: "MAYBE", evidence: "bad verdict" },
      { index: 2, verdict: "plausible", evidence: "line 3" },
    ],
  })
  assert.equal(withoutMissing.ok, false)
  if (!withoutMissing.ok) {
    assert.match(withoutMissing.error, /duplicate index/)
    assert.match(withoutMissing.error, /verdict is invalid/)
  }
  // The text fallback cannot re-prompt, so it keeps the valid verdicts.
  const tolerant = asGroupVerdicts(
    {
      verdicts: [
        { index: 0, verdict: "confirmed", evidence: "line 1" },
        { index: 1, verdict: "MAYBE", evidence: "bad verdict" },
        { index: 2, verdict: "plausible", evidence: "line 3" },
      ],
    },
    3,
  )
  assert.equal(tolerant?.length, 2)
  assert.equal(tolerant?.[0].verdict, "CONFIRMED")
  assert.equal(tolerant?.[1].verdict, "PLAUSIBLE")
})

test("normalizeGroupVerdictsCall accepts a stringified index", () => {
  const r = normalizeGroupVerdictsCall({ verdicts: [{ index: "0", verdict: "confirmed", evidence: "line 2" }] })
  assert.equal(r.ok, true)
  if (r.ok) assert.equal(r.value.verdicts[0].index, 0)
})

test("normalizeGroupVerdictsCall rejects an offset list at the tool boundary", () => {
  const r = normalizeGroupVerdictsCall({
    verdicts: [
      { index: 1, verdict: "CONFIRMED", evidence: "e1" },
      { index: 2, verdict: "REFUTED", evidence: "e2" },
    ],
  })
  assert.equal(r.ok, false)
  if (!r.ok) assert.match(r.error, /zero-based/)
})

test("the tolerant group-verdict validator still rejects an offset list", () => {
  // The runner uses tolerateDropped for text fallback; that must not also
  // accept a 1-based list the engine will then discard as offset.
  const r = normalizeGroupVerdictsCall(
    {
      verdicts: [
        { index: 1, verdict: "CONFIRMED", evidence: "e1" },
        { index: 2, verdict: "REFUTED", evidence: "e2" },
      ],
    },
    64,
    { tolerateDropped: true },
  )
  assert.equal(r.ok, false)
  if (!r.ok) assert.match(r.error, /zero-based/)
})

test("normalizeVerdictCall requires evidence and accepts lowercase", () => {
  const r = normalizeVerdictCall({ verdict: "confirmed", evidence: "line 1" })
  assert.equal(r.ok, true)
  if (r.ok) {
    assert.equal(r.value.verdict, "CONFIRMED")
    assert.equal(r.value.evidence, "line 1")
  }
  const missing = normalizeVerdictCall({ verdict: "confirmed" })
  assert.equal(missing.ok, false)
  if (!missing.ok) assert.match(missing.error, /evidence/)
  assert.equal(normalizeVerdictCall({ verdict: "MAYBE", evidence: "x" }).ok, false)
})

test("normalizeReportCall drops invalid findings and defaults a missing summary", () => {
  const r = normalizeReportCall({
    findings: [
      { file: "a.ts", summary: "missing scenario" },
      { file: "a.ts", summary: "valid", failure_scenario: "f" },
    ],
  })
  assert.equal(r.ok, true)
  if (r.ok) {
    assert.equal(r.value.summary, "Synthesis report")
    assert.equal(r.value.findings.length, 1)
    assert.match(r.notes.join(" "), /findings\[0\] dropped/)
  }
  assert.equal(normalizeReportCall({ findings: [{ file: "a.ts" }] }).ok, false)
})

test("normalizeDecisionsCall accepts numeric strings in index and merge", () => {
  const r = normalizeDecisionsCall({
    summary: "ranked",
    decisions: [{ index: "0", merge: ["1", "2"] }],
  })
  assert.equal(r.ok, true)
  if (r.ok) assert.deepEqual(r.value.decisions, [{ index: 0, merge: [1, 2] }])
})

test("normalizeDecisionsCall rejects a malformed merge plan so the child re-emits it", () => {
  const scalar = normalizeDecisionsCall({
    summary: "ranked",
    decisions: [{ index: 0, merge: 1 }],
  })
  assert.equal(scalar.ok, false)
  if (!scalar.ok) assert.match(scalar.error, /merge must be an array/)

  const fractional = normalizeDecisionsCall({
    summary: "ranked",
    decisions: [{ index: 0, merge: [1.5] }],
  })
  assert.equal(fractional.ok, false)
  if (!fractional.ok) assert.match(fractional.error, /non-negative integers/)

  const badIndex = normalizeDecisionsCall({
    summary: "ranked",
    decisions: [{ index: -1 }, { index: 0 }],
  })
  assert.equal(badIndex.ok, false)
})

test("asGroupVerdicts keeps an evidence-free refutation as PLAUSIBLE", () => {
  const verdicts = asGroupVerdicts(
    {
      verdicts: [
        { index: 0, verdict: "CONFIRMED", evidence: "line 1" },
        { index: 1, verdict: "PLAUSIBLE", evidence: "line 2" },
        { index: 2, verdict: "REFUTED" },
      ],
    },
    3,
  )
  assert.deepEqual(verdicts, [
    { index: 0, verdict: "CONFIRMED", evidence: "line 1" },
    { index: 1, verdict: "PLAUSIBLE", evidence: "line 2" },
    { index: 2, verdict: "PLAUSIBLE", evidence: "(no evidence provided)" },
  ])
})

test("asVerdict keeps an evidence-free PLAUSIBLE but never an evidence-free CONFIRMED", () => {
  assert.deepEqual(asVerdict({ verdict: "confirmed", evidence: "line 1" }), {
    verdict: "CONFIRMED",
    evidence: "line 1",
  })
  assert.deepEqual(asVerdict({ verdict: "confirmed", reason: "line 2" }), {
    verdict: "CONFIRMED",
    evidence: "line 2",
  })
  assert.deepEqual(asVerdict({ verdict: "confirmed" }), {
    verdict: "PLAUSIBLE",
    evidence: "(no evidence provided)",
  })
  assert.deepEqual(asVerdict({ verdict: "plausible" }), {
    verdict: "PLAUSIBLE",
    evidence: "(no evidence provided)",
  })
  // The tool boundary stays strict.
  assert.equal(normalizeVerdictCall({ verdict: "confirmed" }).ok, false)
})

test("asCandidatesResult treats an all-invalid list as a failed agent result", () => {
  assert.equal(asCandidatesResult({ candidates: [{ file: "a.ts" }] }, 10), null)
  assert.deepEqual(asCandidatesResult({ candidates: [] }, 10)?.candidates, [])
})

test("asCandidatesResult keeps valid candidates when a text-fallback sibling is malformed", () => {
  const parsed = asCandidatesResult(
    {
      candidates: [
        { file: "a.ts", summary: "missing scenario" },
        { file: "b.ts", summary: "valid", failure_scenario: "f", line: 3 },
      ],
    },
    10,
  )
  assert.deepEqual(parsed?.candidates, [{ file: "b.ts", summary: "valid", failure_scenario: "f", line: 3 }])
  assert.equal(parsed?.dropped, 1)
})

test("a bare findings array after prose brackets is salvaged as the payload", () => {
  const text =
    'Candidates [0] and [1] were refuted.\n[{"file":"a.ts","summary":"s","failure_scenario":"f"}]'
  const parsed = extractJson(text) as Array<{ file: string }>
  assert.equal(Array.isArray(parsed), true)
  assert.equal(parsed[0].file, "a.ts")
})

test("a finding with a verdict inside a bare array is not mistaken for a verdict result", () => {
  const text =
    '[{"file":"a.ts","summary":"s","failure_scenario":"f","verdict":"CONFIRMED"}]'
  const parsed = extractJson(text) as Array<{ file: string }>
  assert.equal(Array.isArray(parsed), true)
  assert.equal(parsed[0].file, "a.ts")
})

test("asReport preserves the dropped count recorded at the tool boundary", () => {
  const report = asReport({
    summary: "s",
    findings: [{ file: "a.ts", summary: "s", failure_scenario: "f" }],
    dropped: 1,
  })
  assert.equal(report?.dropped, 1)
})

test("asReport and asDecisions preserve the tool boundary's truncation flag", () => {
  const report = asReport({
    summary: "s",
    findings: [{ file: "a.ts", summary: "s", failure_scenario: "f" }],
    truncated: true,
  })
  assert.equal(report?.truncated, true)
  const decisions = asDecisions({ summary: "s", decisions: [{ index: 0 }], truncated: true })
  assert.equal(decisions?.truncated, true)
})

test("short_summary truncation never splits a surrogate pair", () => {
  const parsed = asCandidatesResult(
    {
      candidates: [
        {
          file: "a.ts",
          summary: "s",
          failure_scenario: "f",
          short_summary: `${"x".repeat(59)}😀`,
        },
      ],
    },
    10,
  )
  const short = parsed?.candidates[0].short_summary ?? ""
  assert.equal(short.includes("\uFFFD"), false)
  assert.equal(/[\uD800-\uDBFF]$/.test(short), false)
})

test("extractJson prefers the real payload after an echoed schema example", () => {
  const text = [
    "Use this shape:",
    "```json",
    '{"candidates":[{"file":"example.ts","summary":"example","failure_scenario":"example"}]}',
    "```",
    "Here is the result:",
    '{"candidates":[{"file":"real.ts","summary":"real","failure_scenario":"real"}]}',
  ].join("\n")
  const parsed = extractJson(text) as { candidates: Array<{ file: string }> }
  assert.equal(parsed.candidates[0].file, "real.ts")
})

test("extractJson keeps a real payload that precedes an echoed schema example", () => {
  const text = [
    "Here is the result:",
    '{"candidates":[{"file":"real.ts","summary":"real","failure_scenario":"real"}]}',
    "Expected shape:",
    '{"candidates":[{"file":"path/to/file.ts","line":1,"summary":"one sentence","failure_scenario":"concrete input/state -> wrong output"}]}',
  ].join("\n")
  const parsed = extractJson(text) as { candidates: Array<{ file: string }> }
  assert.equal(parsed.candidates[0].file, "real.ts")
})

test("asGroupVerdicts shifts full 1-based lists but keeps ambiguous partial lists as-is", () => {
  const offset = asGroupVerdicts(
    {
      verdicts: [
        { index: 1, verdict: "CONFIRMED", evidence: "e1" },
        { index: 2, verdict: "CONFIRMED", evidence: "e2" },
        { index: 3, verdict: "CONFIRMED", evidence: "e3" },
      ],
    },
    3,
  )
  assert.deepEqual(offset, [
    { index: 0, verdict: "CONFIRMED", evidence: "e1" },
    { index: 1, verdict: "CONFIRMED", evidence: "e2" },
    { index: 2, verdict: "CONFIRMED", evidence: "e3" },
  ])
  const partial = asGroupVerdicts(
    {
      verdicts: [
        { index: 1, verdict: "CONFIRMED", evidence: "e1" },
        { index: 2, verdict: "CONFIRMED", evidence: "e2" },
      ],
    },
    3,
  )
  // A partial list starting at 1 is ambiguous. Keep it as-is: a 1-based
  // partial answer must not be shifted onto the never-examined candidate 0.
  assert.deepEqual(partial, [
    { index: 1, verdict: "CONFIRMED", evidence: "e1" },
    { index: 2, verdict: "CONFIRMED", evidence: "e2" },
  ])
  // If index 0 was submitted and dropped (invalid verdict), the survivors are
  // zero-based and must not shift onto the wrong candidates.
  const droppedZero = asGroupVerdicts(
    {
      verdicts: [
        { index: 0, verdict: "MAYBE", evidence: "e0" },
        { index: 1, verdict: "CONFIRMED", evidence: "e1" },
        { index: 2, verdict: "CONFIRMED", evidence: "e2" },
      ],
    },
    3,
  )
  assert.deepEqual(droppedZero, [
    { index: 1, verdict: "CONFIRMED", evidence: "e1" },
    { index: 2, verdict: "CONFIRMED", evidence: "e2" },
  ])
  // A complete list is still accepted.
  const complete = asGroupVerdicts(
    {
      verdicts: [
        { index: 0, verdict: "CONFIRMED", evidence: "e0" },
        { index: 1, verdict: "REFUTED", evidence: "e1" },
      ],
    },
    2,
  )
  assert.equal(complete?.length, 2)
})

test("a malformed candidate beyond the cap does not reject the whole list", () => {
  const r = normalizeCandidatesCall(
    {
      candidates: [
        { file: "a.ts", summary: "a", failure_scenario: "f" },
        { file: "b.ts", summary: "b", failure_scenario: "f" },
        { file: "c.ts" },
      ],
    },
    2,
  )
  assert.equal(r.ok, true)
  if (r.ok) assert.deepEqual(r.value.candidates.map((c) => c.file), ["a.ts", "b.ts"])
})

test("an invalid \\u escape is repaired without dropping the rest of the text", () => {
  const text =
    '{"candidates":[{"file":"a.ts","summary":"C:\\users\\foo","failure_scenario":"f"}]}'
  const parsed = extractJson(text) as { candidates: Array<{ summary: string }> }
  assert.match(parsed.candidates[0].summary, /C:users/)
})

test("category truncation counts code points and does not leave a lone surrogate", () => {
  // JSON Schema maxLength counts code points, so 39 ASCII characters plus one
  // emoji is within the 40-character cap and must not be cut.
  const category = "a".repeat(39) + "🔥"
  const r = normalizeCandidatesCall({
    candidates: [{ file: "a.ts", summary: "s", failure_scenario: "f", category }],
  })
  assert.equal(r.ok, true)
  if (r.ok) {
    const out = r.value.candidates[0].category ?? ""
    assert.equal(out, category)
    assert.doesNotMatch(out, /[\uD800-\uDBFF]$/)
  }
})

test("a labeled paraphrased schema example after the real payload is skipped", () => {
  const text = [
    '{"candidates":[{"file":"src/a.ts","summary":"real bug","failure_scenario":"crash"}]}',
    'Expected shape: {"candidates":[{"file":"example.ts","summary":"example","failure_scenario":"example"}]}',
  ].join("\n")
  const parsed = extractJson(text) as { candidates: Array<{ file: string }> }
  assert.equal(parsed.candidates[0].file, "src/a.ts")
})

test("a report beyond the normalizer cap carries the truncation flag", () => {
  const findings = Array.from({ length: 65 }, (_, i) => ({
    file: `src/f${i}.ts`,
    line: i + 1,
    summary: `bug ${i}`,
    failure_scenario: "the call throws",
  }))
  const report = asReport({ summary: "large", findings })
  assert.equal(report?.findings.length, 64)
  assert.equal(report?.truncated, true)
})
