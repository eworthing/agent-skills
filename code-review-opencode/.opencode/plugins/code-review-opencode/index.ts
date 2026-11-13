/**
 * /code-review-opencode for OpenCode — reconstruction of Claude Code's bundled review
 * system (reference: Claude Code v2.1.318).
 *
 * Registers:
 *   - command `code-review-opencode`  → the real executor (inline prompt or engine run)
 *   - tool    `code_review`  → the same executor, callable by an agent
 *   - tool    `ReportFindings` → schema-compatible adapter for the reference tool
 *
 * Nothing here writes to the working tree, commits, pushes, or posts comments
 * unless the invocation explicitly asks for it.
 */
import { Plugin } from "@opencode/plugin"
import {
  HARD_FINDINGS_CAP,
  asVersion,
  detectFamily,
  plannedFinderCount,
  resolveCell,
  LEVELS,
  type InlineVariant,
  type Level,
  VERSIONS,
} from "./cells.ts"
import { runReview, isInline, type AgentRunner, type EngineResult } from "./engine.ts"
import { formatHuman, formatJson, formatOutcomeSummary, formatReportFindings, formatToolResult } from "./format.ts"
import {
  FIX_LATER,
  GITHUB_COMMENT,
  fixBlock,
  inlineHigh,
  inlineMedium,
  inlineXhigh,
  lowExpandedPrompt,
  lowMinimumPrompt,
  lowPrompt,
  minimalPrompt,
  multiHigh,
  multiMax,
  multiMedium,
  multiXhigh,
  type OutputKind,
} from "./prompts.ts"
import {
  fixAction,
  parseArgs,
  parseExtensions,
  parseRoleVariants,
  parseStructured,
  promptLimit,
  resolveConcurrency,
  resolveEffort,
  resolveMaxFindings,
  storedMaxFindings,
  type StructuredInvocation,
} from "./parse.ts"
import { makeRunner, modelRef, trackActivity } from "./runner.ts"
import {
  hasRuntimeSurface,
  hasSkill,
  sessionRecord,
  supportsChildSessions,
  type SessionRecord,
} from "./host.ts"
import {
  extractPathHint,
  missingExplicitPathTarget,
  prTargetNumber,
  resolveReviewRoot,
  resolveScope,
  type Scope,
} from "./scope.ts"
import { postComments, detectHostDetails, type Host } from "./comment.ts"
import { writeReportArtifact } from "./artifact.ts"
import { REPORT_FINDINGS_SCHEMA, normalizeReportFindings } from "./reportfindings.ts"
import {
  CANDIDATES_SCHEMA,
  DECISIONS_SCHEMA,
  GROUP_VERDICTS_SCHEMA,
  REPORT_SCHEMA,
  SCHEMA_TOOL_NAMES,
  VERDICT_SCHEMA,
} from "./schemas.ts"
import {
  normalizeCandidatesCall,
  normalizeDecisionsCall,
  normalizeGroupVerdictsCall,
  normalizeReportCall,
  normalizeVerdictCall,
  type NormalizedCall,
} from "./json.ts"

const STORAGE_EFFORT = "codeReviewLastEffort"
const STORAGE_MAX = "codeReviewLastMaxFindings"

type AnyCtx = any

type Invocation = {
  sessionID: string
  raw: string
  /** When set, `resolveAndRun` uses these values instead of re-parsing `raw`. */
  structured?: StructuredInvocation
  signal?: AbortSignal
  /** The parent session record, when the caller already read it. */
  session?: SessionRecord
  /**
   * The session's model, already read by the caller. A failed parent-session
   * lookup must not drop a model the caller already had: a child created
   * without a model returns an empty response in OpenCode.
   */
  model?: { providerID: string; id: string; variant?: string }
  /** True only for a user-typed command; non-interactive runs don't persist choices. */
  interactive?: boolean
  progress?: (status: string) => Promise<void> | void
  log?: (message: string) => void
}

type Outcome = {
  text: string
  engine?: EngineResult
  /**
   * The command handler must route this text through the model: an inline or
   * prompt-mode review still has to run, or the engine result carries the fix
   * or /verify instructions. Engine-only reports are already complete.
   */
  needsModel: boolean
  /** The text is the final output (bare --json); display it without a model turn. */
  bare?: boolean
}

function resolveInline(kind: OutputKind, variant: InlineVariant | undefined, max: number | "all"): string {
  switch (variant) {
    case "low":
      return lowPrompt(kind, max)
    case "low-min":
      return lowMinimumPrompt(kind)
    case "low-expanded":
      return lowExpandedPrompt(kind, max)
    case "minimal":
      return minimalPrompt(max, kind)
    case "inline-medium":
      return inlineMedium(kind, max)
    case "inline-high":
      return inlineHigh(kind, max)
    case "inline-xhigh":
      return inlineXhigh(kind, max)
    default:
      return inlineHigh(kind, max)
  }
}

function resolveMulti(kind: OutputKind, level: Level, max: number | "all"): string {
  switch (level) {
    case "medium":
      return multiMedium(kind, max)
    case "high":
      return multiHigh(kind, max)
    case "xhigh":
      return multiXhigh(kind, max)
    case "max":
      return multiMax(kind, max)
    default:
      return multiHigh(kind, max)
  }
}

/** Keep tool-result notes short; the full list stays in metadata. */
function summarizeNotes(notes: string[]): string {
  const head = notes.slice(0, 3)
  const rest = notes.length - head.length
  return `(${head.join("; ")}${rest > 0 ? `; ${rest} more` : ""})`
}

/**
 * Report progress without letting a host callback break the review. The
 * callback can reject (session gone, RPC error) or throw synchronously; both
 * are transient and neither should abort work that can still complete.
 */
async function reportProgress(
  callback: ((status: string) => Promise<void> | void) | undefined,
  status: string,
): Promise<void> {
  if (!callback) return
  try {
    await callback(status)
  } catch {
    /* progress is best-effort */
  }
}

/**
 * Keep a long-lived payload map from growing one entry per session forever.
 * Live review children are protected: their schema result may still be the
 * value the runner is about to read, so FIFO eviction must skip them.
 */
