/**
 * Tolerant structured-output parsing.
 *
 * Claude Code constrains subagent output with a JSON schema. OpenCode child
 * sessions return free text, so the reconstruction extracts the first balanced
 * JSON value and validates it against the same shape. Anything that does not
 * validate is treated exactly like a missing agent result in the reference:
 * finder => zero candidates, verifier => candidate dropped, synthesis =>
 * fallback path.
 */
import { positiveLine, truncateCodePoints } from "./finding.ts"
import { SAMPLE_VALUE } from "./samples.ts"

export type RawFinding = {
  file: string
  line?: number
  summary: string
  short_summary?: string
  failure_scenario: string
  category?: string
  /** Producing lens class, carried in the candidate schema (v2.1.221+). */
  kind?: "correctness" | "cleanup"
  verdict?: "CONFIRMED" | "PLAUSIBLE"
}

const VERDICTS = new Set(["CONFIRMED", "PLAUSIBLE", "REFUTED"])

/** Placeholder recorded when a verdict is kept without evidence. The engine
 *  uses the same constant to mark the run partial; keep it shared. */
export const NO_EVIDENCE = "(no evidence provided)"

/** Placeholder the runner writes when a step-limited summary omitted the
 *  failure scenario. The engine uses it to mark the recovered run partial. */
export const STEP_LIMIT_PLACEHOLDER = "not stated in the step-limited summary"

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v)
}

function str(v: unknown): string | undefined {
  return typeof v === "string" && v.trim().length > 0 ? v : undefined
}

function num(v: unknown): number | undefined {
  if (typeof v === "number" && Number.isFinite(v)) return v
  // Models routinely stringify indices ("2"); the tolerant contract accepts
  // an integer-looking string rather than silently dropping that verdict.
  if (typeof v === "string" && /^\d+$/.test(v.trim())) return Number(v.trim())
  return undefined
}

/**
 * Remove backslashes that JSON does not allow before the next character,
 * while preserving every valid escape. A naive regex also eats the second
 * backslash of `\\d` (a valid escaped backslash followed by `d`), corrupting
 * otherwise-valid JSON.
 */
function repairEscapes(s: string): string {
  let out = ""
  for (let i = 0; i < s.length; i++) {
    const ch = s[i]
    if (ch !== "\\") {
      out += ch
      continue
    }
    const next = s[i + 1]
    if (next === undefined) {
      out += ch
      continue
    }
    if (next === "u") {
      // JSON's `\u` escape requires exactly four hex digits. Treat `\u` with
      // any other suffix as an invalid escape and drop only the backslash, or
      // an ordinary Windows path (`C:\users\...`) stays unparseable.
      const hex = s.slice(i + 2, i + 6)
      if (/^[0-9a-fA-F]{4}$/.test(hex)) {
        out += `\\u${hex}`
        i += 5
        continue
      }
      out += next
      i++
      continue
    }
    if ('"\\/bfnrt'.includes(next)) {
      out += ch + next
      i++
      continue
    }
    out += next
    i++
  }
  return out
}

/** Scan at most this many bracket starts before giving up on the fallback. */
const MAX_JSON_SCAN_STARTS = 1000

/**
 * Bound the fallback's total work, not just its attempt count. Each attempt
 * walks the body, so 1000 attempts over a large prose transcript is quadratic.
 */
const MAX_JSON_SCAN_WORK = 2_000_000

/** The array-shaped result keys the child tools return. */
const RESULT_ARRAY_KEYS = ["candidates", "verdicts", "findings", "decisions"] as const

/** One spelling of the structured-result vocabulary for every scanner. */
const RESULT_KEY_PATTERN = `"(?:${RESULT_ARRAY_KEYS.join("|")}|verdict)"\\s*:`

/** The result keys a structured payload must contain. */
function hasResultKey(body: string): boolean {
  return new RegExp(RESULT_KEY_PATTERN).test(body)
}

/** The result objects the child tools are supposed to return. */
function isResultShape(value: unknown): boolean {
  if (!isRecord(value)) return false
  // A grouped-verdict item carries an `index`; it is an element of the
  // `verdicts` array, not a top-level verdict result.
  if ("index" in value) return false
  // A verdict result needs evidence. A finding inside a bare array can also
  // carry a `verdict` field; treating it as a top-level result would return
  // that one item instead of the array the child actually submitted.
  if (typeof value.verdict === "string") {
    // A finding object also carries a verdict field. A top-level verdict result
    // has evidence and none of the finding's required fields.
    if ("file" in value || "summary" in value || "failure_scenario" in value) return false
    return ["evidence", "reason", "justification"].some((key) => typeof value[key] === "string")
  }
  return RESULT_ARRAY_KEYS.some((key) => Array.isArray(value[key]))
}

