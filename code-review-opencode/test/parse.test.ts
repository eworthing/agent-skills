import { test } from "node:test"
import assert from "node:assert/strict"
import {
  asVersion,
  detectFamily,
  finderCount,
  plannedFinderCount,
  resolveCell,
  coerceLevel,
  normalizeLevel,
} from "../.opencode/plugins/code-review-opencode/cells.ts"
import {
  fixAction,
  parseArgs,
  parseExtensions,
  parseRoleVariants,
  parseStructured,
  resolveConcurrency,
  resolveEffort,
  resolveMaxFindings,
  promptLimit,
  storedMaxFindings,
} from "../.opencode/plugins/code-review-opencode/parse.ts"

test("reference argument grammar: level first, target after", () => {
  const p = parseArgs("high src/auth.ts")
  assert.equal(p.explicit, "high")
  assert.equal(p.target, "src/auth.ts")
  assert.equal(p.fix, false)
})

test("med is the only level alias", () => {
  assert.equal(parseArgs("med").explicit, "medium")
  assert.equal(parseArgs("extra-high").explicit, undefined)
  assert.equal(parseArgs("extra-high").target, "extra-high")
})

test("flags are stripped and combined", () => {
  const p = parseArgs("--comment high --fix 123")
  assert.equal(p.explicit, "high")
  assert.equal(p.target, "123")
  assert.equal(p.comment, true)
  assert.equal(p.fix, true)
})

test("a level-looking typo is reported and consumed, not left in the target", () => {
  const p = parseArgs("highh src/a.ts")
  assert.equal(p.explicit, undefined)
  assert.equal(p.unrecognizedLevel, "highh")
  assert.equal(p.target, "src/a.ts")
})

test("ultra is a fallback marker", () => {
  const p = parseArgs("ultra 42")
  assert.equal(p.ultraFallback, true)
  assert.equal(p.target, "42")
})

test("backticks and a leading # are stripped from the target's first token", () => {
  assert.equal(parseArgs("high `#123`").target, "123")
})

test("--max-findings: number, all, default, invalid, bare", () => {
  assert.equal(parseArgs("high --max-findings 12").maxFindings, 12)
  assert.equal(parseArgs("high --max-findings=12").maxFindings, 12)
  assert.equal(parseArgs("high --max-findings all").maxFindings, "all")
  assert.equal(parseArgs("high --max-findings default").maxFindings, "default")
  assert.equal(parseArgs("high --max-findings 0").maxFindingsIgnored, true)
  assert.equal(parseArgs("high --max-findings").maxFindingsIgnored, true)
  // last occurrence wins
  assert.equal(parseArgs("high --max-findings 5 --max-findings 7").maxFindings, 7)
  // A flag-shaped word inside a free-form target is target text, not an option.
  const embedded = parseArgs(parseExtensions("high fix the --max-findings parser bug").rest)
  assert.equal(embedded.maxFindings, undefined)
  assert.equal(embedded.maxFindingsIgnored, false)
  assert.equal(embedded.target, "fix the --max-findings parser bug")
})

test("--fix never applies during a dry run or with --json", () => {
  assert.equal(fixAction(false, false, false), "none")
  assert.equal(fixAction(true, true, false), "dry-run")
  assert.equal(fixAction(true, false, true), "json")
  assert.equal(fixAction(true, false, false), "apply")
})

test("invalid concurrency collapses to the default instead of NaN", () => {
  assert.equal(resolveConcurrency(undefined, "four"), 4)
  assert.equal(resolveConcurrency(undefined, "8x"), 4)
  assert.equal(resolveConcurrency(Number.NaN, undefined), 4)
  assert.equal(resolveConcurrency(0, undefined), 4)
  assert.equal(resolveConcurrency(4, undefined), 4)
  assert.equal(resolveConcurrency(undefined, "3"), 3)
})

test("prototype keys are not valid modes or families", () => {
  assert.equal(asVersion("constructor"), "cc-2.1.318")
  assert.equal(asVersion("toString"), "cc-2.1.318")
  assert.equal(asVersion("cc-workflow-2.1.221"), "cc-workflow-2.1.221")
  assert.equal(detectFamily(undefined, "constructor"), "default")
  assert.deepEqual(
    resolveCell("cc-2.1.318", "constructor", "high"),
    resolveCell("cc-2.1.318", "default", "high"),
  )
})

test("there is no wall-clock timeout flag; steps is the bound", () => {
  const { rest, flags } = parseExtensions("max --timeout 60")
  assert.equal(rest, "max --timeout 60")
  assert.equal("timeoutMs" in flags, false)
})

test("extension flags never reach the reference parser", () => {
  const { rest, flags } = parseExtensions("high src/a.ts --json --mode cc-workflow-2.1.221 --concurrency 3")
  assert.equal(rest, "high src/a.ts")
  assert.equal(flags.json, true)
  assert.equal(flags.mode, "cc-workflow-2.1.221")
  assert.equal(flags.concurrency, 3)
})