function setCapped<K, V>(
  map: Map<K, V>,
  key: K,
  value: V,
  max: number,
  protect?: ReadonlySet<string>,
): void {
  if (!map.has(key) && map.size >= max) {
    for (const candidate of map.keys()) {
      if (protect?.has(String(candidate))) continue
      map.delete(candidate)
      break
    }
  }
  map.set(key, value)
}

const GITLAB_COMMENT_IGNORED = `
\n## GitLab comments are not supported (--comment)\n\nThe \`--comment\` flag was passed, but GitLab merge requests are out of scope\nfor this port, so no MR note was posted. Print the findings to the terminal\nand tell the user in one short line that \`--comment\` was ignored.\n`

const OTHER_COMMENT_IGNORED = `
\n## Comments are not supported for this remote (--comment)\n\nThe \`--comment\` flag was passed, but the reviewed repository's origin is not\nGitHub or GitLab, so no comments were posted. Print the findings to the terminal\nand tell the user in one short line that \`--comment\` was ignored.\n`

function decorate(
  text: string,
  opts: {
    target?: string
    kind: OutputKind
    fix: boolean
    comment: boolean
    suppressFixLater?: boolean
    host?: Host
  },
): string {
  let out = text
  if (opts.target) out = `Review target: \`${opts.target}\`\n\n${out}`
  // Say why --comment was ignored on every prompt-only path; otherwise an
  // inline cell silently drops it or targets the wrong forge.
  if (opts.comment) {
    out +=
      opts.host === "gitlab"
        ? GITLAB_COMMENT_IGNORED
        : opts.host === "github"
          ? GITHUB_COMMENT
          : OTHER_COMMENT_IGNORED
  }
  if (opts.fix) out += fixBlock(opts.kind)
  if (opts.kind === "reportfindings" && !opts.suppressFixLater) out += FIX_LATER
  return out
}

/** One stderr record for every incomplete --json run. */
function partialRecord(warnings: string[]): string {
  return `CODE_REVIEW_PARTIAL ${JSON.stringify({ partial: true, warnings })}`
}

/** Preserve the bare-array contract while disclosing a capped report. */
function truncatedRecord(truncatedFrom: number): string {
  return `CODE_REVIEW_TRUNCATED ${JSON.stringify({ truncated_from: truncatedFrom })}`
}

/** ei(): the reference's one-line effort notice. */
function effortNotice(
  parsed: ReturnType<typeof parseArgs>,
  lastUsed: string | undefined,
  level: Level,
): string | undefined {
  if (parsed.unrecognizedLevel) {
    return `Ignoring unrecognized effort "${parsed.unrecognizedLevel}"; valid: low, medium, high, xhigh, max. Using ${level}${
      lastUsed === level ? ", the level you typed last time" : ""
    }.`
  }
  if (parsed.explicit === undefined && !parsed.ultraFallback && lastUsed !== undefined) {
    return `No effort level given — reusing ${lastUsed}, the level you typed last time${
      level !== lastUsed ? `; running at ${level} here` : ""
    }.`
  }
  return undefined
}

/** go(): the reference's --max-findings notice. */
function maxFindingsNotice(
  limit: ReturnType<typeof resolveMaxFindings>,
  ignored: boolean,
  speaker: "the user" | "you" = "the user",
): string | undefined {
  const notes: string[] = []
  if (ignored) {
    notes.push(
      `\`--max-findings\` was ignored: type a whole number above zero, \`all\`, or \`default\` after it.${
        limit.reused ? "" : " Using the usual limit."
      }`,
    )
  }
  const capNote = `This review reports at most ${HARD_FINDINGS_CAP} findings, so the limit is ${HARD_FINDINGS_CAP} here.`
  if (limit.asked !== undefined && limit.stated === undefined) {
    notes.push("`--max-findings` does not change this review: low effort here has no maximum.")
  } else if (limit.stated !== limit.asked) {
    const who = speaker === "you" ? "You" : "The user"
    notes.push(limit.reused ? `${who} set \`--max-findings ${limit.asked}\` last time. ${capNote}` : capNote)
  } else if (limit.reused && limit.asked !== undefined) {
    notes.push(
      limit.asked === "all"
        ? `Reporting every finding, as ${speaker} chose last time with \`--max-findings all\`.`
        : `Reporting up to ${limit.asked} ${limit.asked === 1 ? "finding" : "findings"}, the limit ${speaker} set last time with \`--max-findings\`.`,
    )
  }
  return notes.length > 0 ? notes.join(" ") : undefined
}

/** ei(): the ultra fallback branch for a host without the cloud reviewer. */
function ultraNotice(
  parsed: ReturnType<typeof parseArgs>,
  level: Level,
  applying: boolean,
): string | undefined {
  if (!parsed.ultraFallback) return undefined
  // `--fix --dry-run` and `--fix --json` omit the fix block, so the notice
  // must not tell the model fixes are being applied.
  if (parsed.fix && applying) {
    return `(Running a local ${level}-effort review and applying its findings.)`
  }
  return `(ultra (cloud review) isn't available in this environment — see https://code.claude.com/docs/en/ultrareview. Falling back to a local ${level}-effort review.)`
}

/** ei(): the --post branch. The flag only applies to the ultra cloud review. */
function postNotice(parsed: ReturnType<typeof parseArgs>, host: Host): string | undefined {
  if (!parsed.post) return undefined
  const gitlab = host === "gitlab"
  const what = parsed.comment
    ? gitlab
      ? "`--comment` was also ignored: GitLab merge requests are out of scope for this port, so no MR note was posted"
      : "when the target is a GitHub PR, your `--comment` is what posts the findings as inline PR comments"
    : gitlab
      ? "this local review will not post to GitLab; GitLab merge requests are out of scope for this port"
      : "this local review will not post to GitHub; `--comment` is the flag that posts local findings as inline PR comments"
  // This notice is also displayed verbatim for a completed engine report, so
  // it must read as user-facing text, not as an instruction to the model.
  return `(The typed \`--post\` applies only to the \`/code-review-opencode ultra\` cloud review and was ignored — ${what}.)`
}

/**
 * Gs/Ws: the reference appends a /verify suggestion when the command exists,
 * the diff has a runtime surface, and the review is not JSON output. OpenCode
 * has no bundled /verify, so this only fires when the user installed one.
 */