/**
 * Scan every top-level bracket start and prefer the structured result object.
 * A child may mention `[0]` or `[1]` in prose before its real JSON payload; the
 * first balanced value is not necessarily the answer.
 */
function balancedAt(body: string, start: number): { end: number; parsed: unknown | undefined } | undefined {
  const open = body[start]
  if (open !== "{" && open !== "[") return undefined
  const close = open === "{" ? "}" : "]"
  let depth = 0
  let inString = false
  let escaped = false
  for (let i = start; i < body.length; i++) {
    const ch = body[i]
    if (inString) {
      if (escaped) escaped = false
      else if (ch === "\\") escaped = true
      else if (ch === '"') inString = false
      continue
    }
    if (ch === '"') {
      inString = true
      continue
    }
    if (ch === open) depth++
    else if (ch === close) {
      depth--
      if (depth === 0) return { end: i, parsed: tryParse(body.slice(start, i + 1)) }
    }
  }
  return undefined
}

const RESULT_KEY = new RegExp(RESULT_KEY_PATTERN, "g")

/**
 * The prompt's `Expected shape:` example is a valid result object, so a model
 * that repeats it after its real payload must not replace that payload.
 * Recognize the generated placeholder values rather than preferring the first
 * or last result-shaped object unconditionally: the example may be quoted
 * before or after the answer.
 */
function isSchemaEcho(value: unknown): boolean {
  if (!isRecord(value)) return false
  // The decisions example has no finding placeholders, so the per-item check
  // below cannot see it. Match the generated example exactly.
  if (
    value.summary === SAMPLE_VALUE.summary &&
    Array.isArray(value.decisions) &&
    value.decisions.length === 1 &&
    isRecord(value.decisions[0]) &&
    value.decisions[0].index === SAMPLE_VALUE.index &&
    Array.isArray(value.decisions[0].merge) &&
    value.decisions[0].merge.length === 1 &&
    value.decisions[0].merge[0] === SAMPLE_VALUE.merge
  ) {
    return true
  }
  // The grouped-verdict example keeps `verdict` inside the array rather than
  // at the top level, so the top-level check below misses it too.
  if (
    Array.isArray(value.verdicts) &&
    value.verdicts.length === 1 &&
    isRecord(value.verdicts[0]) &&
    value.verdicts[0].index === SAMPLE_VALUE.index &&
    value.verdicts[0].verdict === SAMPLE_VALUE.verdict &&
    value.verdicts[0].evidence === SAMPLE_VALUE.evidence
  ) {
    return true
  }
  for (const key of RESULT_ARRAY_KEYS) {
    const items = value[key]
    if (!Array.isArray(items) || items.length === 0) continue
    if (
      items.every((item) => {
        if (!isRecord(item)) return false
        // One placeholder field is not proof of an echo: a real finding in a
        // repository that contains `path/to/file.ts` would otherwise be
        // discarded. The generated example carries all three fields; require
        // at least two before treating the item as the sample.
        const matches = [
          item.file === SAMPLE_VALUE.file,
          item.summary === SAMPLE_VALUE.summary,
          item.failure_scenario === SAMPLE_VALUE.failure_scenario,
        ].filter(Boolean).length
        return matches >= 2
      })
    ) {
      return true
    }
  }
  return typeof value.verdict === "string" && value.evidence === SAMPLE_VALUE.evidence
}

/**
 * A model may paraphrase the generated example instead of copying its
 * placeholders. The `Expected shape:` label immediately before the object is
 * the reliable marker in that case.
 */