test("attached boolean values are recognized instead of becoming the target", () => {
  const enabled = parseExtensions("--json=true src/a.ts")
  assert.equal(enabled.flags.json, true)
  assert.equal(enabled.rest, "src/a.ts")
  const disabled = parseExtensions("--json=false src/a.ts")
  assert.equal(disabled.flags.json, false)
  assert.equal(disabled.rest, "src/a.ts")
})

test("bare --keep-sessions is boolean and does not consume the target", () => {
  const bare = parseExtensions("high --keep-sessions src/auth.ts")
  assert.equal(bare.rest, "high src/auth.ts")
  assert.equal(bare.flags.keepSessions, true)
  const explicit = parseExtensions("high --keep-sessions=false src/auth.ts")
  assert.equal(explicit.rest, "high src/auth.ts")
  assert.equal(explicit.flags.keepSessions, false)
})

test("--no-post wins when it comes after --post, and vice versa", () => {
  assert.equal(parseArgs("--post --no-post 123").post, false)
  assert.equal(parseArgs("--no-post --post 123").post, true)
  assert.equal(parseArgs("--no-post 123").post, false)
})

test("effort precedence: explicit > last used > session > medium", () => {
  assert.equal(resolveEffort(parseArgs("low"), "high", "xhigh"), "low")
  assert.equal(resolveEffort(parseArgs(""), "high", "xhigh"), "high")
  assert.equal(resolveEffort(parseArgs(""), undefined, "xhigh"), "xhigh")
  assert.equal(resolveEffort(parseArgs(""), undefined, undefined), "medium")
  // A provider-specific session variant is not an effort level: fall through
  // to medium rather than coercing an unknown string to high.
  assert.equal(resolveEffort(parseArgs(""), undefined, "thinking"), "medium")
  assert.equal(resolveEffort(parseArgs("ultra"), "low", "low"), "max")
})

test("invalid stored effort collapses to high, not medium", () => {
  assert.equal(coerceLevel("bogus"), "high")
  assert.equal(coerceLevel(undefined), "medium")
  assert.equal(normalizeLevel("XHIGH"), "xhigh")
})

test("model-family cell table matches the v2.1.318 dispatch table", () => {
  assert.equal(detectFamily("anthropic/claude-sonnet-5-5"), "claude-sonnet-5")
  assert.equal(detectFamily("anthropic/claude-opus-5"), "claude-opus-5")
  assert.equal(detectFamily("anthropic/claude-opus-4-8"), "claude-opus-4-8")
  assert.equal(detectFamily("openai/gpt-6.1"), "default")

  assert.equal(resolveCell("cc-2.1.318", "default", "medium").id, "o48-high-v1")
  assert.equal(resolveCell("cc-2.1.318", "default", "high").id, "o48-high-v1")
  assert.equal(resolveCell("cc-2.1.318", "default", "xhigh").id, "o48-xhigh-v1")
  assert.equal(resolveCell("cc-2.1.318", "default", "max").id, "max")

  assert.equal(resolveCell("cc-2.1.318", "claude-sonnet-5", "medium").id, "medium")
  assert.equal(resolveCell("cc-2.1.318", "claude-sonnet-5", "high").id, "high")
  assert.equal(resolveCell("cc-2.1.318", "claude-opus-5", "high").id, "o5-bmin")
  assert.equal(resolveCell("cc-2.1.318", "claude-opus-4-8", "medium").id, "o48-med-v1")
})

test("agent counts per version and level", () => {
  assert.equal(finderCount(resolveCell("cc-2.1.318", "claude-sonnet-5", "high")), 8)
  assert.equal(finderCount(resolveCell("cc-2.1.318", "claude-sonnet-5", "xhigh")), 10)
  assert.equal(finderCount(resolveCell("cc-workflow-2.1.162", "default", "high")), 7)
  assert.equal(finderCount(resolveCell("cc-workflow-2.1.162", "default", "xhigh")), 9)
  assert.equal(finderCount(resolveCell("cc-workflow-2.1.221", "default", "high")), 4)
  assert.equal(finderCount(resolveCell("cc-workflow-2.1.221", "default", "xhigh")), 6)
})

test("max-findings: 32 cap applies only when ReportFindings is available", () => {
  const cell = resolveCell("cc-2.1.318", "claude-sonnet-5", "high")
  assert.equal(resolveMaxFindings(parseArgs("high --max-findings 50"), cell, true).stated, 32)
  assert.equal(resolveMaxFindings(parseArgs("high --max-findings 50"), cell, false).stated, 50)
  assert.equal(resolveMaxFindings(parseArgs("high --max-findings all"), cell, true).stated, 32)
  assert.equal(resolveMaxFindings(parseArgs("high --max-findings all"), cell, false).stated, "all")
  assert.equal(promptLimit(cell, undefined), 10)
})