async function hasVerifySkill(ctx: AnyCtx): Promise<boolean> {
  let listed: unknown = []
  try {
    listed = (await ctx.skill?.list?.()) ?? []
  } catch {
    listed = []
  }
  return hasSkill(listed, "verify")
}

async function verifyFollowUp(ctx: AnyCtx, files: string[]): Promise<string> {
  if (!hasRuntimeSurface(files)) return ""
  if (!(await hasVerifySkill(ctx))) return ""
  return VERIFY_FOLLOW_UP
}

const VERIFY_FOLLOW_UP = `

## After the review

After the findings are reported (and applied, when --fix was passed): if \`/verify\` has not run this session and the diff has a runtime surface (not test-only or docs-only per the pre-ship exemptions), invoke \`/verify\` now — this review checks that the diff reads right; \`/verify\` checks that it runs right.
`

/**
 * Inline and prompt-only cells never reach the engine's scope result. The
 * follow-up text already conditions on a runtime surface, so do not pay a
 * full diff-discovery round trip (including `gh pr view`) just to decide
 * whether to append it. Only the /verify skill check is needed here.
 */
async function verifyFollowUpForTarget(ctx: AnyCtx): Promise<string> {
  return (await hasVerifySkill(ctx)) ? VERIFY_FOLLOW_UP : ""
}

