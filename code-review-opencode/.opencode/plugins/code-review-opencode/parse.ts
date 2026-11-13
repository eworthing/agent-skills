/**
 * Argument parsing and effort/limit resolution.
 *
 * The reference parser (`xe`) is reproduced flag-for-flag for the flags Claude
 * Code owns: --comment, --fix, --post, --no-post, --max-findings. The
 * reconstruction adds its own flags (--json, --mode, --driver, ...) which are
 * stripped before the reference parser runs, so a command line valid in Claude
 * Code parses identically here.
 */
import { HARD_FINDINGS_CAP, LEVELS, coerceLevel, normalizeLevel, type Cell, type Level } from "./cells.ts"
import { positiveLine } from "./finding.ts"

export type Parsed = {
  explicit?: Level
  target: string
  comment: boolean
  fix: boolean
  post: boolean
  ultraFallback: boolean
  unrecognizedLevel?: string
  /** "default" is preserved: it explicitly resets the stored limit. */
  maxFindings?: number | "all" | "default"
  maxFindingsIgnored: boolean
}

export type ExtensionFlags = {
  json: boolean
  mode?: string
  driver?: "engine" | "prompt"
  family?: string
  model?: string
  concurrency?: number
  keepSessions?: boolean
  /** Extension: ignore the reference's diff-size finder budget. */
  fullFleet: boolean
  /** Extension: force the semantic merge/rank synthesizer on or off. */
  semanticMerge?: boolean
  quiet: boolean
  verbose: boolean
  dryRun: boolean
}

