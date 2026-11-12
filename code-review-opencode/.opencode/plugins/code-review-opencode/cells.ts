/**
 * Versioned review configuration.
 *
 * The tables below are transcriptions of Claude Code's own dispatch table
 * (`he` in the v2.1.318 bundle) and of the two extracted workflow scripts
 * (v2.1.162 and v2.1.221). A cell is the unit the reference calls a "recipe":
 * the model family plus the typed effort level selects it.
 */

export type Engine = "inline" | "multi" | "minimal"
export type InlineVariant = "low" | "low-min" | "low-expanded" | "inline-medium" | "inline-high" | "inline-xhigh" | "minimal"
export type VerifyMode = "none" | "3state" | "recall" | "grouped"
export type SynthesisMode = "none" | "index" | "text"
export type CleanupLenses = "162" | "current"

export type Cell = {
  id: string
  engine: Engine
  inlineVariant?: InlineVariant
  /** Number of correctness angles (3 => A/B/C, 5 => A..E). */
  correctnessAngles: number
  /** Cleanup finders: one agent per cleanup angle, or one merged finder. */
  cleanupMode: "per-angle" | "merged"
  /** Number of cleanup lenses (4 in v2.1.162, 5 from v2.1.221). */
  cleanupAngles: number
  /** Candidate cap per finder. */
  perAngle: number
  /** Default result cap. "all" means no maximum. */
  maxFindings: number | "all"
  sweep: boolean
  sweepCap: number
  verify: VerifyMode
  /** How the final report is merged and ranked. */
  synthesis: SynthesisMode
  /** Cleanup lens set: "162" is the four-lens v2.1.162 set. */
  cleanupLenses: CleanupLenses
  /** Default semantic merge/rank synthesizer for this cell. */
  semanticMerge: boolean
  /** Hard verifier budget (v2.1.162 only). */
  verifyBudget?: number
  /** Finders stream into verification instead of waiting at a barrier. */
  streaming?: boolean
  /** Reference injects a diff-size finder-budget hint for this cell. */
  finderBudgetHint: boolean
  /** Set when a workflow version has no recipe for the requested level. */
  fallbackNotice?: string
}

const cell = (c: Partial<Cell> & Pick<Cell, "id" | "engine">): Cell => ({
  correctnessAngles: 3,
  cleanupMode: "per-angle",
  cleanupAngles: 5,
  perAngle: 6,
  maxFindings: 10,
  sweep: false,
  sweepCap: 8,
  verify: "none",
  synthesis: "none",
  cleanupLenses: "current",
  semanticMerge: false,
  finderBudgetHint: false,
  ...c,
})

/* ------------------------------------------------------------------ */
/* Claude Code v2.1.318 (current)                                     */
/* ------------------------------------------------------------------ */

const V318_CELLS: Record<string, Cell> = {
  low: cell({
    id: "low",
    engine: "inline",
    inlineVariant: "low",
    maxFindings: 4,
    verify: "none",
  }),
  "low-sonnet5": cell({
    id: "low-sonnet5",
    engine: "inline",
    inlineVariant: "low-min",
    maxFindings: "all",
    verify: "none",
  }),
  medium: cell({
    id: "medium",
    engine: "multi",
    correctnessAngles: 3,
    cleanupMode: "per-angle",
    perAngle: 6,
    maxFindings: 8,
    verify: "3state",
  }),
  high: cell({
    id: "high",
    engine: "multi",
    correctnessAngles: 3,
    cleanupMode: "per-angle",
    perAngle: 6,
    maxFindings: 10,
    verify: "recall",
  }),
  xhigh: cell({
    id: "xhigh",
    engine: "multi",
    correctnessAngles: 5,
    cleanupMode: "per-angle",
    perAngle: 8,
    maxFindings: 15,
    verify: "3state",
    sweep: true,
    semanticMerge: true,
  }),
  max: cell({
    id: "max",
    engine: "multi",
    correctnessAngles: 5,
    cleanupMode: "per-angle",
    perAngle: 8,
    maxFindings: 15,
    verify: "3state",
    sweep: true,
    semanticMerge: true,
  }),
  "o48-low-v1": cell({
    id: "o48-low-v1",
    engine: "inline",
    inlineVariant: "low-expanded",
    maxFindings: 8,
    verify: "none",
  }),
  "o48-med-v1": cell({
    id: "o48-med-v1",
    engine: "inline",
    inlineVariant: "inline-medium",
    maxFindings: 8,
    verify: "none",
  }),
  "o48-high-v1": cell({
    id: "o48-high-v1",
    engine: "inline",
    inlineVariant: "inline-high",
    maxFindings: 10,
    verify: "none",
  }),
  "o48-xhigh-v1": cell({
    id: "o48-xhigh-v1",
    engine: "inline",
    inlineVariant: "inline-xhigh",
    correctnessAngles: 5,
    perAngle: 8,
    maxFindings: 15,
    verify: "none",
    sweep: true,
  }),
  "o5-bmin": cell({
    id: "o5-bmin",
    engine: "minimal",
    inlineVariant: "minimal",
    maxFindings: 15,
    verify: "none",
  }),
}