async function resolveAndRun(
  ctx: AnyCtx,
  inv: Invocation,
  schemaResults?: Map<string, unknown>,
  schemaFailures?: Map<string, number>,
  reviewChildSessions?: Set<string>,
  /** Stream-event liveness index for child sessions (see trackActivity). */
  activity?: (sessionID: string) => number | undefined,
): Promise<Outcome> {
  const structured = inv.structured ? parseStructured(inv.structured) : undefined
  const raw = structured ? undefined : parseExtensions(inv.raw)
  const parsed = structured ? structured.parsed : parseArgs(raw!.rest)
  const flags = structured ? structured.flags : raw!.flags

  // The command invocation's `prompt` carries text/files/agents/skills, not
  // the selected model or effort variant (OpenCode V2 CommandInvocation).
  // Read the parent session once here so the command path chooses the same
  // family/effort cell as the tool path. Callers that already read it pass
  // `inv.session`; otherwise this is the single lookup used for the whole run.
  const parent =
    inv.session ??
    (typeof ctx.session?.get === "function"
      ? sessionRecord(await ctx.session.get({ sessionID: inv.sessionID }).catch(() => undefined))
      : undefined)
  const sessionModel = inv.model ?? modelRef(parent?.model)
  // An API-created session can have no selected model. Creating a child
  // without one makes OpenCode return an empty assistant response, so fall
  // back to the host's default model rather than silently dropping the whole
  // finder fan-out.
  const hostDefault =
    sessionModel === undefined && typeof ctx.model?.default === "function"
      ? await ctx.model.default().catch(() => undefined)
      : undefined
  const runModel = sessionModel ?? modelRef(hostDefault)
  const sessionEffort = runModel?.variant

  const storage = ctx.storage
  const readStored = (key: string): Promise<unknown> =>
    storage && typeof storage.get === "function"
      ? storage.get(key).catch(() => undefined)
      : Promise.resolve(undefined)
  const storeValue = async (key: string, value: unknown): Promise<void> => {
    if (storage && typeof storage.set === "function") {
      await storage.set(key, value as never).catch(() => {})
    }
  }
  const [storedEffort, storedMax] = await Promise.all([
    readStored(STORAGE_EFFORT),
    readStored(STORAGE_MAX),
  ])
  const effort = resolveEffort(parsed, typeof storedEffort === "string" ? storedEffort : undefined, sessionEffort)

  // A level or --max-findings typed in a non-interactive run is not remembered
  // (official /code-review behavior). --json is our non-interactive proxy.
  const remember = inv.interactive === true && !flags.json
  if (remember && parsed.explicit) await storeValue(STORAGE_EFFORT, parsed.explicit)

  const requestedMode = flags.mode ?? process.env.CODE_REVIEW_MODE
  const invalidMode = requestedMode !== undefined && !Object.hasOwn(VERSIONS, requestedMode)
  const version = asVersion(requestedMode)
  const modelOverride = modelRef(flags.model ?? process.env.CODE_REVIEW_MODEL)
  const family = detectFamily(
    modelOverride?.id ?? runModel?.id,
    flags.family ?? process.env.CODE_REVIEW_FAMILY,
  )
  const cell = resolveCell(version, family, effort)
  if (remember && !cell.suppressMaxFindings) {
    // Only a valid value is persisted. An invalid --max-findings is ignored,
    // so it must not wipe the limit the user set earlier. A cell that suppresses
    // the limit (low-sonnet5) must not persist it either: its contract says it
    // neither reuses nor stores the value.
    const stored = storedMaxFindings(parsed)
    if (stored !== undefined) await storeValue(STORAGE_MAX, stored)
  }
  // The engine renders its own text report and never calls ReportFindings.
  // Only the prompt paths (inline/minimal cells, --driver prompt, or a host
  // without child sessions) go through the 32-entry host schema, so only they
  // need the cap. A deterministic engine report may legitimately exceed 32.
  const childSessions = supportsChildSessions(ctx)
  const usesEngine = flags.driver !== "prompt" && cell.engine === "multi" && childSessions
  const kind: OutputKind = flags.json ? "json" : "reportfindings"
  // An engine report is text, but --fix re-reports through ReportFindings, so
  // that path still needs the host's 32-entry cap.
  const willApplyFix = parsed.fix && !flags.dryRun && !flags.json
  const hasReportFindings = kind === "reportfindings" && (!usesEngine || willApplyFix)
  const limit = resolveMaxFindings(
    parsed,
    cell,
    hasReportFindings,
    typeof storedMax === "number" || storedMax === "all" ? storedMax : undefined,
  )
  const max = promptLimit(cell, limit.stated)

  // `--fix` is an edit action, not a prompt decoration. A dry run or the JSON
  // contract must never append the apply block, on either the inline/prompt
  // path or the engine path.
  // A requested action that the selected output mode cannot perform must be
  // visible in the session, not only in the server log. These notices are
  // included even under --quiet: silently ignoring --fix/--comment is worse
  // than one extra line.
  const actionNotices: string[] = []
  const fixMode = fixAction(parsed.fix, flags.dryRun, flags.json)
  if (fixMode === "dry-run") {
    actionNotices.push("--fix ignored: --dry-run was requested; the working tree was not modified.")
  } else if (fixMode === "json") {
    actionNotices.push(
      "--fix ignored with --json: the JSON contract is a bare array. Run without --json to apply fixes.",
    )
  }
  const applyFix = fixMode === "apply"
  const comment = parsed.comment && !flags.dryRun
  if (parsed.comment && flags.dryRun) {
    actionNotices.push("--comment ignored: --dry-run was requested; no comments were posted.")
  }
  // The prompt path chooses GitHub/GitLab from the reviewed target's origin,
  // not the session cwd: a path or submodule can point at a different host.
  // Resolve the remote only when the invocation actually posts or asks about
  // --post.
  const needsHost = comment || parsed.post
  // Free-form targets ("src/auth.ts, focus on retries") carry their path in a
  // later token. Resolve that hint before choosing the remote, or a submodule
  // review checks the session cwd's host and posts to the wrong repository.
  // The filesystem walk and `/verify` scope probe are only needed when the
  // invocation actually posts or asks about --post.
  // A bare number is a PR target, not a path. Resolving it as a path first
  // would let a same-named directory or submodule redirect host detection to
  // another repository's remote, even though scope resolution reviews the PR.
  const hostTarget =
    needsHost && parsed.target && prTargetNumber(parsed.target) === undefined
      ? extractPathHint(parsed.target, ctx.location.directory) ?? parsed.target
      : undefined
  // Use the same target classifier as scope discovery. Re-deriving the root
  // from the raw target as a path let a directory that shares a branch name
  // send the comments to a different repository than the one reviewed.
  const hostRoot = needsHost
    ? ((await resolveReviewRoot(ctx.location.directory, hostTarget, undefined, {
        ...(inv.signal ? { signal: inv.signal } : {}),
        timeoutMs: 10_000,
      }).catch(() => null)) ?? ctx.location.directory)
    : undefined
  const hostDetails =
    hostRoot !== undefined
      ? await detectHostDetails(hostRoot, undefined, {
          ...(inv.signal ? { signal: inv.signal } : {}),
          timeoutMs: 10_000,
        })
      : { host: "other" as Host }
  const host: Host = hostDetails.host

  // Every path that returns a review prompt decorates it identically. Keeping
  // one assembly point prevents an inline-only decoration (a new --comment or
  // fix contract) from being missed by a fallback path.
  const decorateReview = (text: string): string =>
    decorate(text, {
      target: parsed.target,
      kind,
      fix: applyFix,
      comment,
      suppressFixLater: cell.suppressFixLater,
      host,
    })

  const notices = flags.quiet
    ? [...actionNotices]
    : [
        ...actionNotices,
        ultraNotice(parsed, effort, applyFix),
        invalidMode
          ? `Ignoring unrecognized ${flags.mode !== undefined ? "--mode" : "CODE_REVIEW_MODE"} "${requestedMode}"; valid: ${Object.keys(VERSIONS).join(", ")}. Using ${version}.`
          : undefined,
        cell.fallbackNotice,
        effortNotice(parsed, typeof storedEffort === "string" ? storedEffort : undefined, effort),
        maxFindingsNotice(limit, parsed.maxFindingsIgnored),
        postNotice(parsed, host),
      ].filter((n): n is string => Boolean(n))

  // Every prompt-driven path returns the same shape: optional notices, the
  // recovered prompt, and a model turn to execute it. Keeping one assembly
  // point prevents a new decoration from landing in only one fallback.
  const promptOutcome = (text: string, allNotices: string[] = notices): Outcome => ({
    text: allNotices.length > 0 ? `${allNotices.join("\n")}\n\n${text}` : text,
    needsModel: true,
  })

  // ---- inline / minimal cells: submit the recovered prompt verbatim ------
  if (isInline(cell)) {
    // The inline path never reaches resolveScope. Validate an explicit path
    // target here so a typo cannot silently turn into a working-tree review.
    const missingTarget = missingExplicitPathTarget(ctx.location.directory, parsed.target)
    if (missingTarget !== undefined) {
      const message = `Code review could not start: Review target path not found: ${missingTarget}`
      if (flags.json) {
        inv.log?.(partialRecord([message]))
        return { text: "[]", needsModel: false, bare: true }
      }
      return { text: message, needsModel: true }
    }
    const base = resolveInline(kind, cell.inlineVariant, max)
    let text = decorateReview(base)
    if (!flags.json) text += await verifyFollowUpForTarget(ctx)
    return promptOutcome(text)
  }

  // ---- multi-agent cells ------------------------------------------------
  // A host without child sessions cannot run the deterministic fan-out. Use
  // the recovered single-pass prompt for the selected effort instead of
  // returning an empty, partial engine result.
  if (flags.driver === "prompt" || !childSessions) {
    const base = resolveMulti(kind, effort, max)
    let text = decorateReview(base)
    if (!flags.json) text += await verifyFollowUpForTarget(ctx)
    const allNotices = childSessions
      ? notices
      : [...notices, "Subagent sessions are unavailable in this host; running the single-pass review prompt instead."]
    return promptOutcome(text, allNotices)
  }

  // Host records expose the model as `{providerID, modelID}` as often as the
  // session API's `{providerID, id}`. Normalize both before passing the ref to
  // session.create, or every finder/verifier child fails to start. `parent`,
  // `sessionModel`, and the host default were resolved once at the top.
  const baseModel = modelOverride ?? runModel
  const roleVariants = parseRoleVariants(process.env.CODE_REVIEW_ROLE_VARIANTS)
  const runner: AgentRunner = makeRunner(ctx, {
    parentSessionID: inv.sessionID,
    model: baseModel,
    // An agent's own `model` wins; otherwise this role variant is applied to
    // the parent model; otherwise the parent model is inherited.
    modelFor: (req) => {
      const variant = roleVariants[req.label] ?? roleVariants[req.role]
      return variant && baseModel ? { ...baseModel, variant } : undefined
    },
    schemaResults,
    schemaFailures,
    childSessions: reviewChildSessions,
    activity,
    keepSessions: flags.keepSessions ?? process.env.CODE_REVIEW_KEEP_SESSIONS === "true",
    onLog: inv.log,
  })

  let scope: Scope
  try {
    scope = await resolveScope({
      cwd: ctx.location.directory,
      target: parsed.target,
      signal: inv.signal,
      includeDiffLines: cell.finderBudgetHint,
    })
  } catch (error) {
    const message = `Code review could not start: ${error instanceof Error ? error.message : String(error)}`
    // --json promises a bare array. Do not route an error through a model turn
    // that would turn the contract into prose; report on stderr and return [].
    if (flags.json) {
      inv.log?.(partialRecord([message]))
      return { text: "[]", needsModel: false, bare: true }
    }
    return {
      text: message,
      // Route the error through the model so the command handler does not
      // append a "review complete" acknowledgement to a review that never ran.
      needsModel: true,
    }
  }

  const writeArtifact = async (result: EngineResult): Promise<void> => {
    // --dry-run promises no working-tree writes, and --json promises a bare
    // array with no side effects. A normal review is read-only too: only an
    // explicit CODE_REVIEW_REPORT_DIR opts into writing an artifact, so the
    // review never dirties the checkout it inspected.
    if (flags.dryRun || flags.json) return
    const directory = process.env.CODE_REVIEW_REPORT_DIR
    if (!directory) return
    const path = await writeReportArtifact({
      root: scope.root,
      result,
      files: scope.files,
      directory,
    })
    if (path) inv.log?.(`Report artifact: ${path}`)
  }

  if (scope.files.length === 0) {
    const incomplete = (scope.warnings?.length ?? 0) > 0
    const empty: EngineResult = {
      level: effort,
      summary: incomplete
        ? "No changed files were found, but at least one diff-discovery command failed — this is not a complete review."
        : "No changes found to review.",
      findings: [],
      refuted: [],
      stats: { finders: 0, candidates: 0, verifierAgents: 0, verified: 0, refuted: 0, dupes: 0, budgetDropped: 0, reported: 0 },
      partial: incomplete,
      warnings: scope.warnings ?? [],
      cell: cell.id,
    }
    await writeArtifact(empty)
    if (notices.length > 0 && flags.json) for (const notice of notices) inv.log?.(notice)
    if (flags.json) {
      if (incomplete) {
        inv.log?.(
          partialRecord(empty.warnings),
        )
      } else {
        inv.log?.("No changes found to review.")
      }
    }
    // A clean checkout still has option notices (an ignored --max-findings,
    // for example), and an incomplete discovery still has the failure list.
    // Returning only the generic summary hid both.
    const noticePrefix = notices.length > 0 && !flags.json ? `${notices.join("\n")}\n\n` : ""
    const warningBlock =
      !flags.json && empty.warnings.length > 0
        ? `\n\nWarnings:\n${empty.warnings.map((w) => `  - ${w}`).join("\n")}`
        : ""
    return {
      text: flags.json ? "[]" : `${noticePrefix}${empty.summary}${warningBlock}`,
      engine: empty,
      needsModel: false,
      bare: flags.json,
    }
  }

  if (!flags.quiet) {
    // The host callback may reject or throw synchronously; neither failure may
    // abort a review that can still complete.
    await reportProgress(
      inv.progress,
      `Reviewing ${scope.files.length} changed file(s) at ${effort} effort (${cell.id})`,
    )
  }

  const result = await runReview({
    level: effort,
    cell,
    scope,
    runner,
    statedLimit: limit.stated,
    finderBudget: flags.fullFleet ? undefined : plannedFinderCount(cell, scope.diffLines),
    // Workflow cells default to `semanticMerge: false` in the cell table, but
    // their synthesizer is mandatory (`synthesis` is "index"/"text"). Passing
    // that default through would disable it. Only an explicit
    // --no-semantic-merge should turn synthesis off; otherwise leave the
    // engine's undefined default (enabled) and let the cell's synthesis mode
    // decide.
    semanticMerge: flags.semanticMerge ?? (cell.semanticMerge ? true : undefined),
    signal: inv.signal,
    concurrency: resolveConcurrency(flags.concurrency, process.env.CODE_REVIEW_CONCURRENCY),
    onEvent: (event) => {
      if (flags.quiet) return
      // The host callback may reject or throw synchronously. A floating
      // failure would terminate the plugin process, so observe both.
      const report = (status: string): void => {
        void reportProgress(inv.progress, status)
      }
      if (event.type === "finder") report(`${event.label}: ${event.candidates} candidate(s)`)
      if (event.type === "phase") report(`Phase: ${event.phase}`)
    },
  })

  // A scope-level discovery failure (one of several git diff calls failed)
  // makes the engine result partial even when enough files were listed.
  if (scope.warnings?.length) {
    result.partial = true
    result.warnings.unshift(...scope.warnings)
  }

  // A host can advertise child sessions but fail every create (for example,
  // the review-finder/review-verifier agents are not registered). Falling back
  // to the recovered single-pass prompt is more useful than an empty partial
  // engine report. Only an all-finder failure qualifies: a single unparseable
  // finder alongside finders that legitimately found nothing is still a
  // completed engine run and must not be discarded.
  const allFindersFailed =
    result.stats.finders > 0 && (result.stats.finderFailures ?? 0) >= result.stats.finders
  const agentOutputMissing =
    !inv.signal?.aborted &&
    allFindersFailed &&
    result.stats.candidates === 0 &&
    result.stats.verifierAgents === 0
  if (agentOutputMissing) {
    const warning = "Subagent sessions produced no usable results; running the single-pass review prompt instead."
    if (flags.json) {
      // The JSON contract is a bare array. Keep it intact and report the
      // incomplete run on stderr instead of returning the fallback prompt.
      inv.log?.(
        partialRecord([...result.warnings, warning]),
      )
      if (result.truncatedFrom !== undefined) inv.log?.(truncatedRecord(result.truncatedFrom))
      return { text: formatJson(result), engine: result, needsModel: false, bare: true }
    }
    // The fallback prompt calls ReportFindings, so it must respect the host's
    // 32-entry cap even when the deterministic engine was not capped.
    const fallbackMax =
      typeof max === "number" ? Math.min(max, HARD_FINDINGS_CAP) : max === "all" ? HARD_FINDINGS_CAP : max
    // All finders failed. Do not hand back a multi-agent prompt that tells the
    // model to spawn the same finder subagents that just failed; run the
    // recovered single-pass prompt instead.
    const base = resolveInline(kind, cell.inlineVariant, fallbackMax)
    let text = decorateReview(base)
    text += await verifyFollowUp(ctx, scope.files)
    const allNotices = [...notices, warning]
    return promptOutcome(text, allNotices)
  }

  await writeArtifact(result)

  const prefix = notices.length > 0 && !flags.json ? `${notices.join("\n")}\n\n` : ""
  if (notices.length > 0 && flags.json) for (const notice of notices) inv.log?.(notice)
  // `--json` promises a bare array. A prose warning would break every JSON
  // consumer exactly when the run is incomplete, so emit a stable
  // machine-readable record on stderr instead; the array itself stays intact.
  if (result.partial && flags.json) {
    inv.log?.(
      partialRecord(result.warnings),
    )
  }
  if (result.truncatedFrom !== undefined && flags.json) {
    inv.log?.(truncatedRecord(result.truncatedFrom))
  }
  let body = flags.json
    ? formatJson(result)
    : formatHuman(result, { includeRefuted: flags.verbose, verbose: flags.verbose })
  // Hs(U): the reference appends the fix block to every output contract. The
  // command handler sees "## Applying fixes" and routes the result through the
  // model so the fixes are actually applied. A dry run or --json never
  // reaches that path; those notices were emitted before the review started.
  if (fixMode === "apply") body += fixBlock(kind)
  // The prompt paths decorate every review with FIX_LATER. The engine report
  // is shown to the user, so it must not include model-facing instructions;
  // the ReportFindings tool description carries the same outcome contract for
  // a later fix turn.
  let followUp = ""
  if (!flags.json) {
    followUp = await verifyFollowUp(ctx, scope.files)
    if (followUp) body += followUp
  }
  // A completed engine report needs no model turn unless the fix block or the
  // /verify suggestion still has to run. `--json` is the output itself, so it
  // is displayed verbatim rather than with the completion note.
  const needsModel = fixMode === "apply" || followUp.length > 0

  if (comment) {
    // The reviewed root may be a submodule or a free-form path hint; its origin
    // remote owns the PR. Re-detect only when that root differs from the one
    // already used for the notice, so the normal case stays a single call.
    const scopeHostDetails =
      scope.root === (hostRoot ?? scope.root)
        ? hostDetails
        : await detectHostDetails(scope.root, undefined, {
            ...(inv.signal ? { signal: inv.signal } : {}),
            timeoutMs: 10_000,
          })
    const posted = await postComments({
      cwd: scope.root,
      scope,
      result,
      log: inv.log,
      host: scopeHostDetails.host,
      ...(scopeHostDetails.hostname ? { githubHostname: scopeHostDetails.hostname } : {}),
      signal: inv.signal,
    })
    if (posted && flags.json) inv.log?.(posted)
    const extra = posted && !flags.json ? `\n\n${posted}` : ""
    return { text: prefix + body + extra, engine: result, needsModel, ...(flags.json ? { bare: true } : {}) }
  }

  return { text: prefix + body, engine: result, needsModel, ...(flags.json ? { bare: true } : {}) }
}

