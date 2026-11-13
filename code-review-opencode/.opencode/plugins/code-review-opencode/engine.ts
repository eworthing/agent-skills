/**
 * Deterministic orchestration of the recovered review graphs.
 *
 * Three execution shapes are implemented, selected by the versioned cell:
 *   - cc-2.1.318        barrier find -> one verifier per candidate -> sweep -> rank
 *   - cc-workflow-2.1.162 streaming find -> dedup -> one verifier per candidate
 *                        (hard 25-verifier budget) -> sweep -> synthesis agent
 *   - cc-workflow-2.1.221 barrier find -> group by (file,line) -> one verifier per
 *                        location -> sweep -> index-based synthesis + backfill
 *
 * The engine never edits the working tree and never posts comments; those are
 * separate, explicit actions in the plugin layer.
 */
import { existsSync, realpathSync } from "node:fs"
import {
  BASE_ANGLES,
  CLEANUP_ANGLES_162,
  CLEANUP_TEXT_221,
  EXTENDED_ANGLES,
  candidateDedupPrompt,
  finderPrompt,
  groupVerifierPrompt,
  renderScope,
  sweepPrompt,
  synthPromptIndex,
  synthPromptText,
  verifierPrompt,
} from "./prompts.ts"
import { finderCap, type Cell, type Level } from "./cells.ts"
import {
  asCandidatesResult,
  asDecisions,
  asGroupVerdicts,
  asReport,
  asVerdict,
  normalizeFinding,
  NO_EVIDENCE,
  STEP_LIMIT_PLACEHOLDER,
  type Decisions,
  type RawFinding,
} from "./json.ts"
import { scopeBlock, unquoteGitPath, type Scope } from "./scope.ts"
import { mapLimit } from "./concurrency.ts"
import { location, lineOf, pluralize, renderedLocation, shortSummary } from "./finding.ts"

export type Role = "finder" | "verifier" | "sweep" | "synthesize"

export type AgentRequest = {
  role: Role
  label: string
  phase: string
  prompt: string
  agent: string
  schemaName: "candidates" | "verdict" | "groupVerdicts" | "report" | "decisions"
  signal?: AbortSignal
}

export type AgentRunner = (req: AgentRequest) => Promise<unknown | null>

export type Finding = RawFinding & {
  verdict?: "CONFIRMED" | "PLAUSIBLE"
  kind: "correctness" | "cleanup"
}

export type EngineEvent =
  | { type: "phase"; phase: string }
  | { type: "finder"; label: string; candidates: number }
  | { type: "verify"; kept: number; refuted: number }
  | { type: "sweep"; candidates: number }
  | { type: "warning"; message: string }
  | { type: "stats"; stats: EngineStats }

export type EngineStats = {
  finders: number
  candidates: number
  verifierAgents: number
  verified: number
  refuted: number
  dupes: number
  budgetDropped: number
  reported: number
  /** Finders whose child call produced no usable structured result. */
  finderFailures?: number
}

export type EngineResult = {
  level: Level
  summary: string
  findings: Finding[]
  refuted: Array<{ file: string; line?: number; summary: string }>
  stats: EngineStats
  partial: boolean
  warnings: string[]
  cell: string
  /** Original survivor count when the effort cap cut the report short. */
  truncatedFrom?: number
}

export type EngineOptions = {
  level: Level
  cell: Cell
  scope: Scope
  runner: AgentRunner
  statedLimit?: number | "all"
  /** Qs(e,n): diff-size finder budget; undefined runs one finder per angle. */
  finderBudget?: number
  /**
   * Platform equivalent of the reference model's in-context semantic merge and
   * ranking: one synthesizer child returns merge/rank decisions by index.
   */
  semanticMerge?: boolean
  signal?: AbortSignal
  concurrency?: number
  onEvent?: (event: EngineEvent) => void
}

type Finder = {
  label: string
  kind: "correctness" | "cleanup"
  text: string
  cap: number
  merged?: boolean
  /** A grouped finder covering both correctness and cleanup lenses. */
  multiLens?: boolean
  /** The lens labels inside this finder, used to attribute a candidate's kind. */
  lenses?: Array<{ label: string; kind: "correctness" | "cleanup" }>
}

const AGENT_IDS = {
  finder: "review-finder",
  verifier: "review-verifier",
  sweep: "review-sweep",
  synthesize: "review-synth",
} as const

type FileIndex = {
  files: Set<string>
  root?: string
  realRoot?: string
}

function realPath(value: string): string {
  try {
    return realpathSync(value).replaceAll("\\", "/").replace(/\/+$/, "")
  } catch {
    return value.replaceAll("\\", "/").replace(/\/+$/, "")
  }
}

/** Resolve the repo root once per review instead of once per candidate. */
function makeFileIndex(scope: Scope): FileIndex {
  const root = scope.root ? realPath(scope.root) : undefined
  const declaredRoot = scope.root?.replaceAll("\\", "/").replace(/\/+$/, "")
  return {
    files: new Set(scope.files),
    ...(declaredRoot ? { root: declaredRoot } : {}),
    ...(root ? { realRoot: root } : {}),
  }
}