/** Reference `ot`: strip backticks from the first token, rejoin. */
function cleanTarget(parts: string[]): string {
  const [first = "", ...rest] = parts
  return [first.replaceAll("`", "").replace(/^#/, ""), ...rest].filter(Boolean).join(" ")
}

/** Decide what `--fix` may do for this output mode. A dry run never edits. */
export function fixAction(fix: boolean, dryRun: boolean, json: boolean): "none" | "apply" | "dry-run" | "json" {
  if (!fix) return "none"
  if (dryRun) return "dry-run"
  if (json) return "json"
  return "apply"
}

/**
 * Resolve the child concurrency. `Number("four")` is NaN, and a NaN limit
 * makes `mapLimit` start zero workers — the review then looks clean while
 * every candidate silently vanishes. Collapse anything invalid to the default.
 *
 * The reference launches every finder at once. OpenCode Go publishes no
 * concurrency cap; its limits are dollar-based. Eight concurrent max-effort
 * children saturated the provider in self-review 5 and 6, while four completed
 * cleanly. A six-way run (self-review 10) stalled one finder, so four remains
 * the default: the highest value with a complete run on this workload.
 * `--concurrency 6` is available for smaller diffs or off-peak, and
 * `--concurrency 8` restores the reference fan-out only when the provider is
 * healthy.
 */
export function resolveConcurrency(explicit: number | undefined, env: string | undefined): number {
  return positiveLine(explicit) ?? positiveLine(env) ?? 4
}

const EXTENSION_BOOL = new Set([
  "json",
  "quiet",
  "verbose",
  "full-fleet",
  "semantic-merge",
  "no-semantic-merge",
  "dry-run",
])

const EXTENSION_VALUE = new Set(["mode", "driver", "family", "model", "concurrency"])

const REFERENCE_BOOL = new Set(["comment", "fix", "post", "no-post"])

function isOptionToken(token: string): boolean {
  return token.startsWith("--")
}

function isLevelToken(token: string): boolean {
  return normalizeLevel(token) !== undefined || token.toLowerCase() === "ultra"
}

/** Assign one extension value; false means the token is not an option. */
function assignExtensionValue(
  flags: ExtensionFlags,
  name: string,
  value: string | undefined,
): boolean {
  switch (name) {
    case "mode":
      if (!value) return false
      if (flags.mode === undefined) flags.mode = value
      return true
    case "driver":
      if (value !== "engine" && value !== "prompt") return false
      flags.driver = value
      return true
    case "family":
      if (!value) return false
      if (!flags.family) flags.family = value
      return true
    case "model":
      if (!value) return false
      if (!flags.model) flags.model = value
      return true
    case "concurrency": {
      const n = positiveLine(value)
      if (n === undefined) return false
      flags.concurrency = n
      return true
    }
    default:
      return false
  }
}

export function parseExtensions(input: string): { rest: string; flags: ExtensionFlags } {
  const flags: ExtensionFlags = { json: false, quiet: false, verbose: false, fullFleet: false, dryRun: false }
  const tokens = input.split(/\s+/).filter(Boolean)
  const kept: string[] = []
  let targetStarted = false
  const push = (token: string): void => {
    kept.push(token)
  }

  // Extension flags are recognised before the free-form target, or after it
  // only as a trailing option run. A flag-shaped word inside an instruction
  // ("fix the --json flag") is part of the target, not an option.
  const canStripBoolean = (i: number): boolean =>
    !targetStarted || i === tokens.length - 1 || isOptionToken(tokens[i + 1] ?? "")
  const canStripValue = (i: number, hasValue: boolean): boolean => {
    if (!targetStarted) return true
    if (!hasValue) return i === tokens.length - 1 || isOptionToken(tokens[i + 1] ?? "")
    return i + 1 === tokens.length - 1 || isOptionToken(tokens[i + 2] ?? "")
  }

  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i]
    const eq = token.indexOf("=")
    const attached = token.startsWith("--") && eq > 2
    const name = attached ? token.slice(2, eq) : token.startsWith("--") ? token.slice(2) : ""
    const attachedValue = attached ? token.slice(eq + 1) : undefined

    if (token === "--max-findings" || token.startsWith("--max-findings=")) {
      // Leave reference flags for parseArgs, but keep their value out of the
      // "target started" state.
      push(token)
      if (token === "--max-findings" && i + 1 < tokens.length && !isOptionToken(tokens[i + 1])) {
        push(tokens[++i])
      }
      continue
    }
    if (!attached && REFERENCE_BOOL.has(name)) {
      push(token)
      continue
    }
    if (attached && name === "keep-sessions") {
      if (canStripBoolean(i)) {
        flags.keepSessions = (attachedValue ?? "").toLowerCase() !== "false"
      } else {
        push(token)
      }
      continue
    }
    if (attached && EXTENSION_VALUE.has(name)) {
      if (canStripBoolean(i)) {
        // `--mode=` is an empty assignment, not a value. assignExtensionValue
        // leaves the slot untouched so the env fallback still applies.
        assignExtensionValue(flags, name, attachedValue)
      } else {
        push(token)
      }
      continue
    }
    if (!attached && name === "keep-sessions") {
      const next = tokens[i + 1]
      const explicit = next !== undefined && /^(true|false)$/i.test(next)
      if (explicit && canStripValue(i, true)) {
        flags.keepSessions = (next ?? "").toLowerCase() !== "false"
        i++
      } else if (!explicit && canStripBoolean(i)) {
        flags.keepSessions = true
      } else {
        push(token)
      }
      continue
    }
    if (EXTENSION_BOOL.has(name)) {
      if (canStripBoolean(i)) {
        // `--json=true` and `--json` mean the same thing; `--json=false` is an
        // explicit off. An attached value must never fall through to the
        // target and be passed to the finders as scope guidance.
        const enabled = attached ? (attachedValue ?? "").toLowerCase() !== "false" : true
        if (name === "json") flags.json = enabled
        else if (name === "quiet") flags.quiet = enabled
        else if (name === "verbose") flags.verbose = enabled
        else if (name === "full-fleet") flags.fullFleet = enabled
        else if (name === "semantic-merge") flags.semanticMerge = enabled
        else if (name === "no-semantic-merge") flags.semanticMerge = !enabled
        else if (name === "dry-run") flags.dryRun = enabled
      } else {
        push(token)
      }
      continue
    }
    if (!attached && EXTENSION_VALUE.has(name)) {
      const next = tokens[i + 1]
      const hasValue = next !== undefined && !isOptionToken(next)
      if (canStripValue(i, hasValue)) {
        const value = hasValue ? next : undefined
        // `mode`/`family`/`model` accept any non-empty value; a repeated flag
        // is still consumed (the first value wins) rather than leaking its
        // value into the target. `driver` and `concurrency` have a closed
        // grammar, so an invalid value stays in the command text.
        const accepted = assignExtensionValue(flags, name, value)
        // Consume the value only when it was accepted. An invalid
        // `--driver high` must leave `high` in the command grammar so it can
        // still be read as the effort level instead of silently disappearing.
        // A recognised extension token is deliberately not re-added to the
        // target: it is an option, not prose.
        if (accepted && hasValue) i++
      } else {
        push(token)
      }
      continue
    }
    // A level/ultra token belongs to the command grammar, not the target.
    if (!token.startsWith("--") && isLevelToken(token)) {
      push(token)
      continue
    }
    push(token)
    if (!isOptionToken(token)) targetStarted = true
  }

  return { rest: kept.join(" ").trim(), flags }
}