export default Plugin.define({
  id: "code-review-opencode",
  async setup(ctx: AnyCtx) {
    /** Typed child-agent results, keyed by the child session that submitted them. */
    const schemaResults = new Map<string, unknown>()
    const schemaFailures = new Map<string, number>()
    /** Child sessions created by this review engine; only these are recursion-guarded. */
    const reviewChildSessions = new Set<string>()
    /** Stream deltas keep a long single-step reasoning turn live for the watchdog. */
    const activity = trackActivity(ctx)
    /** Last outcome list posted per session, so a repeated re-report is quiet. */
    const reportedOutcomeHashes = new Map<string, string>()
    const MAX_OUTCOME_HASHES = 200
    /** Show a completed list in the session, trying the inbox before a turn. */
    /** Post without starting a model turn. Returns the failure, if any. */
    const deliverSynthetic = async (
      sessionID: string,
      text: string,
    ): Promise<string | undefined> => {
      if (typeof ctx.session.synthetic !== "function") return "host has no synthetic delivery"
      try {
        await ctx.session.synthetic({ sessionID, text, resume: false })
        return undefined
      } catch (error) {
        return error instanceof Error ? error.message : String(error)
      }
    }
    const deliverToSession = async (
      sessionID: string,
      text: string,
    ): Promise<string | undefined> => {
      const syntheticFailure = await deliverSynthetic(sessionID, text)
      if (syntheticFailure === undefined) return undefined
      if (typeof ctx.session.prompt === "function") {
        try {
          await ctx.session.prompt({ sessionID, text })
          return undefined
        } catch (error) {
          return error instanceof Error ? error.message : String(error)
        }
      }
      return syntheticFailure
    }
    // The schema tools are registered globally, so a stray call from a
    // non-review session would otherwise pin its payload for the process
    // lifetime. Current review children are removed by the runner.
    const MAX_SCHEMA_ENTRIES = 200

    /* ---------------------- child-agent schema tools ---------------------- */
    await ctx.tool.transform((editor: AnyCtx) => {
      const register = (
        name: string,
        description: string,
        input: AnyCtx,
        normalize: (value: unknown) => NormalizedCall<unknown>,
      ) => {
        editor.add({
          name,
          description,
          input,
          execute: async (value: AnyCtx, context: AnyCtx) => {
            const result = normalize(value)
            if (!result.ok) {
              const failures = (schemaFailures.get(context.sessionID) ?? 0) + 1
              setCapped(
                schemaFailures,
                context.sessionID,
                failures,
                MAX_SCHEMA_ENTRIES,
                reviewChildSessions,
              )
              if (failures >= 3) {
                return {
                  content: `Structured output rejected: ${result.error}. Retry limit reached; end your turn without a result.`,
                }
              }
              return { content: `Structured output rejected: ${result.error}. Fix the shape and call once more.` }
            }
            schemaFailures.delete(context.sessionID)
            setCapped(
              schemaResults,
              context.sessionID,
              result.value,
              MAX_SCHEMA_ENTRIES,
              reviewChildSessions,
            )
            const noteText = result.notes.length > 0 ? ` ${summarizeNotes(result.notes)}` : ""
            const content =
              result.notes.length > 0
                ? `Structured output accepted with repairs.${noteText}`
                : "Structured output provided successfully."
            return { content }
          },
        })
      }

      register(
        SCHEMA_TOOL_NAMES.candidates,
        "Submit the candidate findings for one code-review finder angle. Call exactly once. If any candidate is malformed, the call is rejected so the complete list can be re-emitted.",
        CANDIDATES_SCHEMA,
        (value) => normalizeCandidatesCall(value),
      )
      register(
        SCHEMA_TOOL_NAMES.verdict,
        "Submit one CONFIRMED/PLAUSIBLE/REFUTED verdict for a code-review candidate. Call exactly once.",
        VERDICT_SCHEMA,
        (value) => normalizeVerdictCall(value),
      )
      register(
        SCHEMA_TOOL_NAMES.groupVerdicts,
        "Submit one verdict per candidate in a grouped code-review verification. Call exactly once. Every verdict requires evidence; an incomplete payload is rejected so it can be re-emitted.",
        GROUP_VERDICTS_SCHEMA,
        (value) => normalizeGroupVerdictsCall(value),
      )
      register(
        SCHEMA_TOOL_NAMES.report,
        "Submit the synthesized code-review report. Call exactly once. Invalid individual findings are dropped; valid findings are kept.",
        REPORT_SCHEMA,
        (value) => normalizeReportCall(value),
      )
      register(
        SCHEMA_TOOL_NAMES.decisions,
        "Submit merge/rank decisions for verified code-review findings by index. Call exactly once. Every decision must be valid; an invalid payload is rejected so the complete plan can be re-emitted.",
        DECISIONS_SCHEMA,
        // The reference's structured-output loop rejects an invalid payload
        // and re-prompts. Keep that failure behavior; the description above
        // must not promise per-decision tolerance.
        (value) => normalizeDecisionsCall(value),
      )
    })

    /* ------------------------- ReportFindings ------------------------- */
    await ctx.tool.transform((editor: AnyCtx) => {
      editor.add({
        name: "ReportFindings",
        description:
          "Report code-review findings as a typed list so the host UI can render them. Use this only when the active code-review instructions tell you to report findings with this tool; otherwise follow whatever output format those instructions specify. When reporting a review's results, call it once with the verified findings ranked most-severe first (empty array if nothing survived verification) and do not also print the findings as text. When re-reporting after applying fixes (only if the apply instructions ask for it), set `outcome` on each finding to what actually happened.",
        input: REPORT_FINDINGS_SCHEMA as AnyCtx,
        execute: async (input: AnyCtx, context: AnyCtx) => {
          const parsed = normalizeReportFindings(input)
          if (!parsed.ok) return { content: `ReportFindings rejected the call: ${parsed.error}` }
          const findings = parsed.findings
          // After --fix the model re-reports the same findings with outcomes.
          // The reference host renders that list; post a synthetic summary so
          // the command path shows it too. A repeated identical list is quiet.
          const outcomeSummary = formatOutcomeSummary(findings)
          let deliveryError: string | undefined
          if (outcomeSummary) {
            const hash = JSON.stringify(findings.map((f) => [f.file, f.line, f.outcome]))
            if (reportedOutcomeHashes.get(context.sessionID) !== hash) {
              // Post first, then remember the list. Caching before delivery
              // skipped the model's identical re-report after one transient
              // host failure, so the per-finding outcomes never appeared.
              deliveryError = await deliverToSession(context.sessionID, outcomeSummary)
              if (deliveryError === undefined) {
                // Bound the map: a long-lived process must not retain one entry
                // per session that ever used --fix.
                setCapped(reportedOutcomeHashes, context.sessionID, hash, MAX_OUTCOME_HASHES)
              }
            }
          }
          const noteText = parsed.notes.length > 0 ? ` ${summarizeNotes(parsed.notes)}` : ""
          const outcomeNote =
            deliveryError !== undefined
              ? ` Fix outcomes were not posted to the session (${deliveryError}); re-report the same list to retry.`
              : ""
          return {
            content: formatToolResult(findings.length) + noteText + outcomeNote,
            metadata: {
              count: findings.length,
              level: parsed.level,
              findings,
              ...(parsed.notes.length > 0 ? { notes: parsed.notes } : {}),
            },
          }
        },
      })
    })

    /* --------------------------- code_review --------------------------- */
    await ctx.tool.transform((editor: AnyCtx) => {
      editor.add({
        name: "code_review",
        description:
          "Run the /code-review-opencode workflow on the current diff or a PR/branch/path target. It is a port of Claude Code's /code-review. Read-only by default; set fix only when the user explicitly asked for fixes, and comment only when they explicitly asked to post review comments.",
        input: {
          type: "object",
          properties: {
            level: { type: "string", enum: LEVELS },
            target: { type: "string", description: "PR number, branch, ref range, path, or free-form scope instructions" },
            mode: { type: "string", enum: Object.keys(VERSIONS) },
            maxFindings: { anyOf: [{ type: "integer", minimum: 1 }, { type: "string", enum: ["all"] }] },
            json: { type: "boolean" },
            fix: { type: "boolean" },
            comment: { type: "boolean" },
          },
          additionalProperties: false,
        },
        execute: async (input: AnyCtx, context: AnyCtx) => {
          // The fallback path exists for hosts that expose create/prompt but
          // not get; probing get here would crash before resolveAndRun can
          // choose the single-pass review.
          // Recursion guard: a review's own finder/verifier child must not
          // start another review. The runner registers the exact session id,
          // so use it directly: a failed session.get lookup must not disable
          // the guard and let a child fan out another review.
          const childRejection = {
            content:
              "code_review cannot run from a review child session. Return your result to the parent review instead of starting another review.",
          }
          if (reviewChildSessions.has(context.sessionID)) {
            return childRejection
          }
          const rawSession =
            typeof ctx.session?.get === "function"
              ? await ctx.session.get({ sessionID: context.sessionID }).catch(() => undefined)
              : undefined
          // A descendant of a review child (for example a grandchild spawned
          // by a finder) must not start another review. Do not reject every
          // session with a parentID: a user's own subagent is a legitimate
          // caller, and only the review engine's descendants are off limits.
          const insideReview = async (): Promise<boolean> => {
            let parentID = sessionRecord(rawSession)?.parentID ?? undefined
            const visited = new Set<string>()
            while (parentID && !visited.has(parentID)) {
              if (reviewChildSessions.has(parentID)) return true
              visited.add(parentID)
              if (typeof ctx.session?.get !== "function") return false
              const parent = sessionRecord(
                await ctx.session.get({ sessionID: parentID }).catch(() => undefined),
              )
              parentID = parent?.parentID ?? undefined
            }
            return false
          }
          if (await insideReview()) {
            return childRejection
          }
          const session = sessionRecord(rawSession)
          const outcome = await resolveAndRun(
            ctx,
            {
              sessionID: context.sessionID,
              raw: "",
              structured: {
                level: input?.level,
                target: input?.target,
                mode: input?.mode,
                maxFindings: input?.maxFindings,
                json: input?.json === true,
                fix: input?.fix === true,
                comment: input?.comment === true,
              },
              signal: context.signal,
              session,
              model: modelRef(session?.model),
              progress: (status) => context.progress?.({ status }),
              log: (m) => console.error(m),
            },
            schemaResults,
            schemaFailures,
            reviewChildSessions,
            activity.last,
          )
          // The reference's host findings list is the ReportFindings payload.
          // The command path renders text; the tool path also exposes the typed
          // `{level, findings}` metadata for hosts that render it.
          return {
            content: outcome.text,
            ...(outcome.engine ? { metadata: formatReportFindings(outcome.engine) } : {}),
          }
        },
      })
    })

    /* ---------------------- /code-review-opencode ---------------------- */
    await ctx.command.transform((editor: AnyCtx) => {
      editor.add({
        name: "code-review-opencode",
        description:
          "Review the current diff, or a PR number/branch/path target, for correctness bugs (plus reuse/simplification/efficiency cleanups where the model's recipe covers them) at the effort level given first, before any target (low|medium|high|xhigh|max: from few high-confidence findings to many, some uncertain); with no level given, it reuses the level you typed last. Pass --comment to post findings as inline PR comments, or --fix to apply them to the working tree after the review. Pass --max-findings <n> to report up to n findings, or --max-findings all for every finding. The choice stays until you pass --max-findings default.",
        execute: async ({ sessionID, prompt, delivery }: AnyCtx) => {
          // A CommandInvocation carries text/files/agents/skills, not the
          // selected model or effort variant. Read the session so the command
          // path chooses the same family/effort cell as the tool path.
          const rawSession =
            typeof ctx.session?.get === "function"
              ? await ctx.session.get({ sessionID }).catch(() => undefined)
              : undefined
          const session = sessionRecord(rawSession)
          const sessionModel = modelRef(session?.model)
          // The command's text is replaced by the recovered review prompt, so
          // the original mention offsets no longer address it. Keep the
          // attachments themselves and drop only those offsets.
          const attachments = {
            ...(Array.isArray(prompt?.files) && prompt.files.length > 0
              ? { files: prompt.files.map(({ mention: _mention, ...file }: AnyCtx) => file) }
              : {}),
            ...(Array.isArray(prompt?.agents) && prompt.agents.length > 0
              ? { agents: prompt.agents.map(({ mention: _mention, ...agent }: AnyCtx) => agent) }
              : {}),
            ...(Array.isArray(prompt?.skills) && prompt.skills.length > 0
              ? { skills: prompt.skills.map(({ mention: _mention, ...skill }: AnyCtx) => skill) }
              : {}),
          }
          const outcome = await resolveAndRun(
            ctx,
            {
              sessionID,
              session,
              raw: prompt?.text ?? "",
              model: sessionModel,
              interactive: true,
              log: (m) => console.error(m),
            },
            schemaResults,
            schemaFailures,
            reviewChildSessions,
            activity.last,
          )
          // Engine --json is the command's output, not a prompt. Display it
          // without a model turn so the visible result stays the bare array.
          if (outcome.bare) {
            // A transient synthetic failure must not drop the JSON the engine
            // just produced; fall through to the constrained turn.
            if ((await deliverSynthetic(sessionID, outcome.text)) === undefined) return
            // The host has no way to display a message without a model turn.
            // Constrain that turn to echoing the JSON verbatim; otherwise the
            // bare-array contract breaks in the one environment the fallback
            // exists for.
            await ctx.session.prompt({
              sessionID,
              delivery,
              text: `Output exactly the following text and nothing else: no prose, no Markdown fences, no reformatting.\n\n${outcome.text}`,
            })
            return
          }
          // Prompt-driven paths (inline cells and --fix) must go through the
          // model so the recovered instructions actually run. A completed
          // engine report needs no model turn at all: display it with
          // synthetic and avoid paying for a no-op acknowledgement.
          // A transient synthetic failure must not drop a completed engine
          // report; fall through to the constrained turn below.
          if (!outcome.needsModel && (await deliverSynthetic(sessionID, outcome.text)) === undefined) return
          // A host without synthetic still needs a turn to show the report.
          // Constrain it to a short acknowledgement rather than a re-review.
          const text = outcome.needsModel
            ? outcome.text
            : `${outcome.text}\n\n---\nThe review above is complete and was produced by the deterministic /code-review-opencode engine. Do not re-run the review, do not re-derive findings, and do not restate the list. Reply with one short line confirming completion.`
          // Attachments belong on the model-driven review turn. The bare --json
          // echo and the completion acknowledgement must stay exact and should
          // not gain review context.
          await ctx.session.prompt({
            sessionID,
            text,
            delivery,
            ...(outcome.needsModel ? attachments : {}),
          })
        },
      })
    })
    // The event subscription outlives individual reviews; tie it to the
    // plugin instance so a reload does not leave a second reader running.
    return () => activity.stop()
  },
})