test("low-sonnet5 ignores --max-findings entirely", () => {
  const cell = resolveCell("cc-2.1.318", "claude-sonnet-5", "low")
  const r = resolveMaxFindings(parseArgs("low --max-findings 5"), cell, true)
  assert.equal(r.stated, undefined)
})

test("--max-findings default clears a stored limit instead of reusing it", () => {
  const cell = resolveCell("cc-2.1.318", "default", "max")
  const r = resolveMaxFindings(parseArgs("max --max-findings default"), cell, true, 12)
  assert.equal(r.reused, false)
  assert.equal(r.asked, undefined)
  assert.equal(r.stated, undefined)
})

test("the diff-size finder budget only applies to sonnet-5 high/xhigh/max", () => {
  const def = resolveCell("cc-2.1.318", "default", "max")
  assert.equal(plannedFinderCount(def, 300), 10)
  const sonnet = resolveCell("cc-2.1.318", "claude-sonnet-5", "max")
  assert.equal(plannedFinderCount(sonnet, 300), 2)
  assert.equal(plannedFinderCount(sonnet, 1500), 8)
  // A rename- or binary-only diff has no line churn but still uses the floor.
  assert.equal(plannedFinderCount(sonnet, 0), 2)
})

test("reuse of the last max-findings", () => {
  const cell = resolveCell("cc-2.1.318", "claude-sonnet-5", "high")
  const r = resolveMaxFindings(parseArgs("high"), cell, true, 6)
  assert.equal(r.reused, true)
  assert.equal(r.stated, 6)
})

test("an invalid --max-findings does not clear the stored limit", () => {
  assert.equal(storedMaxFindings(parseArgs("high --max-findings banana")), undefined)
  assert.equal(storedMaxFindings(parseArgs("high --max-findings")), undefined)
  assert.equal(storedMaxFindings(parseArgs("high --max-findings 5")), 5)
  assert.equal(storedMaxFindings(parseArgs("high --max-findings all")), "all")
  assert.equal(storedMaxFindings(parseArgs("high --max-findings default")), null)
  assert.equal(storedMaxFindings(parseArgs("high")), undefined)
})

test("structured tool input is not reinterpreted as a level or flag", () => {
  // The typed tool accepts the same aliases as the CLI.
  assert.equal(parseStructured({ level: "med" }).parsed.explicit, "medium")
  const { parsed, flags } = parseStructured({ target: "high", level: "low", maxFindings: 5, json: true })
  assert.equal(parsed.explicit, "low")
  assert.equal(parsed.target, "high")
  assert.equal(parsed.maxFindings, 5)
  assert.equal(flags.json, true)
  const flagged = parseStructured({ target: "--fix src/a.ts" })
  assert.equal(flagged.parsed.target, "--fix src/a.ts")
  assert.equal(flagged.parsed.fix, false)
  // The tool's target follows the same normal form as the command grammar.
  assert.equal(parseStructured({ target: "#123" }).parsed.target, "123")
  assert.equal(parseStructured({ target: "`src/a.ts`" }).parsed.target, "src/a.ts")
})

test("cells declare their synthesis and cleanup modes", () => {
  const max318 = resolveCell("cc-2.1.318", "default", "max")
  assert.equal(max318.synthesis, "none")
  assert.equal(max318.semanticMerge, true)
  const wf162 = resolveCell("cc-workflow-2.1.162", "default", "max")
  assert.equal(wf162.synthesis, "text")
  assert.equal(wf162.streaming, true)
  assert.equal(wf162.cleanupLenses, "162")
  const wf221 = resolveCell("cc-workflow-2.1.221", "default", "max")
  assert.equal(wf221.synthesis, "index")
})

test("a workflow mode at an unsupported level keeps the model family and says so", () => {
  const medium = resolveCell("cc-workflow-2.1.162", "claude-sonnet-5", "medium")
  assert.equal(medium.id, "medium")
  assert.equal(medium.engine, "multi")
  assert.match(medium.fallbackNotice ?? "", /no medium-effort recipe/)
})

test("repeated extension flags are all stripped from the target", () => {
  const { rest, flags } = parseExtensions("--mode cc-workflow-2.1.221 --mode foo high src/a.ts")
  assert.equal(flags.mode, "cc-workflow-2.1.221")
  assert.equal(rest, "high src/a.ts")
  const bools = parseExtensions("high --json --json --verbose --verbose")
  assert.equal(bools.flags.json, true)
  assert.equal(bools.flags.verbose, true)
  assert.equal(bools.rest, "high")
})