/** Structured input from the typed `code_review` tool, already parsed. */
export type StructuredInvocation = {
  level?: Level
  target?: string
  mode?: string
  maxFindings?: number | "all"
  json?: boolean
  fix?: boolean
  comment?: boolean
}

/** Normalize a typed `maxFindings` the same way the CLI parser does. */
function structuredMaxFindings(value: unknown): number | "all" | undefined {
  if (typeof value === "string" && value.trim().toLowerCase() === "all") return "all"
  // Reuse the shared positive-integer grammar: models routinely stringify
  // integers ("5"), and the value must stay numeric for the engine caps.
  return positiveLine(value)
}

/**
 * Build the reference-shaped parse result from the typed tool's fields.
 * The tool must not serialize its arguments back into the CLI grammar: a
 * target named `high` would be read as an effort level, and a target containing
 * `--fix` would be peeled off as a flag.
 */
export function parseStructured(input: StructuredInvocation): { parsed: Parsed; flags: ExtensionFlags } {
  // The typed tool's target still carries the command grammar's normal form:
  // `#123` and backticked paths mean the same as they do on the command line.
  // The host may pass a JSON number for a PR target; coerce it here so the
  // tolerant tool boundary cannot throw on `.split`.
  const rawTarget =
    typeof input.target === "string" ? input.target : input.target == null ? "" : String(input.target)
  const target = cleanTarget(rawTarget.split(/\s+/).filter(Boolean))
  const maxFindings = structuredMaxFindings(input.maxFindings)
  // The typed tool accepts the same aliases as the CLI (`med`, padded or
  // mixed-case values). `coerceLevel` alone maps every unrecognized spelling
  // to high, so normalize first.
  const explicit =
    input.level === undefined
      ? undefined
      : (normalizeLevel(String(input.level)) ?? coerceLevel(String(input.level)))
  return {
    parsed: {
      explicit,
      target,
      comment: input.comment === true,
      fix: input.fix === true,
      post: false,
      ultraFallback: false,
      maxFindings,
      maxFindingsIgnored: input.maxFindings !== undefined && maxFindings === undefined,
    },
    flags: {
      json: input.json === true,
      mode: input.mode,
      quiet: false,
      verbose: false,
      fullFleet: false,
      dryRun: false,
    },
  }
}