function isLabeledExample(body: string, brace: number): boolean {
  const before = body.slice(Math.max(0, brace - 80), brace)
  return /(?:expected|required)\s+(?:shape|format|schema)\s*:?\s*[`"']?\s*$/i.test(before)
}

/**
 * Result-key anchored scan. A prose code quote can contain hundreds of
 * brackets (or one unmatched bracket whose scan never terminates), and the
 * generic start-by-start scan would exhaust its attempt budget before reaching
 * the real payload that follows. Every result object must contain one of these
 * keys, so locate those keys first and parse outward from the nearest `{`.
 */
function scanAnchored(body: string): unknown | undefined {
  RESULT_KEY.lastIndex = 0
  let found: unknown | undefined
  const ranges: Array<{ start: number; end: number }> = []
  let match: RegExpExecArray | null
  while ((match = RESULT_KEY.exec(body)) !== null) {
    const brace = body.lastIndexOf("{", match.index)
    if (brace === -1) continue
    // A result key inside an already-parsed result object is a nested item
    // (a group verdict carries `verdict` inside each entry). Do not let that
    // item replace the outer `{verdicts:[...]}` payload.
    if (ranges.some((range) => range.start < brace && brace < range.end)) continue
    const balanced = balancedAt(body, brace)
    // A child may quote the prompt's schema example before or after its real
    // payload. Keep the last real result; fall back to an echoed example only
    // when it is the only result-shaped object.
    if (balanced?.parsed !== undefined && isResultShape(balanced.parsed)) {
      ranges.push({ start: brace, end: balanced.end })
      const echo = isSchemaEcho(balanced.parsed) || isLabeledExample(body, brace)
      if (!echo || found === undefined) found = balanced.parsed
    }
  }
  return found
}

function scanBalanced(body: string): unknown | undefined {
  const anchored = scanAnchored(body)
  // An echoed schema example is not an answer. Keep scanning the body for a
  // real payload that follows it; fall back to the echo only if none exists.
  if (anchored !== undefined && !isSchemaEcho(anchored)) return anchored
  let attempts = 0
  let work = 0
  const values: unknown[] = []
  for (let start = 0; start < body.length; start++) {
    const open = body[start]
    if (open !== "{" && open !== "[") continue
    if (++attempts > MAX_JSON_SCAN_STARTS || work > MAX_JSON_SCAN_WORK) break
    // balancedAt can scan to the end of the body on an unbalanced fragment.
    work += body.length
    const match = balancedAt(body, start)
    if (match === undefined) {
      // This fragment never balances. A later independent fragment can still
      // be the answer (for example a bare array after an unmatched `[` in
      // prose), and the attempt budget bounds the extra scanning.
      continue
    }
    if (match.parsed !== undefined) {
      values.push(match.parsed)
      // Ignore nested starts inside a valid value; only independent
      // top-level fragments can be the child's final result.
      start = match.end
    }
  }
  for (let i = values.length - 1; i >= 0; i--) if (isResultShape(values[i])) return values[i]
  if (anchored !== undefined) return anchored
  // A bare array of finding/verdict objects is the payload for the array
  // schemas. Prefer it over a prose bracket like `[0]` and over an unrelated
  // record; normalizeShape wraps it in the expected key.
  for (let i = values.length - 1; i >= 0; i--) {
    const value = values[i]
    if (Array.isArray(value) && value.some((item) => isRecord(item))) return value
  }
  for (let i = values.length - 1; i >= 0; i--) if (isRecord(values[i])) return values[i]
  for (let i = values.length - 1; i >= 0; i--) if (Array.isArray(values[i])) return values[i]
  return values[0]
}

function parseCandidate(raw: string): unknown | undefined {
  const body = raw.trim()
  if (!body) return undefined
  const direct = tryParse(body)
  if (direct !== undefined) return direct
  const repaired = repairEscapes(body)
  if (repaired !== body) {
    const retried = tryParse(repaired)
    if (retried !== undefined) return retried
    return scanBalanced(repaired)
  }
  return scanBalanced(body)
}

/**
 * Extract a JSON value from child output. Try the whole body, then every
 * fenced block (JSON-labelled first), then a bracket scan. The reference's
 * StructuredOutput tool always returns JSON; this is the text fallback for
 * models that answer in prose, so it must not prefer an arbitrary first fence.
 */
export function extractJson(text: string | undefined | null): unknown | null {
  if (!text) return null
  const body = text.trim()

  // Whole-body JSON is unambiguous unless it is the prompt's own `Expected
  // shape:` example. A child that copies the example verbatim must not be
  // accepted as a real result, so run the same echo check as the bracket scan.
  const direct = tryParse(body)
  if (direct !== undefined && !isSchemaEcho(direct)) return direct

  const fences: Array<{ info: string; body: string }> = []
  const re = /```([^\n`]*)\r?\n([\s\S]*?)```/g
  let match: RegExpExecArray | null
  while ((match = re.exec(body)) !== null) {
    fences.push({ info: (match[1] ?? "").trim().toLowerCase(), body: match[2] ?? "" })
  }
  const ordered = [
    ...fences.filter((f) => f.info === "json" || f.info === ""),
    ...fences.filter((f) => f.info !== "json" && f.info !== ""),
  ]
  const parsedFences: unknown[] = []
  for (const fence of ordered) {
    const body = fence.body.trim()
    if (!body) continue
    // A pasted source listing can be much larger than a result payload. If it
    // has no result key, parsing it would run the fallback bracket scan over
    // every `[` in the listing for no benefit.
    if (body.length > 32_000 && !hasResultKey(body)) continue
    const value = parseCandidate(fence.body)
    if (value !== undefined) parsedFences.push(value)
  }
  // Scan the whole body first: unlike a single fence, it can see a real
  // payload that follows an echoed schema example, and scanAnchored prefers
  // the final result-shaped object. Skip the whole-body fallback for a large
  // prose blob with no result key: it would only run the quadratic bracket
  // scan.
  const scanned = body.length > 32_000 && !hasResultKey(body) ? undefined : parseCandidate(body)
  const scannedIsEcho = scanned !== undefined && isSchemaEcho(scanned)
  if (
    scanned !== undefined &&
    !scannedIsEcho &&
    (isResultShape(scanned) || (Array.isArray(scanned) && scanned.some((item) => isRecord(item))))
  ) {
    return scanned
  }
  // A real bare array can follow an echoed schema example. Prefer that
  // non-echo payload over the echo the anchored scan stopped on.
  const nonEchoFences = parsedFences.filter((value) => !isSchemaEcho(value))
  const shapedFences = nonEchoFences.filter(isResultShape)
  if (shapedFences.length > 0) return shapedFences[shapedFences.length - 1]
  const arrayFences = nonEchoFences.filter(
    (value) => Array.isArray(value) && value.some((item) => isRecord(item)),
  )
  if (arrayFences.length > 0) return arrayFences[arrayFences.length - 1]
  if (scanned !== undefined && !scannedIsEcho) return scanned
  // An echoed example is not an answer. Prefer any non-echo fence; otherwise
  // report no usable JSON so the runner retries the child.
  return nonEchoFences.length > 0 ? nonEchoFences[nonEchoFences.length - 1] : null
}

function tryParse(s: string): unknown | undefined {
  try {
    return JSON.parse(s)
  } catch {
    return undefined
  }
}

export type NormalizeFindingOptions = {
  /** ReportFindings' schema allows empty strings; finder candidates do not. */
  allowEmptyStrings?: boolean
  /** ReportFindings drops a finding with an invalid verdict; engine parsing ignores it. */
  invalidVerdict?: "ignore" | "drop"
  /** Optional collector for caller-specific repair notes. */
  notes?: string[]
  notePrefix?: string
}

/**
 * One normalizer for every finding boundary. `json.ts` uses the defaults for
 * child-agent candidates; `reportfindings.ts` opts into the reference tool's
 * empty-string and invalid-verdict semantics instead of reimplementing the
 * field rules.
 */
export function normalizeFinding(v: unknown, opts: NormalizeFindingOptions = {}): RawFinding | null {
  const prefix = opts.notePrefix ?? "finding"
  const text = opts.allowEmptyStrings
    ? (value: unknown) => (typeof value === "string" ? value : undefined)
    : str
  if (!isRecord(v)) {
    opts.notes?.push(`${prefix} dropped: not an object`)
    return null
  }
  const file = text(v.file)
  const summary = text(v.summary)
  const failure = text(v.failure_scenario)
  if (file === undefined || summary === undefined || failure === undefined) {
    opts.notes?.push(`${prefix} dropped: needs file, summary, and failure_scenario`)
    return null
  }
  const out: RawFinding = { file, summary, failure_scenario: failure }
  const kind = str(v.kind)
  if (kind === "correctness" || kind === "cleanup") out.kind = kind
  else if (v.kind !== undefined) opts.notes?.push(`${prefix}.kind is invalid; omitted`)
  if (v.line !== undefined) {
    const line = positiveLine(v.line)
    if (line !== undefined) out.line = line
    else opts.notes?.push(`${prefix}.line is not a positive integer; omitted`)
  }
  if (v.short_summary !== undefined) {
    const short = text(v.short_summary)
    if (short === undefined) {
      opts.notes?.push(`${prefix}.short_summary is not a string; omitted`)
    } else {
      out.short_summary = truncateCodePoints(short, 60)
      if (out.short_summary !== short) opts.notes?.push(`${prefix}.short_summary truncated to 60 characters`)
    }
  }
  if (v.category !== undefined) {
    const category = text(v.category)
    if (category === undefined) {
      opts.notes?.push(`${prefix}.category is not a string; omitted`)
    } else {
      out.category = truncateCodePoints(category, 40)
      if (out.category !== category) opts.notes?.push(`${prefix}.category truncated to 40 characters`)
    }
  }
  const verdict = str(v.verdict)
  if (verdict === "CONFIRMED" || verdict === "PLAUSIBLE") out.verdict = verdict
  else if (v.verdict !== undefined && opts.invalidVerdict === "drop") {
    opts.notes?.push(`${prefix} dropped: verdict "${String(v.verdict)}" is invalid`)
    return null
  }
  return out
}

/** Text fallback with the count of malformed entries that were dropped, so
 *  the engine can surface a partial run instead of silently losing them. */
export function asCandidatesResult(
  value: unknown,
  cap: number,
): { candidates: RawFinding[]; dropped: number; truncated?: boolean } | null {
  // Text fallback: a malformed sibling must not discard the valid candidates,
  // because there is no tool response that can ask the child to re-emit.
  const parsed = normalizeCandidatesCall(value, cap, { tolerateDropped: true })
  return parsed.ok
    ? {
        candidates: parsed.value.candidates,
        dropped: parsed.value.dropped ?? 0,
        ...(parsed.value.truncated ? { truncated: true } : {}),
      }
    : null
}

export type Verdict = { verdict: "CONFIRMED" | "PLAUSIBLE" | "REFUTED"; evidence: string }

function normalizeVerdictText(value: unknown): Verdict["verdict"] | undefined {
  const text = str(value)?.trim().toUpperCase()
  return text && VERDICTS.has(text) ? (text as Verdict["verdict"]) : undefined
}

export function asVerdict(value: unknown): Verdict | null {
  // Text fallback: keep a verdict with a placeholder rather than dropping the
  // candidate; the engine marks the run partial when the placeholder appears.
  const parsed = normalizeVerdictCall(value, { tolerateMissingEvidence: true })
  return parsed.ok ? parsed.value : null
}

export function asGroupVerdicts(
  value: unknown,
  count: number,
): Array<{ index: number; verdict: Verdict["verdict"]; evidence: string }> | null {
  // Text fallback: keep the auditable verdicts instead of dropping the whole
  // group because one sibling omitted its evidence.
  const parsed = normalizeGroupVerdictsCall(value, Math.max(1, count), {
    tolerateMissingEvidence: true,
    tolerateDropped: true,
    tolerateOffset: true,
  })
  if (!parsed.ok) return null
  // A text fallback cannot re-prompt the child. Keep partial verdicts instead
  // of discarding the whole group, and shift a contiguous 1-based list so the
  // verdicts still map to candidates [0..n-1]. A non-contiguous list is kept
  // as-is; the engine drops the missing indices and warns.
  // Shift before filtering: a 1-based list ending at `count` has an index
  // equal to the group size, which a pre-shift range filter would discard.
  const raw = parsed.value.verdicts
  const sorted = [...raw].sort((a, b) => a.index - b.index)
  const contiguousFromOne =
    sorted.length > 0 && sorted.every((v, i) => v.index === i + 1)
  const shifted = contiguousFromOne ? sorted.map((v) => ({ ...v, index: v.index - 1 })) : raw
  return shifted.filter((v) => v.index >= 0 && v.index < count)
}

/* -------------------------------------------------------------------------
 * Tolerant child-tool calls.
 *
 * The reference's StructuredOutput tool validates a subagent's payload and
 * re-prompts on a mismatch. OpenCode has no pre-validation hook, so the tool
 * boundary normalises what it can and rejects a payload when doing so would
 * silently lose part of the answer (a malformed candidate, a verdict with no
 * evidence). Valid entries otherwise survive one bad sibling.
 * ---------------------------------------------------------------------- */

export type NormalizedCall<T> = { ok: true; value: T; notes: string[] } | { ok: false; error: string }

type ListItemOutcome<T> = {
  value?: T
  note?: string
  /** Count a non-empty outcome as dropped (e.g. a tolerated missing-evidence verdict). */
  dropped?: boolean
}

/**
 * One cap/drop/notes skeleton for every list-shaped child payload. The four
 * normalizers below differ only in their per-item validator and whether the
 * cap applies before or after normalization. Keeping that policy here means a
 * truncation or retry change lands in one place.
 */
function normalizeList<T>(
  entries: unknown[],
  opts: {
    key: string
    cap: number
    /** Candidates skip malformed tail entries; the others normalize then cap. */
    capOrder: "before" | "after"
    normalize: (item: unknown, index: number) => ListItemOutcome<T>
  },
): { items: T[]; notes: string[]; dropped: number } {
  const items: T[] = []
  const notes: string[] = []
  let dropped = 0
  for (const [i, item] of entries.entries()) {
    if (opts.capOrder === "before" && items.length >= opts.cap) {
      notes.push(`${opts.key} truncated at ${opts.cap}`)
      break
    }
    const outcome = opts.normalize(item, i)
    if (outcome.note) notes.push(outcome.note)
    if (outcome.dropped === true || (outcome.dropped === undefined && outcome.value === undefined)) dropped++
    if (outcome.value === undefined) continue
    if (opts.capOrder === "after" && items.length >= opts.cap) {
      notes.push(`${opts.key} truncated at ${opts.cap}`)
      break
    }
    items.push(outcome.value)
  }
  return { items, notes, dropped }
}

export function normalizeCandidatesCall(
  value: unknown,
  cap = 64,
  opts: { tolerateDropped?: boolean } = {},
): NormalizedCall<{ candidates: RawFinding[]; dropped?: number; truncated?: boolean }> {
  if (!isRecord(value)) return { ok: false, error: "expected an object with a candidates array" }
  if (!Array.isArray(value.candidates)) return { ok: false, error: "candidates must be an array" }
  const { items: candidates, notes, dropped } = normalizeList<RawFinding>(value.candidates, {
    key: "candidates",
    cap,
    // Check the cap before normalizing: a malformed entry beyond the cap is
    // discarded by truncation anyway, so it must not reject the whole call.
    capOrder: "before",
    normalize: (item, i) => {
      const finding = normalizeFinding(item)
      return finding
        ? { value: finding }
        : { note: `candidates[${i}] dropped: needs file, summary, and failure_scenario` }
    },
  })
  // A finder submits its whole angle in one call. Silently keeping only the
  // well-formed entries hides the lost candidates from the engine; reject the
  // tool call so the child is told to re-emit the complete list. The text
  // fallback opts into tolerance because it cannot re-prompt the child.
  if (dropped > 0 && !opts.tolerateDropped) {
    return {
      ok: false,
      error: `${notes.filter((n) => n.includes("dropped")).join("; ")}. Re-emit every candidate with file, summary, and failure_scenario.`,
    }
  }
  if (candidates.length === 0 && value.candidates.length > 0)
    return { ok: false, error: notes[0] ?? "no candidate had the required file, summary, and failure_scenario fields" }
  const truncated = notes.some((note) => note.includes("truncated at"))
  return { ok: true, value: { candidates, dropped, ...(truncated ? { truncated } : {}) }, notes }
}

type EvidenceResult = {
  verdict: Verdict["verdict"]
  evidence: string
  /** The verdict was kept despite missing evidence. */
  missing: boolean
}

/**
 * Both the single and grouped verifier accept `reason`/`justification` as
 * aliases for `evidence`, and both downgrade an unevidenced CONFIRMED verdict
 * in the tolerant text path. Keep that policy in one place.
 */
function verdictWithEvidence(
  verdict: Verdict["verdict"],
  value: Record<string, unknown>,
  tolerateMissing: boolean,
): EvidenceResult | undefined {
  const evidence = str(value.evidence) ?? str(value.reason) ?? str(value.justification)
  if (evidence) return { verdict, evidence, missing: false }
  if (!tolerateMissing) return undefined
  // A verdict without evidence is not auditable. The text fallback keeps the
  // candidate for recall and downgrades both CONFIRMED and REFUTED to
  // PLAUSIBLE: an unevidenced refutation must not silently delete a finding
  // the verifier could not justify.
  return {
    verdict: "PLAUSIBLE",
    evidence: NO_EVIDENCE,
    missing: true,
  }
}

export function normalizeVerdictCall(
  value: unknown,
  opts: { tolerateMissingEvidence?: boolean } = {},
): NormalizedCall<Verdict> {
  if (!isRecord(value)) return { ok: false, error: "expected an object with verdict and evidence" }
  const verdict = normalizeVerdictText(value.verdict)
  if (!verdict) return { ok: false, error: "verdict must be CONFIRMED, PLAUSIBLE, or REFUTED" }
  const safe = verdictWithEvidence(verdict, value, opts.tolerateMissingEvidence === true)
  if (!safe) return { ok: false, error: "evidence is required for a verdict" }
  return {
    ok: true,
    value: { verdict: safe.verdict, evidence: safe.evidence },
    notes: safe.missing
      ? [
          `evidence was missing; recorded as (no evidence provided)${safe.verdict !== verdict ? " and downgraded to PLAUSIBLE" : ""}`,
        ]
      : [],
  }
}

export function normalizeGroupVerdictsCall(
  value: unknown,
  cap = 64,
  opts: { tolerateMissingEvidence?: boolean; tolerateDropped?: boolean; tolerateOffset?: boolean } = {},
): NormalizedCall<{ verdicts: Array<{ index: number; verdict: Verdict["verdict"]; evidence: string }> }> {
  if (!isRecord(value)) return { ok: false, error: "expected an object with a verdicts array" }
  if (!Array.isArray(value.verdicts)) return { ok: false, error: "verdicts must be an array" }
  const seen = new Set<number>()
  let missingEvidence = 0
  const { items: verdicts, notes, dropped } = normalizeList<{
    index: number
    verdict: Verdict["verdict"]
    evidence: string
  }>(value.verdicts, {
    key: "verdicts",
    cap,
    capOrder: "after",
    normalize: (item, i) => {
      if (!isRecord(item)) return { note: `verdicts[${i}] dropped: not an object` }
      const index = num(item.index)
      const verdict = normalizeVerdictText(item.verdict)
      if (index === undefined || !Number.isInteger(index) || index < 0) {
        return { note: `verdicts[${i}] dropped: index must be a non-negative integer` }
      }
      if (!verdict) return { note: `verdicts[${i}] dropped: verdict is invalid` }
      const safe = verdictWithEvidence(verdict, item, opts.tolerateMissingEvidence === true)
      if (!safe) {
        // A verdict without evidence cannot be audited; the strict tool
        // boundary rejects it so the verifier re-emits.
        missingEvidence++
        return { note: `verdicts[${i}] dropped: evidence is required`, dropped: true }
      }
      if (safe.missing) {
        // The text fallback keeps the candidate with a placeholder so it is
        // not lost; it is still counted as a missing-evidence repair.
        missingEvidence++
        const note = `verdicts[${i}] dropped: evidence is required`
        if (!seen.has(index)) {
          seen.add(index)
          return { value: { index, verdict: safe.verdict, evidence: safe.evidence }, note, dropped: true }
        }
        return { note, dropped: true }
      }
      if (seen.has(index)) return { note: `verdicts[${i}] dropped: duplicate index ${index}` }
      seen.add(index)
      return { value: { index, verdict: safe.verdict, evidence: safe.evidence } }
    },
  })
  if (missingEvidence > 0 && !opts.tolerateMissingEvidence) {
    return { ok: false, error: "evidence is required for every verdict; re-emit each verdict with its evidence" }
  }
  // A grouped verifier submits its whole payload in one call. Keeping only the
  // valid entries would silently drop candidates, so reject and let it re-emit.
  if (dropped > 0 && !opts.tolerateDropped) {
    return {
      ok: false,
      error: `${notes.filter((n) => n.includes("dropped")).join("; ")}. Re-emit one valid verdict per candidate.`,
    }
  }
  // Indices are positions in the candidate group and are always zero-based.
  // Accepting an offset list here told the verifier its submission succeeded,
  // then the engine discarded every candidate because index 0 was absent. The
  // text fallback has its own guard, but the runner's shared validator must
  // reject an offset list too, or it never re-prompts the child.
  if (verdicts.length > 0 && !seen.has(0) && !opts.tolerateOffset) {
    return {
      ok: false,
      error: "verdict indices must be zero-based: include index 0 for the first candidate.",
    }
  }
  if (verdicts.length === 0 && value.verdicts.length > 0)
    return { ok: false, error: "no verdict had a valid index and verdict" }
  return { ok: true, value: { verdicts }, notes }
}

export function normalizeReportCall(value: unknown, cap = 64): NormalizedCall<Report> {
  if (!isRecord(value)) return { ok: false, error: "expected an object with summary and findings" }
  if (!Array.isArray(value.findings)) return { ok: false, error: "findings must be an array" }
  const summary = str(value.summary)
  const { items: findings, notes, dropped } = normalizeList<Report["findings"][number]>(value.findings, {
    key: "findings",
    cap,
    capOrder: "after",
    normalize: (item, i) => {
      const finding = normalizeFinding(item)
      return finding
        ? { value: finding }
        : { note: `findings[${i}] dropped: needs file, summary, and failure_scenario` }
    },
  })
  if (!summary) notes.push("summary was missing; using a generic summary")
  if (findings.length === 0 && value.findings.length > 0)
    return { ok: false, error: notes[0] ?? "no finding had the required file, summary, and failure_scenario fields" }
  // A capped report is not a complete report. Carry the flag so the engine can
  // mark the run partial instead of presenting a silently shortened list.
  const truncated = notes.some((note) => note.includes("truncated at"))
  return {
    ok: true,
    value: {
      summary: summary ?? "Synthesis report",
      findings,
      ...(dropped > 0 ? { dropped } : {}),
      ...(truncated ? { truncated } : {}),
    },
    notes,
  }
}

/** Decisions are one per verified survivor; the max cell can exceed 64. */
const MAX_DECISIONS = 256

export function normalizeDecisionsCall(
  value: unknown,
  cap = MAX_DECISIONS,
  opts: { tolerateDropped?: boolean } = {},
): NormalizedCall<Decisions> {
  if (!isRecord(value)) return { ok: false, error: "expected an object with summary and decisions" }
  if (!Array.isArray(value.decisions)) return { ok: false, error: "decisions must be an array" }
  const summary = str(value.summary)
  const { items: decisions, notes, dropped } = normalizeList<Decisions["decisions"][number]>(
    value.decisions,
    {
      key: "decisions",
      cap,
      capOrder: "after",
      normalize: (item, i) => {
        if (!isRecord(item)) return { note: `decisions[${i}] dropped: not an object` }
        const index = num(item.index)
        if (index === undefined || !Number.isInteger(index) || index < 0) {
          return { note: `decisions[${i}] dropped: index must be a non-negative integer` }
        }
        const merge: number[] = []
        if (item.merge !== undefined) {
          if (!Array.isArray(item.merge)) {
            return { note: `decisions[${i}].merge must be an array of indices` }
          }
          for (const entry of item.merge) {
            const merged = num(entry)
            if (merged === undefined || !Number.isInteger(merged) || merged < 0) {
              return { note: `decisions[${i}].merge entries must be non-negative integers` }
            }
            merge.push(merged)
          }
        }
        return { value: { index, merge } }
      },
    },
  )
  if (!summary) notes.push("summary was missing; using a generic summary")
  // A synthesizer submits its whole plan in one call. Silently filtering a
  // malformed merge would drop the merge and let both findings appear again;
  // reject so the child can re-emit the plan. The text fallback opts into
  // tolerance because it cannot re-prompt the child.
  if (dropped > 0 && !opts.tolerateDropped) {
    return {
      ok: false,
      error: `${notes.filter((n) => n.includes("dropped") || n.includes("must")).join("; ")}. Re-emit one valid decision per candidate.`,
    }
  }
  if (decisions.length === 0 && value.decisions.length > 0)
    return { ok: false, error: "no decision had a valid index" }
  const truncated = notes.some((note) => note.includes("truncated at"))
  return {
    ok: true,
    value: {
      summary: summary ?? "Merge and rank decisions",
      decisions,
      ...(truncated ? { truncated: true } : {}),
    },
    notes,
  }
}

export type Report = {
  summary: string
  findings: Array<RawFinding & { verdict?: "CONFIRMED" | "PLAUSIBLE" }>
  /** Malformed findings the normalizer had to drop. */
  dropped?: number
  /** The report was longer than the normalizer's cap. */
  truncated?: boolean
}

export function asReport(value: unknown, cap = 64): Report | null {
  const parsed = normalizeReportCall(value, cap)
  if (!parsed.ok) return null
  // A payload captured from code_review_report was already normalized at the
  // tool boundary, which recorded its dropped count. Re-normalizing the valid
  // remainder computes zero and would hide the loss from the engine.
  const priorDropped =
    isRecord(value) && typeof value.dropped === "number" && Number.isFinite(value.dropped)
      ? Math.max(0, Math.trunc(value.dropped))
      : 0
  const dropped = (parsed.value.dropped ?? 0) + priorDropped
  // The tool boundary also records that it truncated a too-long report. A
  // re-normalization of the already-shortened array cannot see that fact.
  const priorTruncated = isRecord(value) && value.truncated === true
  return {
    ...parsed.value,
    ...(dropped > 0 ? { dropped } : {}),
    ...(priorTruncated ? { truncated: true } : {}),
  }
}

export type Decisions = {
  summary: string
  decisions: Array<{ index: number; merge: number[] }>
  /** The tool cap dropped decisions from the tail. */
  truncated?: boolean
}

export function asDecisions(value: unknown): Decisions | null {
  const parsed = normalizeDecisionsCall(value, MAX_DECISIONS, { tolerateDropped: true })
  if (!parsed.ok) return null
  // Preserve the tool boundary's truncation flag; re-normalizing the valid
  // remainder cannot discover that decisions were cut from the tail.
  const priorTruncated = isRecord(value) && value.truncated === true
  return priorTruncated ? { ...parsed.value, truncated: true } : parsed.value
}