export const V318_FAMILIES: Record<string, Record<string, string>> = {
  default: {
    low: "low",
    medium: "o48-high-v1",
    high: "o48-high-v1",
    xhigh: "o48-xhigh-v1",
    max: "max",
  },
  "claude-sonnet-5": {
    low: "low-sonnet5",
    medium: "medium",
    high: "high",
    xhigh: "xhigh",
    max: "max",
  },
  "claude-opus-4-8": {
    low: "o48-low-v1",
    medium: "o48-med-v1",
    high: "o48-high-v1",
    xhigh: "o48-xhigh-v1",
    max: "max",
  },
  "claude-opus-5": {
    low: "low",
    medium: "o5-bmin",
    high: "o5-bmin",
    xhigh: "o48-xhigh-v1",
    max: "max",
  },
}

/* ------------------------------------------------------------------ */
/* Extracted workflow v2.1.162                                        */
/* ------------------------------------------------------------------ */

const V162_CELLS: Record<string, Cell> = {
  high: cell({
    id: "wf162-high",
    engine: "multi",
    correctnessAngles: 3,
    cleanupMode: "per-angle",
    cleanupAngles: 4,
    perAngle: 6,
    maxFindings: 10,
    verify: "3state",
    synthesis: "text",
    cleanupLenses: "162",
    verifyBudget: 25,
    streaming: true,
  }),
  xhigh: cell({
    id: "wf162-xhigh",
    engine: "multi",
    correctnessAngles: 5,
    cleanupMode: "per-angle",
    cleanupAngles: 4,
    perAngle: 8,
    maxFindings: 15,
    verify: "3state",
    synthesis: "text",
    cleanupLenses: "162",
    verifyBudget: 25,
    streaming: true,
    sweep: true,
  }),
  max: cell({
    id: "wf162-max",
    engine: "multi",
    correctnessAngles: 5,
    cleanupMode: "per-angle",
    cleanupAngles: 4,
    perAngle: 8,
    maxFindings: 15,
    verify: "3state",
    synthesis: "text",
    cleanupLenses: "162",
    verifyBudget: 25,
    streaming: true,
    sweep: true,
  }),
}

/* ------------------------------------------------------------------ */
/* Extracted workflow v2.1.221                                        */
/* ------------------------------------------------------------------ */

const V221_CELLS: Record<string, Cell> = {
  high: cell({
    id: "wf221-high",
    engine: "multi",
    correctnessAngles: 3,
    cleanupMode: "merged",
    perAngle: 6,
    maxFindings: 10,
    verify: "grouped",
    synthesis: "index",
  }),
  xhigh: cell({
    id: "wf221-xhigh",
    engine: "multi",
    correctnessAngles: 5,
    cleanupMode: "merged",
    perAngle: 8,
    maxFindings: 15,
    verify: "grouped",
    synthesis: "index",
    sweep: true,
  }),
  max: cell({
    id: "wf221-max",
    engine: "multi",
    correctnessAngles: 5,
    cleanupMode: "merged",
    perAngle: 8,
    maxFindings: 15,
    verify: "grouped",
    synthesis: "index",
    sweep: true,
  }),
}

/* ------------------------------------------------------------------ */
/* Public tables                                                      */
/* ------------------------------------------------------------------ */