/** Reference `xe`: the Claude Code argument grammar. */
export function parseArgs(raw: string): Parsed {
  // Pull --max-findings first; the last option occurrence wins. A flag-shaped
  // word inside a free-form target ("fix the --max-findings parser bug") is
  // target text, not an option, so use the same target/trailing-option-run
  // boundary as parseExtensions instead of a regex over the whole string.
  const argv = raw.match(/\S+/g) ?? []
  const removed = new Set<number>()
  const found = new Set<string>()
  let postAt = -1
  let noPostAt = -1
  let rawValue: string | undefined
  let targetStarted = false
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i]
    if (token === "--max-findings" || token.startsWith("--max-findings=")) {
      const attached = token.startsWith("--max-findings=")
      const hasValue = attached || (argv[i + 1] !== undefined && !isOptionToken(argv[i + 1]))
      const end = attached || !hasValue ? i : i + 1
      const trailing =
        end === argv.length - 1 ||
        (argv[end + 1] !== undefined && isOptionToken(argv[end + 1]))
      if (!targetStarted || trailing) {
        removed.add(i)
        if (!attached && hasValue) removed.add(i + 1)
        rawValue = attached
          ? token.slice(token.indexOf("=") + 1).toLowerCase()
          : hasValue
            ? argv[i + 1].toLowerCase()
            : ""
        i = end
        continue
      }
    }
    // Reference booleans follow the same target/trailing-option-run boundary
    // as the extensions: `review the --fix parsing` mentions the flag, while
    // `src/auth.ts --fix` asks for it.
    const name = token.startsWith("--") && !token.includes("=") ? token.slice(2) : ""
    if (REFERENCE_BOOL.has(name)) {
      const trailing = i === argv.length - 1 || isOptionToken(argv[i + 1] ?? "")
      if (!targetStarted || trailing) {
        removed.add(i)
        found.add(name)
        if (name === "post") postAt = i
        if (name === "no-post") noPostAt = i
        continue
      }
    }
    // Command grammar argv before the target (effort, reference booleans)
    // do not start the free-form target.
    if (!targetStarted && (isLevelToken(token) || REFERENCE_BOOL.has(name))) {
      continue
    }
    if (targetStarted || !isOptionToken(token)) targetStarted = true
  }
  const stripped = argv.filter((_, i) => !removed.has(i)).join(" ")

  let maxFindings: number | "all" | "default" | undefined
  if (rawValue !== undefined) {
    if (rawValue === "all" || rawValue === "default") {
      maxFindings = rawValue
    } else {
      maxFindings = positiveLine(rawValue)
    }
  }
  const maxFindingsIgnored = rawValue !== undefined && maxFindings === undefined

  const tokens = stripped.split(/\s+/).filter(Boolean)
  const first = tokens[0] ?? ""
  // Last flag wins: `--post --no-post` means no posting, while
  // `--no-post --post` explicitly asks for it. Positions were recorded during
  // the boundary-aware scan, so a target mention cannot beat a real option.
  const post = postAt > noPostAt
  const common = {
    comment: found.has("comment"),
    fix: found.has("fix"),
    post,
    maxFindings,
    maxFindingsIgnored,
  }

  if (first.toLowerCase() === "ultra") {
    return { ...common, target: cleanTarget(tokens.slice(1)), ultraFallback: true }
  }

  const explicit = normalizeLevel(first)
  if (explicit !== undefined) {
    return { ...common, explicit, target: cleanTarget(tokens.slice(1)), ultraFallback: false }
  }

  // qs: a token that is one typo away from a level ("highh", "medum"). It is
  // consumed as a failed effort token, not forwarded as part of the target:
  // otherwise "hihg src/a.ts" reviews a path named "hihg src/a.ts".
  const typo = looksLikeLevel(first) ? first : undefined
  return {
    ...common,
    target: cleanTarget(typo === undefined ? tokens : tokens.slice(1)),
    ultraFallback: false,
    ...(typo !== undefined ? { unrecognizedLevel: typo } : {}),
  }
}

/** Levenshtein distance, used only for short effort-level tokens. */
function editDistance(a: string, b: string): number {
  let prev = Array.from({ length: b.length + 1 }, (_, i) => i)
  for (let i = 1; i <= a.length; i++) {
    const next = [i]
    for (let j = 1; j <= b.length; j++) {
      next[j] = Math.min(prev[j] + 1, next[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1))
    }
    prev = next
  }
  return prev[b.length]
}

/**
 * Prefix matching flagged ordinary words ("maximum", "highlight",
 * "lowercase") as mistyped effort levels and consumed the first word of a
 * free-form target. A typo must also share a meaningful prefix with the level,
 * or ordinary one-edit words ("flow", "slow", "map") look like effort attempts.
 */
function oneTransposition(a: string, b: string): boolean {
  if (a.length !== b.length) return false
  const diffs: number[] = []
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) diffs.push(i)
  return (
    diffs.length === 2 &&
    a[diffs[0]] === b[diffs[1]] &&
    a[diffs[1]] === b[diffs[0]]
  )
}

