/**
 * ReportFindings adapter schema.
 *
 * Recovered from the v2.1.318 bundle (offset 276,603,074):
 *   findings: array(max 32) of {
 *     file: string (required),
 *     line?: integer,
 *     summary: string (required),
 *     short_summary?: string (max 60),
 *     failure_scenario: string (required),
 *     category?: string (max 40),
 *     verdict?: "CONFIRMED" | "PLAUSIBLE",
 *     outcome?: "fixed" | "skipped" | "no_change_needed"
 *   }
 *   level?: "low" | "medium" | "high" | "xhigh" | "max"
 */
import { isRecord, normalizeFinding } from "./json.ts"
import { HARD_FINDINGS_CAP, LEVELS, normalizeLevel } from "./cells.ts"
import { codePointLength } from "./finding.ts"

export const REPORT_FINDINGS_SCHEMA = {
  type: "object",
  properties: {
    level: {
      type: "string",
      enum: [...LEVELS],
      description: "Effort level the review ran at",
    },
    findings: {
      type: "array",
      maxItems: HARD_FINDINGS_CAP,
      description: "Verified findings, most-severe first; empty if none survived",
      items: {
        type: "object",
        properties: {
          file: { type: "string", description: "Repo-relative path of the file the finding is in" },
          line: {
            type: "integer",
            minimum: -9007199254740991,
            maximum: 9007199254740991,
            description: "1-indexed line the finding anchors to",
          },
          summary: { type: "string", description: "One-sentence statement of the defect" },
          short_summary: {
            type: "string",
            maxLength: 60,
            description:
              "Compressed label for compact UI (≤60 chars): the claim alone, no rationale or consequence clause",
          },
          failure_scenario: { type: "string", description: "Concrete inputs/state → wrong output/crash" },
          category: {
            type: "string",
            maxLength: 40,
            description:
              'Short kebab-case slug of the finding type, e.g. "correctness", "simplification", "efficiency", "test-coverage"',
          },
          evidence: {
            type: "string",
            description: "Verifier evidence: the line(s) or citation that prove the claim",
          },
          verdict: {
            type: "string",
            enum: ["CONFIRMED", "PLAUSIBLE"],
            description: "Set when a verify pass ran; absent on inline-only reviews",
          },
          outcome: {
            type: "string",
            enum: ["fixed", "skipped", "no_change_needed"],
            description: "Set ONLY when re-reporting after applying fixes: what happened to this finding",
          },
        },
        required: ["file", "summary", "failure_scenario"],
        additionalProperties: false,
      },
    },
  },
  required: ["findings"],
  additionalProperties: false,
} as const

export type ReportedFinding = {
  file: string
  line?: number
  summary: string
  short_summary?: string
  failure_scenario: string
  category?: string
  verdict?: "CONFIRMED" | "PLAUSIBLE"
  evidence?: string
  outcome?: Outcome
}

export type ReportFindingsResult =
  | {
      ok: true
      level?: string
      findings: ReportedFinding[]
      /** Non-fatal repairs: dropped findings and coerced outcomes. */
      notes: string[]
    }
  | { ok: false; error: string }

/**
 * Validate/normalise a ReportFindings call.
 *
 * The reference schema is strict: one malformed finding rejects the call so
 * the model re-emits the complete list.
 *   - invalid verdict/outcome => reject the call
 *   - missing required fields / wrong types / unknown properties => reject
 *   - >32 findings => reject the call so the model merges/ranks and re-emits
 *   - invalid level => ignore the level, keep the findings
 *
 * Only a payload that is not an object or has no findings array is unusable.
 */
type FindingProperty = {
  type?: string
  maxLength?: number
  enum?: readonly string[]
  minimum?: number
  maximum?: number
}

const FINDING_SCHEMA = REPORT_FINDINGS_SCHEMA.properties.findings.items
const FINDING_PROPERTIES = FINDING_SCHEMA.properties as unknown as Record<string, FindingProperty>
const FINDING_REQUIRED: readonly string[] = FINDING_SCHEMA.required
/** The outcome enum is owned by the advertised schema; do not copy it. */
const OUTCOMES = FINDING_SCHEMA.properties.outcome.enum
type Outcome = (typeof OUTCOMES)[number]
const isOutcome = (value: string): value is Outcome =>
  (OUTCOMES as readonly string[]).includes(value)

/**
 * Validate one finding by walking the advertised schema, not a second
 * hand-maintained copy of its keys and limits. Adding/renaming a property in
 * REPORT_FINDINGS_SCHEMA automatically changes what this validator accepts.
 */