export const VERSIONS = {
  "cc-2.1.318": { cells: V318_CELLS, families: V318_FAMILIES },
  "cc-workflow-2.1.162": { cells: V162_CELLS, families: null },
  "cc-workflow-2.1.221": { cells: V221_CELLS, families: null },
} as const

export type VersionID = keyof typeof VERSIONS

export const DEFAULT_MODE: VersionID = "cc-2.1.318"

/**
 * Validate a `--mode`/`CODE_REVIEW_MODE` value. `Object.hasOwn` rather than
 * `in`: inherited keys such as `constructor` must not pass as versions.
 */
export function asVersion(value: string | undefined): VersionID {
  return value !== undefined && Object.hasOwn(VERSIONS, value) ? (value as VersionID) : DEFAULT_MODE
}

export const LEVELS = ["low", "medium", "high", "xhigh", "max"] as const
export type Level = (typeof LEVELS)[number]

export const LEVEL_ALIASES: Record<string, Level> = { med: "medium" }

export function isLevel(value: string): value is Level {
  return (LEVELS as readonly string[]).includes(value)
}

/** oN(e): lowercase, alias, validate. */
export function normalizeLevel(raw: string): Level | undefined {
  const lower = raw.trim().toLowerCase()
  const resolved = LEVEL_ALIASES[lower] ?? lower
  return isLevel(resolved) ? resolved : undefined
}

/** oL(e): invalid strings collapse to "high"; undefined collapses to "medium". */
export function coerceLevel(raw: string | undefined): Level {
  if (raw === undefined) return "medium"
  return isLevel(raw) ? raw : "high"
}

/** Ie(modelID): map a model id to one of the reference's four families. */
export function detectFamily(modelID: string | undefined, override?: string): string {
  if (override && Object.hasOwn(V318_FAMILIES, override)) return override
  const id = (modelID ?? "").toLowerCase()
  if (id.includes("sonnet-5") || id.includes("sonnet5")) return "claude-sonnet-5"
  if (id.includes("opus-5") || id.includes("opus5")) return "claude-opus-5"
  if (id.includes("opus-4-8") || id.includes("opus-4.8") || id.includes("opus4-8")) return "claude-opus-4-8"
  return "default"
}

export function resolveCell(version: VersionID, family: string, level: Level): Cell {
  const table = VERSIONS[version]
  if (table.families) {
    const row = Object.hasOwn(table.families, family) ? table.families[family] : table.families.default
    const cell = table.cells[row[level]]
    // The reference stores finderBudgetHint on the family entry, not the
    // shared cell: only claude-sonnet-5 high/xhigh/max get the diff-size hint.
    if (family === "claude-sonnet-5" && (level === "high" || level === "xhigh" || level === "max")) {
      return { ...cell, finderBudgetHint: true }
    }
    return cell
  }
  // Workflow versions only parameterise high/xhigh/max. Lower levels keep the
  // same model family's current recipe; forcing the `default` family here gave
  // a sonnet-5 session an Opus inline prompt with no notice.
  if (level === "low" || level === "medium") {
    const fallback = resolveCell("cc-2.1.318", family, level)
    return {
      ...fallback,
      fallbackNotice: `--mode ${version} has no ${level}-effort recipe; using the current ${family} ${level} recipe instead.`,
    }
  }
  return table.cells[level]
}

/** Number of finder agents a cell spawns. */
export function finderCount(c: Cell): number {
  const cleanup = c.cleanupMode === "merged" ? 1 : c.cleanupAngles
  return c.correctnessAngles + cleanup
}

/** Per-finder candidate cap; the merged cleanup finder absorbs all lenses. */
export function finderCap(c: Cell): number {
  return c.cleanupMode === "merged" ? c.cleanupAngles * c.perAngle : c.perAngle
}

/**
 * Qs(e,n): the reference's diff-size finder budget. Only cells with
 * finderBudgetHint use it; y = max(2, min(8, ceil(lines / 150))).
 */
export function plannedFinderCount(c: Cell, diffLines?: number): number {
  const total = finderCount(c)
  // Undefined means the caller did not compute churn (full fleet). A real zero
  // (rename- or binary-only diff) still takes the formula's floor of two.
  if (!c.finderBudgetHint || diffLines === undefined || diffLines < 0) return total
  return Math.max(2, Math.min(8, Math.ceil(diffLines / 150)))
}

export const HARD_FINDINGS_CAP = 32