/** Canonicalise a path against the scope's repo-relative list (v2.1.221). */
function canonFile(raw: string, index: FileIndex): string {
  if (!raw) return ""
  // A real filename may itself begin and end with a double quote. If the
  // reported path is already in the changed-file list, it is authoritative:
  // unquoting it would strip those literal quotes and point at another path.
  if (index.files.has(raw)) return raw
  // A finder can copy a git-quoted diff header (`"b/caf\303\251.ts"`).
  // Replacing its backslashes directly would turn the octal escapes into
  // path separators, so unquote first, then normalize separators. A POSIX
  // filename may itself contain a literal backslash; check the unquoted form
  // against the changed-file list before treating backslashes as separators.
  const unquoted = unquoteGitPath(raw)
  if (index.files.has(unquoted)) return unquoted
  const p = unquoted.replaceAll("\\", "/").replace(/^\.\//, "")
  if (index.files.has(p)) return p
  // Only strip a real repository-root prefix. Suffix matching alone turns a
  // report about unchanged `lib/src/a.ts` into the changed `src/a.ts`.
  const underRoot = (value: string): string | undefined => {
    for (const base of [index.root, index.realRoot]) {
      if (base && value.startsWith(`${base}/`)) {
        const rel = value.slice(base.length + 1)
        if (index.files.has(rel)) return rel
      }
    }
    return undefined
  }
  if (index.root) {
    const rel = underRoot(p)
    if (rel) return rel
  }
  // A finder may copy the `b/` side of a diff header, or report an absolute
  // path through a symlinked checkout. Resolve the latter physically and only
  // map it when the physical path is actually inside the repository.
  if (p.startsWith("b/") || p.startsWith("a/")) {
    const rel = p.slice(2)
    const base = index.realRoot ?? index.root
    // Only treat the prefix as a diff header when the literal path is not a
    // real file: an unchanged `a/lib.ts` must not map to changed `lib.ts`.
    if (index.files.has(rel) && (!base || !existsSync(`${base}/${p}`))) return rel
  }
  if (p.startsWith("/")) {
    const rel = underRoot(realPath(p))
    if (rel) return rel
  }
  return p
}

const NORMALIZED_CACHE = new Map<string, string>()
const TOKEN_CACHE = new Map<string, Set<string>>()

function normalizedSummary(s: string): string {
  const cached = NORMALIZED_CACHE.get(s)
  if (cached !== undefined) return cached
  const normalized = s
    .toLowerCase()
    .normalize("NFKC")
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim()
  // A summary made only of punctuation or emoji still has to stay distinct
  // from another such summary; an empty normalized form would merge them all.
  const result = normalized || s.trim().toLowerCase()
  if (NORMALIZED_CACHE.size >= 10_000) NORMALIZED_CACHE.clear()
  NORMALIZED_CACHE.set(s, result)
  return result
}

/** v2.1.162 dedup key: file + 5-line bucket + the full normalized claim. */
function dedupKey162(c: RawFinding): string {
  // The reference buckets by file and five lines. That alone drops two
  // distinct defects that happen to land in the same bucket, so the claim is
  // part of the key: only the same claim at a nearby line is a duplicate.
  const bucket = c.line != null ? Math.floor(c.line / 5) * 5 : "x"
  return `${c.file}:${bucket}:${normalizedSummary(c.summary)}`
}

/**
 * Shared seen-set dedup. The accept hook lets the streaming path enforce its
 * hard verifier budget without marking rejected candidates as seen.
 */
function dedupeBy<T extends RawFinding>(
  items: T[],
  key: (c: T) => string,
  seen: Set<string> = new Set(),
  accept?: (c: T) => boolean,
): { novel: T[]; dupes: number } {
  const novel: T[] = []
  let dupes = 0
  for (const c of items) {
    const k = key(c)
    if (seen.has(k)) {
      dupes++
      continue
    }
    if (accept && !accept(c)) continue
    seen.add(k)
    novel.push(c)
  }
  return { novel, dupes }
}

/** v2.1.318 has no specified deterministic key; merge only exact claims. */
function dedupKey318(c: RawFinding): string {
  return `${c.file}:${c.line ?? "?"}:${normalizedSummary(c.summary)}`
}

const STOP_WORDS = new Set([
  "the", "and", "for", "that", "this", "with", "from", "into", "when", "then",
  "than", "are", "was", "were", "has", "have", "had", "not", "but", "its",
  "it", "is", "be", "as", "at", "by", "on", "or", "of", "to", "in", "a", "an",
])

/** Words too generic to prove two adjacent-line cleanup claims are one defect. */
const GENERIC_WORDS = new Set([
  "new", "use", "used", "uses", "add", "added", "adds", "existing", "still",
  "two", "place", "places", "instead", "through", "one", "mechanism", "rule",
  "call", "site", "code", "line", "lines", "value", "values", "case", "cases",
  "make", "makes", "made", "change", "changes", "changed", "also", "same",
  // Generic cleanup vocabulary: two adjacent "unused parameter" findings are
  // distinct defects, but the shared words cannot prove they are one.
  "unused", "parameter", "parameters", "duplicate", "duplicated", "helper",
  "function", "functions", "variable", "variables", "dead", "redundant",
  "simplify", "simplification", "reuse", "complexity", "inline", "inlined",
  "inlines", "implements", "implemented", "implementation", "foo", "bar",
])

function summaryTokens(s: string): Set<string> {
  const cached = TOKEN_CACHE.get(s)
  if (cached !== undefined) return cached
  const tokens = new Set(
    normalizedSummary(s)
      .split(" ")
      .filter((t) => t.length > 2 && !STOP_WORDS.has(t)),
  )
  if (TOKEN_CACHE.size >= 10_000) TOKEN_CACHE.clear()
  TOKEN_CACHE.set(s, tokens)
  return tokens
}

/**
 * Shared claim comparator. Every stage (post-verify merge, sweep-refuted guard,
 * text-synthesizer matching) uses this one spelling of "same claim wording"
 * with an explicit policy, so the thresholds cannot drift apart per stage.
 */
type ClaimPolicy = {
  /** Jaccard overlap at or above this is the same claim. */
  jaccard?: number
  /** Shared tokens / smaller token set at or above this is the same claim. */
  containment?: number
  /** Any shared non-stop token is enough (same-anchor synthesis match). */
  anyToken?: boolean
}

function sameClaim(a: string, b: string, policy: ClaimPolicy = {}): boolean {
  if (normalizedSummary(a) === normalizedSummary(b)) return true
  const ta = summaryTokens(a)
  const tb = summaryTokens(b)
  if (ta.size === 0 || tb.size === 0) return false
  let intersection = 0
  for (const t of ta) if (tb.has(t)) intersection++
  if (policy.anyToken && intersection > 0) return true
  if (policy.jaccard !== undefined && intersection / (ta.size + tb.size - intersection) >= policy.jaccard) {
    return true
  }
  if (policy.containment !== undefined && intersection / Math.max(1, Math.min(ta.size, tb.size)) >= policy.containment) {
    return true
  }
  return false
}

/** Per-stage policies. Keep every threshold here, not at the call sites. */
const CLAIM_POLICY = {
  fileLevel: { jaccard: 0.5 } satisfies ClaimPolicy,
  sameLine: { jaccard: 0.3, containment: 0.4 } satisfies ClaimPolicy,
  /** Strong same-line summary paraphrase: same defect even with different consequences. */
  paraphrase: { jaccard: 0.52 } satisfies ClaimPolicy,
  /** Weaker summary overlap needs the failure mechanisms to agree. */
  failureScenario: { jaccard: 0.2, containment: 0.3 } satisfies ClaimPolicy,
  refuted: { jaccard: 0.7 } satisfies ClaimPolicy,
  synthAnchor: { anyToken: true } satisfies ClaimPolicy,
  synth: { jaccard: 0.6 } satisfies ClaimPolicy,
}

/**
 * The reference's Phase 2 dedup is semantic, performed by the main model.
 * The deterministic engine approximates it: same file, compatible line, and
 * a paraphrase-level token overlap. The thresholds are calibrated against
 * observed finder paraphrases (0.17–0.43 Jaccard at the same line), which are
 * the same defect worded differently. A claim at the same line with almost no
 * shared vocabulary stays separate.
 */
function sameDefect(a: RawFinding, b: RawFinding): boolean {
  if (a.file !== b.file) return false
  // A cleanup claim and a correctness claim at the same location are not the
  // same defect. Merging them lets one absorb the other's rank and text.
  const ka = (a as { kind?: string }).kind
  const kb = (b as { kind?: string }).kind
  if (ka !== undefined && kb !== undefined && ka !== kb) return false
  const la = lineOf(a) ?? -1
  const lb = lineOf(b) ?? -1

  if (la === -1 || lb === -1) {
    // A file-level claim can describe the same defect as a line claim, but it
    // also covers every line in the file. Only merge when the wording is
    // nearly identical; otherwise a second real defect would disappear before
    // verification.
    return sameClaim(a.summary, b.summary, CLAIM_POLICY.fileLevel)
  }

  if (la !== lb) {
    // Only a cleanup helper declared at line N and used at line N+1 may merge
    // across lines. Require two shared non-generic tokens and cleanup on both
    // sides so a convention violation or a correctness bug stays separate.
    const adjacent = Math.abs(la - lb) === 1
    if (!adjacent || (ka !== undefined && ka !== "cleanup") || (kb !== undefined && kb !== "cleanup")) return false
    const ta = summaryTokens(a.summary)
    const tb = summaryTokens(b.summary)
    let specific = 0
    for (const t of ta) if (tb.has(t) && !GENERIC_WORDS.has(t)) specific++
    // The shared tokens must be specific. Generic cleanup vocabulary
    // ("unused", "parameter", "helper") is excluded above, so two domain
    // tokens are enough to recognize a reworded helper.
    return specific >= 2
  }

  if (!sameClaim(a.summary, b.summary, CLAIM_POLICY.sameLine)) return false
  if (normalizedSummary(a.summary) === normalizedSummary(b.summary)) return true
  // A strong summary paraphrase is the same defect even when the two finders
  // describe different downstream consequences ("the render throws" vs "the
  // handler returns 500"). Weaker summary overlap still needs the failure
  // mechanisms to agree, or two distinct bugs at the same line ("missing
  // response check" vs "missing response await", Jaccard exactly 0.5) would
  // merge. Keep this threshold just above that boundary so 0.5-0.55
  // paraphrases of one defect still merge.
  if (sameClaim(a.summary, b.summary, CLAIM_POLICY.paraphrase)) return true
  if (a.failure_scenario && b.failure_scenario) {
    return sameClaim(a.failure_scenario, b.failure_scenario, CLAIM_POLICY.failureScenario)
  }
  return true
}

/**
 * Merge near-duplicate findings transitively: a new item joins a cluster when
 * it matches any member, not only the representative. The representative keeps
 * the longest failure scenario and the strongest verdict.
 */
function mergeNearDuplicates<T extends RawFinding>(items: T[]): T[] {
  const clusters: T[][] = []
  const verdictStrength = (v: RawFinding["verdict"]): number =>
    v === "CONFIRMED" ? 2 : v === "PLAUSIBLE" ? 1 : 0
  const absorb = (target: T[], item: T) => {
    const rep = target[0]
    target.push(item)
    // A weaker entry must not rewrite a stronger one's claim text: the sweep
    // returns PLAUSIBLE gaps, and its reworded scenario must not be presented
    // under a CONFIRMED verdict. Equal or stronger entries may replace text.
    const upgrades = item.verdict === "CONFIRMED" && rep.verdict !== "CONFIRMED"
    const canReplace =
      upgrades ||
      (verdictStrength(item.verdict) >= verdictStrength(rep.verdict) &&
        (item.failure_scenario?.length ?? 0) > (rep.failure_scenario?.length ?? 0))
    if (canReplace) {
      rep.failure_scenario = item.failure_scenario
      rep.summary = item.summary
      if (item.short_summary) rep.short_summary = item.short_summary
    }
    // A file-level representative otherwise erases the only anchor.
    if (rep.line === undefined && item.line !== undefined) rep.line = item.line
    if (upgrades) rep.verdict = item.verdict
    if (item.category && !rep.category) rep.category = item.category
  }
  for (const item of items) {
    // A paraphrase can match more than one existing cluster. Merge every
    // matching cluster, not only the first, or the same root cause survives
    // twice and consumes two report slots.
    const hits = clusters.filter((group) => group.some((existing) => sameDefect(existing, item)))
    if (hits.length === 0) {
      clusters.push([{ ...item }])
      continue
    }
    const [target, ...rest] = hits
    absorb(target, item)
    for (const other of rest) {
      for (const existing of other) absorb(target, existing)
      clusters.splice(clusters.indexOf(other), 1)
    }
  }
  return clusters.map((group) => group[0])
}

function toFinding(c: RawFinding, kind: "correctness" | "cleanup"): Finding {
  return {
    ...c,
    kind,
    short_summary: c.short_summary ?? shortSummary(c.summary),
  }
}

/** One mapping from a verifier verdict to a kept finding or a refutation. */
function toVerdictFinding(
  c: RawFinding,
  kind: "correctness" | "cleanup",
  verdict: Verdict["verdict"],
  evidence: string,
): Finding {
  return {
    ...toFinding(c, kind),
    verdict: verdict === "REFUTED" ? undefined : verdict,
    evidence,
  } as Finding
}

/**
 * Shared index-plan applier. The candidate dedup and the post-verify
 * synthesis differ only in how they combine a representative with its merged
 * entries; the claim/backfill mechanics are the same.
 */
/** Tolerate a 1-based plan when every index is one past the valid range. */
function normalizeDecisionBase(
  decisions: Decisions["decisions"],
  itemCount: number,
  cap: number,
): Decisions["decisions"] {
  if (decisions.length === 0 || itemCount === 0) return decisions
  let maxIndex = 0
  let hasZero = false
  for (const d of decisions) {
    for (const index of [d.index, ...d.merge]) {
      if (index < 0) return decisions
      if (index === 0) hasZero = true
      if (index > maxIndex) maxIndex = index
    }
  }
  // A zero-based plan must name index 0 somewhere. A plan without it is
  // 1-based only when it is full-length or fills the output cap; a legitimate
  // subset plan can start above 0 and must not be shifted. Do not use
  // Math.max(...indices): a child-supplied merge array is unbounded.
  const fullPlan = maxIndex === itemCount
  const cappedPlan = Number.isFinite(cap) && decisions.length >= cap && maxIndex === cap
  if (hasZero || maxIndex === 0 || maxIndex > itemCount || (!fullPlan && !cappedPlan)) {
    return decisions
  }
  return decisions.map((d) => ({
    index: d.index - 1,
    merge: d.merge.map((i) => i - 1),
  }))
}

function applyIndexPlan<T, R>(
  items: T[],
  decisions: Decisions["decisions"],
  cap: number,
  combine: (item: T, merged: T[]) => R,
  backfill: (item: T) => R,
): { output: R[]; backfilled: number; truncated: boolean } {
  const claimed = new Set<number>()
  const output: R[] = []
  let truncated = false
  const plan = normalizeDecisionBase(decisions, items.length, cap)
  for (const d of plan) {
    if (output.length >= cap) {
      if (d.index >= 0 && d.index < items.length && !claimed.has(d.index)) truncated = true
      continue
    }
    if (d.index < 0 || d.index >= items.length || claimed.has(d.index)) continue
    claimed.add(d.index)
    const merged: T[] = []
    for (const i of d.merge) {
      if (i < 0 || i >= items.length || claimed.has(i)) continue
      claimed.add(i)
      merged.push(items[i])
    }
    output.push(combine(items[d.index], merged))
  }
  let backfilled = 0
  for (let i = 0; i < items.length; i++) {
    if (claimed.has(i)) continue
    if (output.length >= cap) {
      truncated = true
      break
    }
    output.push(backfill(items[i]))
    backfilled++
  }
  return { output, backfilled, truncated }
}

/**
 * Apply index-based dedup decisions before verification. The representative
 * keeps correctness priority, then prefers the most concrete failure scenario;
 * unclaimed candidates are backfilled so the synthesizer cannot silently drop
 * a non-duplicate.
 */
function applyCandidateDedup<T extends RawFinding & { kind: "correctness" | "cleanup" }>(
  items: T[],
  report: Decisions,
): T[] {
  const { output } = applyIndexPlan(
    items,
    report.decisions,
    Number.POSITIVE_INFINITY,
    (item, merged) => {
      const candidates = [item, ...merged]
      // A cleanup candidate must never absorb a correctness candidate just
      // because its scenario is longer: that would downgrade the merged claim
      // before verification and let the report cap cut a real bug first.
      const representative = candidates.sort(
        (a, b) =>
          (a.kind === "correctness" ? 0 : 1) - (b.kind === "correctness" ? 0 : 1) ||
          (b.failure_scenario?.length ?? 0) - (a.failure_scenario?.length ?? 0),
      )[0]
      if (representative.line !== undefined) return representative
      const line = candidates.find((c) => c.line !== undefined)?.line
      return line === undefined ? representative : { ...representative, line }
    },
    (item) => item,
  )
  return output
}

/** Apply index-based merge/rank decisions from the synthesizer child. */
function applyDecisions(
  ranked: Finding[],
  report: Decisions,
  cap: number,
): { findings: Finding[]; backfilled: number; truncated: boolean } {
  const { output, backfilled, truncated } = applyIndexPlan(
    ranked,
    report.decisions,
    cap,
    (c, merged) => {
      // If a merged duplicate is the one the verifier confirmed, its text is
      // the verified claim. Upgrading the representative's text while keeping
      // the representative's unverified wording presents unverified prose as
      // confirmed, so use the confirmed entry's claim.
      const confirmed = merged.find((m) => m.verdict === "CONFIRMED")
      const source = c.verdict === "CONFIRMED" || !confirmed ? c : confirmed
      const verdict = confirmed ? "CONFIRMED" : c.verdict
      // A file-level representative would otherwise erase the only anchor a
      // merged finding carried. Resolve the anchor before computing the
      // "also at" list, or the inherited line is both the finding's own
      // location and an additional location.
      const line = c.line ?? merged.find((m) => m.file === c.file && m.line !== undefined)?.line
      const anchored = line === undefined ? c : { ...c, line }
      const alsoLocations = [...new Set(merged.map(location).filter((l) => l !== location(anchored)))]
      const also = alsoLocations.length > 0 ? ` [same root cause also at: ${alsoLocations.join(", ")}]` : ""
      return {
        ...anchored,
        summary: source.summary + also,
        failure_scenario: source.failure_scenario,
        ...(source.short_summary !== undefined ? { short_summary: source.short_summary } : {}),
        verdict,
      }
    },
    (c) => ({ ...c }),
  )
  return { findings: output, backfilled, truncated }
}

/** The deterministic fallback: exact-claim dedup, keep verified order, cap. */
function deterministicReport(
  ranked: Finding[],
  cap: number,
  level: Level,
): { findings: Finding[]; summary: string; truncated: boolean } {
  const { novel } = dedupeBy(ranked, dedupKey318)
  const findings = novel.slice(0, Number.isFinite(cap) ? cap : undefined).map((c) => ({ ...c }))
  const summary = `${pluralize(findings.length, "finding")} survived verification (${level}-effort review).`
  return { findings, summary, truncated: Number.isFinite(cap) && novel.length > cap }
}

/**
 * One global gate for every child-agent call. Without it, the streaming path
 * launches every finder at once and each finder nests its own `mapLimit`, so
 * in-flight agents become finders × concurrency. Verifier calls get priority
 * over not-yet-started finders so streaming still overlaps find and verify
 * instead of degrading to a barrier.
 */
function limitRunner(runner: AgentRunner, limit: number): AgentRunner {
  let active = 0
  const high: Array<() => void> = []
  const low: Array<() => void> = []
  const acquire = (priority: boolean): Promise<void> =>
    new Promise((resolve) => {
      const grant = () => {
        active++
        resolve()
      }
      if (active < limit) {
        grant()
        return
      }
      ;(priority ? high : low).push(grant)
    })
  const release = () => {
    active--
    const next = high.shift() ?? low.shift()
    if (next) next()
  }
  return async (req) => {
    if (req.signal?.aborted) return null
    await acquire(req.role !== "finder")
    try {
      if (req.signal?.aborted) return null
      return await runner(req)
    } finally {
      release()
    }
  }
}

/** The angle slug the output contract expects for a finder's findings. */
function categoryFor(f: Finder): string {
  if (f.kind === "correctness") return "correctness"
  if (f.label === "cleanup" || f.label.startsWith("angles-")) return "cleanup"
  return f.label
}

const CLEANUP_LABELS = [
  "reuse",
  "simplification",
  "efficiency",
  "altitude",
  "conventions",
  "dead-code",
  "duplication",
  "readability",
  "performance",
  "maintainability",
]

/**
 * A budget-grouped finder mixes correctness and cleanup lenses, so its
 * finder-level kind is not the kind of every candidate. The group carries the
 * lens list; a candidate's `category` is the lens slug the prompt asked for.
 * This is attribution from the actual group, not a global slug heuristic.
 */
/** Normalize a model-provided category before comparing it to a lens label. */
function categorySlug(category: string): string {
  return category.trim().toLowerCase()
}

function kindFor(f: Finder, c: RawFinding): "correctness" | "cleanup" {
  // The candidate schema carries the producing lens class. Trust it only on a
  // mixed-lens finder; a single-lens finder's own kind wins, so a correctness
  // finder cannot relabel a crash as cleanup (and rank it last).
  if (!f.multiLens) return f.kind
  if (c.kind) return c.kind
  // Attribute from the actual group's lens list, not a global slug guess. A
  // model may capitalize or pad the slug, so compare normalized forms.
  if (c.category && f.lenses) {
    const category = categorySlug(c.category)
    const lens = f.lenses.find((l) => categorySlug(l.label) === category)
    if (lens) return lens.kind
  }
  // A cleanup slug such as `dead-code` may not be one of this group's lens
  // labels (the merged v2.1.221 finder folds several lens sets together).
  // Recognize the shared cleanup vocabulary before falling back to the mixed
  // finder's own (correctness) kind. An invented slug is not a licence to claim
  // bug priority; it takes the same unattributed fallback below.
  if (c.category) {
    const slug = categorySlug(c.category)
    if (slug === "correctness") return "correctness"
    if (slug === "cleanup" || CLEANUP_LABELS.includes(slug)) return "cleanup"
  }
  // No attribution on a mixed-lens candidate. Defaulting to the aggregate kind
  // is always "correctness" for a mixed group, which lets a cleanup finding
  // outrank a real bug under the report cap. A candidate without a known lens
  // cannot claim correctness priority; use the unanimous lens when the group
  // has one, otherwise rank it as cleanup.
  if (f.lenses && f.lenses.every((l) => l.kind === "correctness")) return "correctness"
  return "cleanup"
}

/** A sweep candidate has only its category slug, not a producing Finder. */
function kindForCategory(category: string | undefined): "correctness" | "cleanup" {
  // A sweep candidate has no producing lens. Only an explicit `correctness`
  // slug may claim bug priority; an unattributed or invented slug falls back
  // to cleanup, mirroring kindFor().
  if (category === undefined) return "cleanup"
  return categorySlug(category) === "correctness" ? "correctness" : "cleanup"
}

function buildFinders(cell: Cell, budget?: number): Finder[] {
  // Read and split the base corpus lazily: the merged wf221 cleanup finder uses
  // its own corpus, so an extended correctness cell would otherwise load and
  // split the base angles only to discard them.
  let baseTexts: string[] | undefined
  const base = (): string[] =>
    (baseTexts ??= BASE_ANGLES().split(/\n(?=### )/))
  const extended = cell.correctnessAngles >= 5
  const angleTexts = extended ? EXTENDED_ANGLES().split(/\n(?=### )/) : base()
  const correctnessTexts = angleTexts.slice(0, extended ? 5 : 3)
  const labels = ["angle-A", "angle-B", "angle-C", "angle-D", "angle-E"]
  const correctnessFinders: Finder[] = correctnessTexts.map((text, i) => ({
    label: labels[i] ?? `angle-${i}`,
    kind: "correctness",
    text,
    cap: cell.perAngle,
    lenses: [{ label: labels[i] ?? `angle-${i}`, kind: "correctness" }],
  }))

  if (cell.cleanupMode === "merged") {
    return [
      ...correctnessFinders,
      {
        label: "cleanup",
        kind: "cleanup",
        text: CLEANUP_TEXT_221(),
        cap: finderCap(cell),
        merged: true,
        lenses: CLEANUP_LABELS.slice(0, cell.cleanupAngles).map((label) => ({ label, kind: "cleanup" as const })),
      },
    ]
  }

  // v2.1.162's cleanup set is four lenses (no conventions finder); the
  // current recipes add a fifth conventions finder.
  const cleanupTexts =
    cell.cleanupLenses === "162" ? CLEANUP_ANGLES_162().split(/\n(?=### )/) : base().slice(3)
  const cleanupFinders: Finder[] = cleanupTexts.map((text, i) => {
    const label = CLEANUP_LABELS[i] ?? `cleanup-${i}`
    return {
      label,
      kind: "cleanup",
      text,
      cap: cell.perAngle,
      lenses: [{ label, kind: "cleanup" }],
    }
  })

  const all = [...correctnessFinders, ...cleanupFinders]
  if (budget === undefined || budget >= all.length) return all

  // Qs(e,n): the prompt asks for "about Y finder subagents (min 2, max 8)".
  // A deterministic engine has to choose the grouping: distribute the lenses
  // round-robin so every finder sees a mix of correctness and cleanup work.
  const count = Math.max(2, Math.min(8, Math.trunc(budget)))
  const groups: Finder[][] = Array.from({ length: Math.min(count, all.length) }, () => [])
  all.forEach((f, i) => groups[i % groups.length].push(f))
  return groups.map((group, i) => {
    const mixed = group.some((g) => g.kind === "correctness") && group.some((g) => g.kind === "cleanup")
    return {
      label: `angles-${i + 1}`,
      kind: group.some((g) => g.kind === "correctness") ? "correctness" : "cleanup",
      text: group.map((g) => g.text).join("\n"),
      // A grouped finder carries every lens it folded in; keeping only
      // cell.perAngle would throw away the capacity of the other lenses.
      cap: group.reduce((sum, g) => sum + g.cap, 0),
      merged: true,
      multiLens: mixed || group.length > 1,
      lenses: group.flatMap((g) => g.lenses ?? [{ label: g.label, kind: g.kind }]),
    }
  })
}

export async function runReview(opts: EngineOptions): Promise<EngineResult> {
  const { cell, scope, level } = opts
  const concurrency = Math.max(1, opts.concurrency ?? 8)
  // Every role shares this gate; mapLimit below is only a scheduling hint.
  const runner = limitRunner(opts.runner, concurrency)
  const block = scopeBlock(scope)
  const fileIndex = makeFileIndex(scope)
  const warnings: string[] = []
  const stats: EngineStats = {
    finders: 0,
    candidates: 0,
    verifierAgents: 0,
    verified: 0,
    refuted: 0,
    dupes: 0,
    budgetDropped: 0,
    reported: 0,
    finderFailures: 0,
  }
  let partial = false
  const emit = (e: EngineEvent) => opts.onEvent?.(e)

  const finders = buildFinders(cell, opts.finderBudget)
  stats.finders = finders.length

  let cancelled = false
  const aborted = () => {
    if (opts.signal?.aborted === true && !cancelled) {
      cancelled = true
      partial = true
      warnings.push("review was cancelled before every phase completed")
      emit({ type: "warning", message: "review cancelled" })
    }
    return opts.signal?.aborted === true
  }

  /** Shared finder/sweep candidate normalisation and truncation warnings. */
  const acceptCandidates = (
    value: unknown,
    cap: number,
    label: string,
  ): { candidates: RawFinding[]; partial: boolean } | null => {
    const parsed = asCandidatesResult(value, cap)
    if (parsed === null) return null
    let incomplete = false
    if (parsed.dropped > 0) {
      warnings.push(`${label} dropped ${pluralize(parsed.dropped, "malformed candidate")}`)
      incomplete = true
    }
    const candidates = parsed.candidates.slice(0, cap)
    if (candidates.some((c) => c.failure_scenario === STEP_LIMIT_PLACEHOLDER)) {
      warnings.push(`${label} was recovered from its step-limited summary; some failure scenarios are missing`)
      incomplete = true
    }
    return { candidates, partial: incomplete }
  }

  const runFinder = async (f: Finder): Promise<RawFinding[]> => {
    if (aborted()) return []
    const value = await runner({
      role: "finder",
      label: f.label,
      phase: "Find",
      prompt: finderPrompt({
        label: f.label,
        scope: block,
        angleText: f.text,
        cap: f.cap,
        kind: f.kind,
        merged: f.merged,
        multiLens: f.multiLens,
        lenses: f.lenses,
      }),
      agent: AGENT_IDS.finder,
      schemaName: "candidates",
      signal: opts.signal,
    })
    const accepted = acceptCandidates(value, f.cap, `finder ${f.label}`)
    if (accepted === null) {
      stats.finderFailures = (stats.finderFailures ?? 0) + 1
      warnings.push(`finder ${f.label} returned no usable structured result; treated as zero candidates`)
      partial = true
      emit({ type: "warning", message: `finder ${f.label} returned no usable result` })
      return []
    }
    if (accepted.partial) partial = true
    const capped = accepted.candidates.map((c) => {
      // A grouped finder mixes lenses, so its aggregate kind cannot stand in
      // for a candidate's missing category. Prefer the candidate's own kind;
      // leave a mixed finder's category unset rather than mislabelling a
      // cleanup finding as correctness.
      // A single-lens finder's documented slug is the angle that produced the
      // finding; the candidate's coarse kind is only a fallback for a grouped
      // finder, where no single lens owns the finding.
      const category = c.category ?? (f.multiLens ? c.kind : categoryFor(f))
      return {
        ...c,
        file: canonFile(c.file, fileIndex),
        ...(category ? { category } : {}),
      }
    })
    emit({ type: "finder", label: f.label, candidates: capped.length })
    return capped
  }

  // One source for each verifier bias: the ladder follows the cell's verify
  // mode; the recall sentence is added for xhigh/max even though those cells
  // keep the 3-state ladder.
  const recallLadder = cell.verify === "recall"
  const recallSentence = level === "xhigh" || level === "max"

  const verifyOne = async (
    c: RawFinding,
    kind: "correctness" | "cleanup",
    recallBiased: boolean,
    addRecallSentence: boolean,
  ): Promise<Finding | null> => {
    if (aborted()) return null
    stats.verifierAgents++
    const value = await runner({
      role: "verifier",
      label: `verify:${c.file.split("/").pop()}`,
      phase: "Verify",
      prompt: verifierPrompt({
        scope: block,
        candidate: c,
        recallBiased,
        // Both deep multi-agent prompts describe a recall-biased 3-state
        // verifier. Omitting the sentence made xhigh verifiers use the strict
        // precision ladder and refute genuine state-dependent bugs.
        recallSentence: addRecallSentence,
      }),
      agent: AGENT_IDS.verifier,
      schemaName: "verdict",
      signal: opts.signal,
    })
    const verdict = asVerdict(value)
    if (!verdict) {
      warnings.push(`verifier for ${location(c)} returned no usable verdict; candidate dropped`)
      partial = true
      emit({ type: "warning", message: `verifier failed for ${location(c)}` })
      return null
    }
    if (verdict.evidence === NO_EVIDENCE) {
      warnings.push(`verifier for ${location(c)} returned a verdict without evidence; kept as ${verdict.verdict}`)
      partial = true
    }
    return toVerdictFinding(c, kind, verdict.verdict, verdict.evidence)
  }

  const verifyGroups = async (candidates: Array<RawFinding & { kind: "correctness" | "cleanup" }>): Promise<Finding[]> => {
    const byLoc = new Map<string, Array<RawFinding & { kind: "correctness" | "cleanup" }>>()
    for (const c of candidates) {
      const key = location(c)
      const list = byLoc.get(key) ?? []
      list.push(c)
      byLoc.set(key, list)
    }
    const groups = [...byLoc.values()]
    stats.verifierAgents += groups.length
    const out = await mapLimit(groups, concurrency, async (group) => {
      if (aborted()) return []
      const value = await runner({
        role: "verifier",
        label: `verify:${group[0].file.split("/").pop()}(${group.length})`,
        phase: "Verify",
        prompt: groupVerifierPrompt({
          scope: block,
          group,
          recallBiased: recallLadder,
          // xhigh/max grouped verifiers must carry the same recall sentence as
          // the per-candidate path, or the strict ladder refutes reachable
          // state-dependent bugs only in grouped mode.
          recallSentence,
        }),
        agent: AGENT_IDS.verifier,
        schemaName: "groupVerdicts",
        signal: opts.signal,
      })
      const verdicts = asGroupVerdicts(value, group.length)
      if (!verdicts || verdicts.length === 0) {
        warnings.push(`group verifier for ${location(group[0])} returned no usable verdicts; ${pluralize(group.length, "candidate")} dropped`)
        partial = true
        return []
      }
      const byIdx = new Map(verdicts.map((v) => [v.index, v]))
      const noEvidence = verdicts.filter((v) => v.evidence === NO_EVIDENCE).length
      if (noEvidence > 0) {
        warnings.push(
          `group verifier for ${location(group[0])} returned ${pluralize(noEvidence, "verdict")} without evidence; kept with a placeholder`,
        )
        partial = true
      }
      const missing = group.filter((_, i) => !byIdx.has(i)).length
      if (missing > 0) {
        // An empty or partially indexed result is an agent failure, not a
        // clean verification: say so instead of silently dropping candidates.
        warnings.push(
          `group verifier for ${location(group[0])} returned ${verdicts.length}/${group.length} usable verdicts; ${pluralize(missing, "candidate")} dropped`,
        )
        partial = true
      }
      return group.flatMap((c, i) => {
        const v = byIdx.get(i)
        if (!v) return []
        return [toVerdictFinding(c, c.kind, v.verdict, v.evidence)]
      })
    })
    return out.flat()
  }

  // ---------------------------------------------------------------- find
  emit({ type: "phase", phase: "Find" })
  let verified: Finding[] = []

  if (cell.streaming) {
    // v2.1.162: no barrier. Each finder's candidates are deduped against the
    // shared `seen` map and verified immediately, while other finders run.
    const seen = new Set<string>()
    let verifySlots = cell.verifyBudget ?? Number.POSITIVE_INFINITY
    let budgetWarning = false
    await Promise.all(
      finders.map(async (f) => {
        const candidates = await runFinder(f)
        stats.candidates += candidates.length
        const deduped = dedupeBy(candidates, dedupKey162, seen, () => {
          if (verifySlots <= 0) {
            stats.budgetDropped++
            if (!budgetWarning) {
              budgetWarning = true
              warnings.push(
                `verifier budget of ${cell.verifyBudget} exhausted; remaining candidates were left unverified`,
              )
              partial = true
            }
            return false
          }
          verifySlots--
          return true
        })
        stats.dupes += deduped.dupes
        const novel = deduped.novel.map((c) => ({ ...c, kind: kindFor(f, c) }))
        const results = await mapLimit(novel, concurrency, (c) =>
          verifyOne(c, c.kind, recallLadder, recallSentence),
        )
        verified.push(...results.filter((x): x is Finding => x !== null))
      }),
    )
  } else {
    const finderOutputs = await mapLimit(finders, concurrency, async (f) => ({ finder: f, candidates: await runFinder(f) }))
    for (const o of finderOutputs) stats.candidates += o.candidates.length
    const pooled: Array<RawFinding & { kind: "correctness" | "cleanup" }> = []
    if (cell.verify === "grouped") {
      // v2.1.221: grouping, not dedup. Every candidate keeps its own verdict.
      for (const o of finderOutputs) for (const c of o.candidates) pooled.push({ ...c, kind: kindFor(o.finder, c) })
      verified = await verifyGroups(pooled)
    } else {
      // v2.1.318 barrier: dedup then one verifier per candidate. The reference
      // model dedups candidates before spawning verifiers. Exact duplicates are
      // merged here; paraphrases are deliberately verified first, because a
      // token heuristic that merges two distinct defects at one line means the
      // second bug is never verified or reported. The post-verify
      // merge/synthesizer applies the semantic criterion.
      const raw: Array<RawFinding & { kind: "correctness" | "cleanup" }> = []
      for (const o of finderOutputs) for (const c of o.candidates) raw.push({ ...c, kind: kindFor(o.finder, c) })
      let candidatePool = raw
      if (opts.semanticMerge && candidatePool.length > 1) {
        emit({ type: "phase", phase: "Dedup" })
        const value = await runner({
          role: "synthesize",
          label: "dedup",
          phase: "Dedup",
          prompt: candidateDedupPrompt({ level, candidates: candidatePool, diffText: scope.diffText }),
          agent: AGENT_IDS.synthesize,
          schemaName: "decisions",
          signal: opts.signal,
        })
        const report = asDecisions(value)
        if (report) {
          const before = candidatePool.length
          candidatePool = applyCandidateDedup(candidatePool, report)
          stats.dupes += before - candidatePool.length
          // The model's decisions are authoritative, exactly as in the
          // reference.
          pooled.push(...candidatePool)
        } else {
          // The semantic merge was explicitly requested; when its child fails,
          // fall back to the same paraphrase merge the deterministic path uses
          // instead of verifying the same defect once per finder.
          warnings.push("candidate dedup returned no usable decisions; deterministic merge used")
          partial = true
          const merged = mergeNearDuplicates(candidatePool)
          stats.dupes += candidatePool.length - merged.length
          pooled.push(...merged)
        }
      } else {
        const deduped = dedupeBy(candidatePool, dedupKey318)
        stats.dupes += deduped.dupes
        pooled.push(...deduped.novel)
      }
      const results = await mapLimit(pooled, concurrency, (c) =>
        verifyOne(c, c.kind, recallLadder, recallSentence),
      )
      verified = results.filter((x): x is Finding => x !== null)
    }
  }

  const kept = verified.filter((c) => c.verdict !== undefined)
  const refuted = verified.filter((c) => c.verdict === undefined)
  stats.verified = verified.length
  stats.refuted = refuted.length
  emit({ type: "verify", kept: kept.length, refuted: refuted.length })

  // ---------------------------------------------------------------- sweep
  if (cell.sweep && !aborted()) {
    emit({ type: "phase", phase: "Sweep" })
    // Refuted claims must stay visible to the sweep. Omitting them lets a
    // false positive return as a fresh PLAUSIBLE finding with no new evidence.
    const known = [
      ...kept.map((c) => `${renderedLocation(c)} — ${c.summary}`),
      ...refuted.map(
        (c) => `${renderedLocation(c)} — ${c.summary} (refuted — do not re-report without new evidence)`,
      ),
    ]
    const value = await runner({
      role: "sweep",
      label: "sweep",
      phase: "Sweep",
      prompt: sweepPrompt({ scope: block, known, cap: cell.sweepCap }),
      agent: AGENT_IDS.sweep,
      schemaName: "candidates",
      signal: opts.signal,
    })
    const accepted = acceptCandidates(value, cell.sweepCap, "sweep")
    if (accepted === null) {
      warnings.push("sweep returned no usable structured result; no gap candidates added")
      partial = true
    } else {
      if (accepted.partial) partial = true
      const knownFindings = [...kept, ...refuted]
      // Compare the exact claim only. A reworded sweep gap at a known line is
      // often a distinct defect, so the paraphrase heuristic can silently
      // discard the gap the sweep exists to surface.
      const exactKnown = new Set(knownFindings.map(dedupKey318))
      const novel = accepted.candidates
        .map((c) => {
          const kind = c.kind ?? kindForCategory(c.category)
          const category = c.category ?? (kind === "cleanup" ? "cleanup" : "correctness")
          return {
            ...c,
            file: canonFile(c.file, fileIndex),
            category,
            kind,
          }
        })
        .filter((c) => {
          const line = lineOf(c)
          const refutedSpot = refuted.some((k) => {
            if (k.file !== c.file) return false
            const refutedLine = lineOf(k)
            // A file-level refuted claim covers the whole file; a line claim
            // only covers its own line. A candidate without a line is not
            // covered by a line-scoped refutation, even when the wording is
            // close: a distinct bug with similar wording must still reach the
            // report.
            if (refutedLine !== undefined && refutedLine !== line) return false
            // Summary vocabulary alone is not enough: two distinct defects at
            // one line can share the nouns. Require the failure mechanism to
            // match too, or a genuine sweep gap is discarded as the refuted
            // false positive it is not.
            return (
              sameClaim(k.summary, c.summary, CLAIM_POLICY.refuted) &&
              sameClaim(k.failure_scenario, c.failure_scenario, CLAIM_POLICY.refuted)
            )
          })
          if (refutedSpot) {
            stats.dupes++
            return false
          }
          const key = dedupKey318(c)
          if (exactKnown.has(key)) {
            stats.dupes++
            return false
          }
          exactKnown.add(key)
          return true
        })
      stats.candidates += accepted.candidates.length
      emit({ type: "sweep", candidates: novel.length })
      if (novel.length > 0) {
        // The reference's Phase 3 sweep runs after verification and its
        // "additional candidates" go straight to the report; they are not
        // re-verified. A second gate here would drop the gaps the sweep exists
        // to catch. Mark them PLAUSIBLE so ranking still prefers confirmed
        // findings unless the synthesizer judges otherwise.
        const swept = novel.map((c) => ({
          ...toFinding(c, c.kind),
          verdict: "PLAUSIBLE" as const,
        }))
        kept.push(...swept)
      }
    }
  }

  aborted()
  const surviving = kept
    .filter((c) => c.verdict !== undefined)
    .map((c) => ({ ...c, verdict: c.verdict as "CONFIRMED" | "PLAUSIBLE" }))

  const limit = opts.statedLimit ?? cell.maxFindings
  const cap = limit === "all" ? Number.POSITIVE_INFINITY : limit

  if (surviving.length === 0) {
    const result: EngineResult = {
      level,
      summary: partial
        ? "No findings survived verification, but at least one review agent failed — this is not a complete review."
        : "No findings survived verification.",
      findings: [],
      refuted: refuted.map((c) => ({ file: c.file, line: c.line, summary: c.summary })),
      stats: { ...stats, reported: 0 },
      partial,
      warnings,
      cell: cell.id,
    }
    emit({ type: "stats", stats: result.stats })
    return result
  }

  // ---------------------------------------------------------------- synthesize
  // The reference model merges and ranks the verified findings semantically,
  // with the diff in context. Only run the deterministic token merge when no
  // synthesizer will see the findings; otherwise it would override the
  // synthesizer's decisions and can collapse two distinct defects.
  // --no-semantic-merge must disable the workflow synthesizer too, not only
  // the v2.1.318 merge pass.
  const synthesisEnabled = opts.semanticMerge !== false
  const willSynthesize =
    synthesisEnabled &&
    (cell.synthesis !== "none" || (opts.semanticMerge === true && surviving.length > 1))
  const mergeBase = willSynthesize ? surviving : mergeNearDuplicates(surviving)
  stats.dupes += surviving.length - mergeBase.length
  const rank = (c: Finding) => (c.kind === "cleanup" ? 2 : 0) + (c.verdict === "PLAUSIBLE" ? 1 : 0)
  // Code-unit comparison, not localeCompare: the report order must not change
  // with the host's locale or ICU build.
  const compare = (a: string, b: string): number => (a < b ? -1 : a > b ? 1 : 0)
  const ranked = mergeBase.slice().sort(
    (a, b) =>
      rank(a) - rank(b) ||
      compare(location(a), location(b)) ||
      compare(a.summary, b.summary) ||
      compare(a.failure_scenario, b.failure_scenario),
  )

  let findings: Finding[]
  let summary: string
  let truncatedByCap = false

  /**
   * Every synthesis-failure path returns the same ranked, unmerged list. Keep
   * the cap accounting in one place so a fallback cannot silently drop the
   * truncation flag or the dropped-count handling.
   */
  const unmergedFallback = (summaryText: string): void => {
    findings = ranked.slice(0, Number.isFinite(cap) ? cap : undefined).map((c) => ({ ...c }))
    truncatedByCap = Number.isFinite(cap) && ranked.length > cap
    summary = summaryText
  }

  /** Shared by wf221 synthesis and the v2.1.318 semantic-merge equivalent. */
  const runIndexSynthesis = async (
    label: "synthesize" | "merge",
  ): Promise<{ findings: Finding[]; summary: string; truncated: boolean } | null> => {
    emit({ type: "phase", phase: "Synthesize" })
    const value = await runner({
      role: "synthesize",
      label,
      phase: "Synthesize",
      prompt: synthPromptIndex({
        level,
        ranked,
        maxFindings: Number.isFinite(cap) ? cap : ranked.length,
        diffText: scope.diffText,
      }),
      agent: AGENT_IDS.synthesize,
      schemaName: "decisions",
      signal: opts.signal,
    })
    const report = asDecisions(value)
    if (!report) return null
    if (report.truncated) {
      // The decision list was capped before the engine saw it. Backfilling the
      // tail keeps the findings, but some merges/rank decisions are missing;
      // do not present the report as complete.
      warnings.push("synthesis decisions were truncated at the tool cap; some merges may be missing")
      partial = true
    }
    const applied = applyDecisions(ranked, report, cap)
    return {
      findings: applied.findings,
      summary:
        report.summary +
        (applied.backfilled > 0
          ? ` (${pluralize(applied.backfilled, "additional verified finding")} appended unmerged.)`
          : ""),
      truncated: applied.truncated || report.truncated === true,
    }
  }

  const applyIndexSynthesis = (
    synthesized: { findings: Finding[]; summary: string; truncated: boolean } | null,
    warning: string,
    fallback: () => void,
  ): void => {
    if (!synthesized) {
      warnings.push(warning)
      partial = true
      fallback()
      return
    }
    findings = synthesized.findings
    summary = synthesized.summary
    truncatedByCap = synthesized.truncated
  }

  if (synthesisEnabled && cell.synthesis === "index") {
    applyIndexSynthesis(
      await runIndexSynthesis("synthesize"),
      "synthesis returned no usable decisions; returning ranked findings unmerged",
      () =>
        unmergedFallback(
          "Synthesis step was skipped or its decisions were unusable — returning verified findings ranked, unmerged.",
        ),
    )
  } else if (synthesisEnabled && cell.synthesis === "text") {
    emit({ type: "phase", phase: "Synthesize" })
    const value = await runner({
      role: "synthesize",
      label: "synthesize",
      phase: "Synthesize",
      prompt: synthPromptText({
        level,
        ranked,
        maxFindings: Number.isFinite(cap) ? cap : ranked.length,
        diffText: scope.diffText,
      }),
      agent: AGENT_IDS.synthesize,
      schemaName: "report",
      signal: opts.signal,
    })
    // "all" means the synthesizer was asked for every survivor, so the
    // normalizer must not silently cap the report below that asked-for count.
    const report = asReport(value, Number.isFinite(cap) ? cap : ranked.length)
    if (!report) {
      warnings.push("synthesis returned no usable report; returning ranked findings unmerged")
      partial = true
      unmergedFallback("Synthesis step was skipped or failed — returning verified findings unmerged.")
    } else {
      if ((report.dropped ?? 0) > 0) {
        warnings.push(
          `synthesis dropped ${pluralize(report.dropped ?? 0, "malformed finding")}; the report may be incomplete`,
        )
        partial = true
      }
      if (report.truncated) {
        warnings.push("synthesis report was truncated at the normalizer cap; the report may be incomplete")
        partial = true
      }
      if (report.findings.some((f) => f.failure_scenario === STEP_LIMIT_PLACEHOLDER)) {
        warnings.push("synthesis was recovered from a step-limited summary; some failure scenarios are missing")
        partial = true
      }
      if (report.findings.length === 0) {
        // An empty report with verified survivors is not a merge decision:
        // there is no replacement entry. Returning it would present a
        // confirmed defect as "No findings." with a complete status.
        warnings.push("synthesis returned an empty report; returning verified findings unmerged")
        partial = true
        unmergedFallback("Synthesis returned an empty report — returning verified findings unmerged.")
      } else {
        let unmatched = 0
        const claimed = new Set<number>()
        const matchIndex = (n: RawFinding): number => {
          // A text synthesizer re-emits findings but has no index data. An
          // exact claim, or a report entry anchored to the same file and line
          // as a verified finding, is that finding even when reworded. The
          // emitted text remains the verified survivor's, so a reworded or
          // merged entry cannot attach a CONFIRMED verdict to invented text.
          const anchor = lineOf(n)
          const exact = ranked.findIndex(
            (r, i) =>
              !claimed.has(i) &&
              r.file === n.file &&
              (anchor === undefined || lineOf(r) === undefined || lineOf(r) === anchor) &&
              normalizedSummary(r.summary) === normalizedSummary(n.summary),
          )
          if (exact !== -1) return exact
          if (anchor !== undefined) {
            // Same file/line is an anchor, not proof that the claim is the
            // same. Without shared vocabulary the entry may describe another
            // verified finding at that line; claiming it would emit the wrong
            // text and silently drop the reworded finding. The any-token
            // anchor is safe only when exactly one unclaimed finding sits at
            // that line; with several, fall through to the stronger summary
            // match or mark the entry unmatched.
            const sameLine = ranked
              .map((r, i) => ({ r, i }))
              .filter(({ r, i }) => !claimed.has(i) && r.file === n.file && lineOf(r) === anchor)
            if (
              sameLine.length === 1 &&
              sameClaim(sameLine[0].r.summary, n.summary, CLAIM_POLICY.synthAnchor)
            ) {
              return sameLine[0].i
            }
          }
          return ranked.findIndex(
            (r, i) =>
              !claimed.has(i) &&
              r.file === n.file &&
              sameClaim(r.summary, n.summary, CLAIM_POLICY.synth),
          )
        }
        const emitted: Finding[] = []
        for (const f of report.findings) {
          const normalized = normalizeFinding(f)
          if (!normalized) continue
          // A text synthesizer can copy the `b/` side of a diff header or an
          // absolute path. Canonicalize it the same way as a finder candidate
          // before matching, or the verified finding is dropped as unmatched.
          const n = { ...normalized, file: canonFile(normalized.file, fileIndex) }
          // The text report must re-emit verified findings, not invent new ones.
          const index = matchIndex(n)
          if (index === -1) {
            unmatched++
            continue
          }
          claimed.add(index)
          const match = ranked[index]
          // Emit the verified survivor's claim text: a text synthesizer can
          // invent or distort a summary, and pairing that text with the
          // survivor's CONFIRMED verdict would present it as verified. Keep only
          // the synthesizer's corrected anchor, which does not change the claim.
          // The verified verdict always wins; synthesis cannot upgrade it.
          // The verified anchor also wins: a hallucinated or off-by-N line
          // must not replace the only location the verifier approved.
          emitted.push({
            ...match,
            ...(match.line === undefined && n.line !== undefined ? { line: n.line } : {}),
            verdict: match.verdict ?? f.verdict ?? "PLAUSIBLE",
          } as Finding)
        }
        // Do not backfill findings the synthesizer merged away: a text report
        // has no index/merge data, so an unclaimed survivor may be the second
        // half of a merged pair. Returning only the synthesizer's list is what
        // the reference does; an omitted finding is a model decision, not a
        // defect the orchestrator can safely reconstruct.
        if (emitted.length === 0 && ranked.length > 0) {
          // Every re-emitted entry failed the match. An empty report would
          // render as "No findings." even though verified survivors exist.
          warnings.push(
            "synthesis report did not match any verified finding; returning verified findings unmerged",
          )
          partial = true
          unmergedFallback(
            "Synthesis could not match any verified finding — returning verified findings unmerged.",
          )
        } else {
          // A text report can be truncated by the normalizer before the final
          // cap is applied. Preserve that fact so the engine can record
          // truncatedFrom instead of presenting a shortened list as complete.
          truncatedByCap = report.truncated === true || (Number.isFinite(cap) && emitted.length > cap)
          findings = emitted.slice(0, Number.isFinite(cap) ? cap : undefined)
          if (unmatched > 0) {
            // A reworded or merged entry is indistinguishable from an invented
            // one, so the matching failure may have dropped verified findings.
            // Mark the run incomplete instead of presenting the remainder as a
            // complete review.
            warnings.push(`synthesis reported ${pluralize(unmatched, "finding")} that did not match a verified candidate; dropped`)
            partial = true
          }
          summary = report.summary
        }
      }
    }
  } else if (opts.semanticMerge && ranked.length > 1) {
    // Platform equivalent of the reference model's in-context semantic merge
    // and ranking: a synthesizer child returns merge/rank decisions by index.
    applyIndexSynthesis(
      await runIndexSynthesis("merge"),
      "semantic merge returned no usable decisions; deterministic merge used",
      () => {
        // The warning promises a deterministic merge; applying only the
        // exact-key report would leave paraphrases unmerged.
        const fallback = deterministicReport(mergeNearDuplicates(ranked), cap, level)
        findings = fallback.findings
        summary = fallback.summary
        truncatedByCap = fallback.truncated
      },
    )
  } else {
    // v2.1.318 without the synthesizer: the deterministic equivalent keeps the
    // verified order and merges exact duplicates only.
    const fallback = deterministicReport(ranked, cap, level)
    findings = fallback.findings
    summary = fallback.summary
    truncatedByCap = fallback.truncated
  }
  if (Number.isFinite(cap) && findings.length > cap) truncatedByCap = true

  const result: EngineResult = {
    level,
    summary,
    findings: findings.slice(0, Number.isFinite(cap) ? cap : undefined),
    refuted: refuted.map((c) => ({ file: c.file, line: c.line, summary: c.summary })),
    stats: { ...stats, reported: Math.min(findings.length, Number.isFinite(cap) ? cap : findings.length) },
    partial,
    warnings,
    cell: cell.id,
    // Truncation means the cap cut the emitted report short, not merely that
    // more candidates entered synthesis: a synthesizer that merged 20
    // survivors into 12 under a 15 cap dropped nothing.
    ...(truncatedByCap && Number.isFinite(cap) ? { truncatedFrom: surviving.length } : {}),
  }
  emit({ type: "stats", stats: result.stats })
  return result
}

/** Inline cells produce a prompt, not an engine run. */
export function isInline(cell: Cell): boolean {
  return cell.engine === "inline" || cell.engine === "minimal"
}