function looksLikeLevel(token: string): boolean {
  const lower = token.toLowerCase()
  return LEVELS.some((level) => {
    // `hihg` is a transposition, not a one-character substitution.
    if (oneTransposition(lower, level) && lower[0] === level[0]) return true
    if (editDistance(lower, level) !== 1) return false
    let shared = 0
    while (shared < lower.length && shared < level.length && lower[shared] === level[shared]) shared++
    return shared >= (level.length <= 3 ? level.length : 2)
  })
}

/** Reference `yo`: explicit > last used > session effort > "medium". */
export function resolveEffort(parsed: Parsed, lastUsed?: string, sessionEffort?: string): Level {
  // A session/model variant is not necessarily an effort level ("thinking",
  // "reasoning"). Normalize it before coercing: an unrecognized value must
  // fall through to the documented medium default, not collapse to high.
  const picked = parsed.ultraFallback
    ? "max"
    : (parsed.explicit ??
      normalizeLevel(lastUsed ?? "") ??
      normalizeLevel(sessionEffort ?? ""))
  return coerceLevel(picked)
}

/**
 * `CODE_REVIEW_ROLE_VARIANTS` maps a role or finder label to a model variant:
 * `finder=max,verifier=high,reuse=low`. The variant is applied to the parent
 * model; an agent's own `model` still wins.
 */
export function parseRoleVariants(value: string | undefined): Record<string, string> {
  const out: Record<string, string> = {}
  if (!value) return out
  for (const part of value.split(",")) {
    const eq = part.indexOf("=")
    if (eq <= 0) continue
    const key = part.slice(0, eq).trim()
    const variant = part.slice(eq + 1).trim()
    if (key && variant) out[key] = variant
  }
  return out
}

export type LimitResolution = {
  asked?: number | "all"
  stated?: number | "all"
  reused: boolean
}

/**
 * Reference `fo`: the 32 cap applies whenever the review runs as a fork, not
 * only when the output is the ReportFindings tool. The engine path is the
 * fork equivalent here, so `--json` must not lift the bound.
 */
export function hardLimitApplies(usesEngine: boolean, hasReportFindings: boolean): boolean {
  return usesEngine || hasReportFindings
}

/**
 * Reference `fo`: resolve --max-findings.
 * `stated` is what the prompt receives; `capAtHardLimit` is true on the
 * engine/fork path or when the output is ReportFindings.
 */
export function resolveMaxFindings(
  parsed: Parsed,
  cell: Cell,
  capAtHardLimit: boolean,
  lastUsed?: number | "all",
): LimitResolution {
  const reused =
    parsed.maxFindings === undefined &&
    !cell.suppressMaxFindings &&
    lastUsed !== undefined &&
    (lastUsed === "all" || positiveLine(lastUsed) !== undefined)

  // `--max-findings default` explicitly clears the stored choice; it must not
  // fall back to `lastUsed`.
  const explicit = parsed.maxFindings === "default" ? undefined : parsed.maxFindings
  const asked: number | "all" | undefined = reused ? lastUsed : explicit

  let stated: number | "all" | undefined = asked
  if (cell.suppressMaxFindings) {
    stated = undefined
  } else if (
    capAtHardLimit &&
    (asked === "all" || (typeof asked === "number" && asked > HARD_FINDINGS_CAP))
  ) {
    stated = HARD_FINDINGS_CAP
  }

  return { asked, stated, reused }
}

/** The value a prompt builder should use: stated limit or the cell default. */
export function promptLimit(cell: Cell, stated?: number | "all"): number | "all" {
  return stated ?? cell.maxFindings
}

/**
 * The value to persist for `--max-findings`, or undefined when the argument
 * was absent or invalid. `default` clears the stored choice with null.
 * An invalid value must not wipe the user's previously stored limit.
 */
export function storedMaxFindings(parsed: Parsed): number | "all" | null | undefined {
  if (parsed.maxFindings === undefined) return undefined
  return parsed.maxFindings === "default" ? null : parsed.maxFindings
}