test("an invalid spaced extension value does not consume the next token", () => {
  const { rest, flags } = parseExtensions("--driver high src/auth.ts")
  assert.equal(flags.driver, undefined)
  assert.equal(rest, "high src/auth.ts")
})

test("parseStructured coerces a stringified max-findings value", () => {
  const { parsed } = parseStructured({ maxFindings: "5" as unknown as number })
  assert.equal(parsed.maxFindings, 5)
  assert.equal(parsed.maxFindingsIgnored, false)
})

test("ordinary words that only start like a level are not effort typos", () => {
  assert.equal(parseArgs("maxim src/auth.ts").unrecognizedLevel, undefined)
  assert.equal(parseArgs("maxim src/auth.ts").target, "maxim src/auth.ts")
  assert.equal(parseArgs("highlight the retry loop").unrecognizedLevel, undefined)
  assert.equal(parseArgs("flow control in the scheduler").unrecognizedLevel, undefined)
  assert.equal(parseArgs("slow path in the cache").unrecognizedLevel, undefined)
  assert.equal(parseArgs("map the retry loop").unrecognizedLevel, undefined)
  assert.equal(parseArgs("medum src/auth.ts").unrecognizedLevel, "medum")
  assert.equal(parseArgs("highh src/auth.ts").unrecognizedLevel, "highh")
})

test("role variants parse role and label keys", () => {
  assert.deepEqual(parseRoleVariants("finder=max, verifier=high, reuse=low"), {
    finder: "max",
    verifier: "high",
    reuse: "low",
  })
  assert.deepEqual(parseRoleVariants(undefined), {})
  assert.deepEqual(parseRoleVariants("bad,=x,key="), {})
})

test("repeated --keep-sessions flags are all stripped and the last value wins", () => {
  const { rest, flags } = parseExtensions("--keep-sessions --keep-sessions=false high")
  assert.equal(rest, "high")
  assert.equal(flags.keepSessions, false)
  const reversed = parseExtensions("--keep-sessions=false --keep-sessions high")
  assert.equal(reversed.rest, "high")
  assert.equal(reversed.flags.keepSessions, true)
})

test("flag-shaped words inside a free-form target are not stripped", () => {
  const { rest, flags } = parseExtensions("fix the --json flag")
  assert.equal(rest, "fix the --json flag")
  assert.equal(flags.json, false)
  // A flag after the target is an option only when it ends the command or is
  // followed by another option; a mid-sentence flag belongs to the target.
  const middle = parseExtensions("src/a.ts --json extra")
  assert.equal(middle.rest, "src/a.ts --json extra")
  assert.equal(middle.flags.json, false)
  const trailing = parseExtensions("review src/a.ts --json")
  assert.equal(trailing.rest, "review src/a.ts")
  assert.equal(trailing.flags.json, true)
})

test("extension values after a target are stripped when they end the command", () => {
  const { rest, flags } = parseExtensions("review src/a.ts --concurrency 3")
  assert.equal(rest, "review src/a.ts")
  assert.equal(flags.concurrency, 3)
  const model = parseExtensions("src/a.ts --model opencode-go/deepseek-v4.1-flash#max")
  assert.equal(model.rest, "src/a.ts")
  assert.equal(model.flags.model, "opencode-go/deepseek-v4.1-flash#max")
})

test("an empty attached extension value leaves the slot unset", () => {
  const { flags } = parseExtensions("--mode= --family= --model= high src/a.ts")
  assert.equal(flags.mode, undefined)
  assert.equal(flags.family, undefined)
  assert.equal(flags.model, undefined)
  // The empty assignment must not block a later valid flag.
  const later = parseExtensions("--mode= --mode cc-workflow-2.1.221 high")
  assert.equal(later.flags.mode, "cc-workflow-2.1.221")
})

test("parseStructured coerces a numeric target", () => {
  const { parsed } = parseStructured({ target: 123 as unknown as string })
  assert.equal(parsed.target, "123")
})

test("--keep-sessions values are case-insensitive", () => {
  const { rest, flags } = parseExtensions("high --keep-sessions FALSE src/a.ts")
  assert.equal(rest, "high src/a.ts")
  assert.equal(flags.keepSessions, false)
  const attached = parseExtensions("high --keep-sessions=FALSE src/a.ts")
  assert.equal(attached.rest, "high src/a.ts")
  assert.equal(attached.flags.keepSessions, false)
})

test("reference boolean flags inside a free-form target stay target text", () => {
  const parsed = parseArgs(parseExtensions("high review the --fix parsing in src/args.ts").rest)
  assert.equal(parsed.fix, false)
  assert.equal(parsed.target, "review the --fix parsing in src/args.ts")
  // A trailing reference flag is still an option.
  const trailing = parseArgs(parseExtensions("high src/a.ts --fix").rest)
  assert.equal(trailing.fix, true)
})