function reportFindingError(raw: unknown, i: number): string | undefined {
  if (!isRecord(raw)) {
    return `findings[${i}] must be an object`
  }
  const rec = raw
  for (const key of Object.keys(rec)) {
    if (!Object.hasOwn(FINDING_PROPERTIES, key)) {
      return `findings[${i}].${key} is not allowed by the ReportFindings schema`
    }
  }
  for (const key of FINDING_REQUIRED) {
    if (typeof rec[key] !== "string") {
      return `findings[${i}].${key} must be a string`
    }
  }
  for (const [key, property] of Object.entries(FINDING_PROPERTIES)) {
    const value = rec[key]
    if (value === undefined) continue
    if (property.type === "string") {
      if (typeof value !== "string") return `findings[${i}].${key} must be a string`
      if (property.maxLength !== undefined && codePointLength(value) > property.maxLength) {
        return `findings[${i}].${key} must be at most ${property.maxLength} characters`
      }
      // Outcomes accept the common capitalized spelling and are normalized
      // later; the other enums are exact.
      if (key === "outcome") {
        if (!isOutcome(value.trim().toLowerCase())) {
          return `findings[${i}].outcome "${value}" is invalid; use fixed, skipped, or no_change_needed`
        }
      } else if (property.enum && !property.enum.includes(value)) {
        if (key === "verdict") {
          return `findings[${i}].verdict "${value}" is invalid; use CONFIRMED or PLAUSIBLE`
        }
        return `findings[${i}].${key} "${value}" is invalid`
      }
    } else if (property.type === "integer") {
      if (
        typeof value !== "number" ||
        !Number.isInteger(value) ||
        value < (property.minimum ?? Number.MIN_SAFE_INTEGER) ||
        value > (property.maximum ?? Number.MAX_SAFE_INTEGER)
      ) {
        return `findings[${i}].${key} must be an integer within the safe range`
      }
    }
  }
  return undefined
}

export function normalizeReportFindings(input: unknown): ReportFindingsResult {
  if (typeof input !== "object" || input === null) return { ok: false, error: "input must be an object" }
  const obj = input as Record<string, unknown>
  const notes: string[] = []

  let level: string | undefined
  if (obj.level !== undefined) {
    // Every other level boundary is case-insensitive (and accepts aliases such
    // as `med`); a capitalized re-report must not lose its typed metadata.
    level = normalizeLevel(String(obj.level))
    if (level === undefined) notes.push(`level "${String(obj.level)}" is invalid; ignored`)
  }

  if (!Array.isArray(obj.findings)) return { ok: false, error: "findings must be an array" }
  if (obj.findings.length > HARD_FINDINGS_CAP) {
    return {
      ok: false,
      error: `findings must contain at most ${HARD_FINDINGS_CAP} entries; merge or rank them and re-emit`,
    }
  }

  const findings: ReportedFinding[] = []
  for (const [i, raw] of obj.findings.entries()) {
    const schemaError = reportFindingError(raw, i)
    if (schemaError) return { ok: false, error: schemaError }
    // The reference tool schema allows empty strings; pre-validation has
    // already enforced the rest of the closed schema. Keep the shared field
    // normalizer for line handling and empty-string semantics.
    const finding = normalizeFinding(raw, {
      allowEmptyStrings: true,
      invalidVerdict: "drop",
      notes,
      notePrefix: `findings[${i}]`,
    })
    if (!finding) {
      return { ok: false, error: `findings[${i}] could not be normalized` }
    }

    const rawOutcome = (raw as Record<string, unknown>).outcome
    let outcome: Outcome | undefined
    if (rawOutcome !== undefined) {
      // `reportFindingError` already validated the case-normalized value
      // against the schema enum; do not validate it a second time here.
      outcome = String(rawOutcome).trim().toLowerCase() as Outcome
    }

    findings.push({
      ...finding,
      ...(outcome !== undefined ? { outcome } : {}),
    })
  }

  if (findings.length === 0 && obj.findings.length > 0) {
    // The level note is pushed first, but it did not cause the empty result.
    // Report the finding-level error so the model fixes the right field.
    const findingNote = notes.find((note) => note.startsWith("findings["))
    return {
      ok: false,
      error:
        findingNote ??
        notes[0] ??
        "no finding had the required file, summary, and failure_scenario fields",
    }
  }

  return { ok: true, level, findings, notes }
}
