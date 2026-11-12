/**
 * Child-agent tool schemas and the retry example derived from them.
 *
 * The tool boundary (`index.ts`) and the runner's retry prompt use the same
 * definitions so a renamed or added field cannot leave the retry example
 * describing a shape the orchestrator no longer accepts.
 */
import { REPORT_FINDINGS_SCHEMA } from "./reportfindings.ts"
import { SAMPLE_VALUE } from "./samples.ts"

export type SchemaName = "candidates" | "verdict" | "groupVerdicts" | "report" | "decisions"

/**
 * The one mapping from a result kind to the tool the child is told to call.
 * Both the runner's retry prompt and the plugin registration derive from it,
 * so a rename cannot point a child at an unregistered tool.
 */
export const SCHEMA_TOOL_NAMES: Record<SchemaName, string> = {
  candidates: "code_review_candidates",
  verdict: "code_review_verdict",
  groupVerdicts: "code_review_group_verdicts",
  report: "code_review_report",
  decisions: "code_review_decisions",
}

const REPORT_FINDING_PROPERTIES = REPORT_FINDINGS_SCHEMA.properties.findings.items.properties

function childFindingSchema(): unknown {
  const {
    outcome: _outcome,
    short_summary: _shortSummary,
    category: _category,
    verdict: _verdict,
    ...rest
  } = REPORT_FINDING_PROPERTIES
  return {
    type: "object",
    properties: {
      ...rest,
      short_summary: { type: "string", description: "Compressed label, at most 60 characters" },
      category: { type: "string", description: "Short kebab-case slug" },
      kind: {
        type: "string",
        description: "correctness or cleanup: the class of your assigned lens",
      },
      verdict: {
        type: "string",
        description: "CONFIRMED or PLAUSIBLE; invalid values drop that finding at the tool boundary",
      },
    },
    required: ["file", "summary", "failure_scenario"],
  }
}

export const FINDING_ITEM_SCHEMA = childFindingSchema()

export const CANDIDATES_SCHEMA = {
  type: "object",
  properties: {
    candidates: { type: "array", items: FINDING_ITEM_SCHEMA },
  },
  required: ["candidates"],
} as const

export const VERDICT_SCHEMA = {
  type: "object",
  properties: {
    verdict: { type: "string", description: "CONFIRMED, PLAUSIBLE, or REFUTED" },
    evidence: { type: "string", description: "Quote or cite the relevant line(s)" },
  },
  required: ["verdict", "evidence"],
} as const

export const GROUP_VERDICTS_SCHEMA = {
  type: "object",
  properties: {
    verdicts: {
      type: "array",
      items: {
        type: "object",
        properties: {
          index: { type: "integer", minimum: 0 },
          verdict: { type: "string", description: "CONFIRMED, PLAUSIBLE, or REFUTED" },
          evidence: { type: "string" },
        },
        required: ["index", "verdict", "evidence"],
      },
    },
  },
  required: ["verdicts"],
} as const

export const REPORT_SCHEMA = {
  type: "object",
  properties: {
    summary: { type: "string" },
    findings: { type: "array", items: FINDING_ITEM_SCHEMA },
  },
  required: ["findings"],
} as const

export const DECISIONS_SCHEMA = {
  type: "object",
  properties: {
    summary: { type: "string" },
    decisions: {
      type: "array",
      items: {
        type: "object",
        properties: {
          index: { type: "integer", minimum: 0 },
          merge: { type: "array", items: { type: "integer", minimum: 0 } },
        },
        required: ["index"],
      },
    },
  },
  required: ["decisions"],
} as const

export const SCHEMAS: Record<SchemaName, unknown> = {
  candidates: CANDIDATES_SCHEMA,
  verdict: VERDICT_SCHEMA,
  groupVerdicts: GROUP_VERDICTS_SCHEMA,
  report: REPORT_SCHEMA,
  decisions: DECISIONS_SCHEMA,
}

/** Keep the example useful without listing every optional finding field. */
function includeProperty(key: string, required: readonly string[]): boolean {
  return required.includes(key) || key === "line" || key === "summary" || key === "merge"
}

function exampleValue(schema: unknown, key?: string): unknown {
  const s = (schema ?? {}) as {
    type?: string
    properties?: Record<string, unknown>
    required?: string[]
    items?: unknown
    enum?: unknown[]
  }
  if (Array.isArray(s.enum) && s.enum.length > 0) return s.enum[0]
  if (s.type === "object") {
    const out: Record<string, unknown> = {}
    const required = Array.isArray(s.required) ? s.required : []
    for (const [name, property] of Object.entries(s.properties ?? {})) {
      if (!includeProperty(name, required)) continue
      out[name] = exampleValue(property, name)
    }
    return out
  }
  if (s.type === "array") return [exampleValue(s.items, key)]
  if (s.type === "integer" || s.type === "number") return SAMPLE_VALUE[key ?? ""] ?? 0
  if (s.type === "boolean") return false
  return SAMPLE_VALUE[key ?? ""] ?? "string"
}

/** One JSON example generated from the same schema the child tool validates. */
export function schemaExample(schemaName: string): string {
  const schema = SCHEMAS[schemaName as SchemaName]
  return schema ? JSON.stringify(exampleValue(schema)) : "{}"
}
