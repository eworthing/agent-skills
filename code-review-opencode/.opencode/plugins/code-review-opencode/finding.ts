/**
 * Shared finding helpers.
 *
 * One anchor formatter, one short-summary derivation, and one pluralizer for
 * every output contract. The reference schema types `line` as an integer
 * without a minimum, but a non-positive line is not an anchor: GitHub rejects
 * line 0, and a terminal `file:0` reads like a real location.
 */
export type Locatable = { file: string; line?: number }

/**
 * A positive integer line, or undefined. Models routinely stringify line
 * numbers ("42"), and dropping that anchor turns a locatable finding into an
 * unanchorable one at comment-posting time.
 */
export function positiveLine(value: unknown): number | undefined {
  const n =
    typeof value === "number"
      ? value
      : typeof value === "string" && /^\d+$/.test(value.trim())
        ? Number(value.trim())
        : undefined
  return typeof n === "number" && Number.isSafeInteger(n) && n > 0 ? n : undefined
}

export function lineOf(f: Locatable): number | undefined {
  return positiveLine(f.line)
}

export function location(f: Locatable): string {
  const line = lineOf(f)
  return line === undefined ? f.file : `${f.file}:${line}`
}

/**
 * The display/prompt form of a location. `location` stays the raw key used for
 * grouping and comment anchors; this form escapes control characters so a
 * filename cannot forge a new instruction line or report entry.
 */
export function renderedLocation(f: Locatable): string {
  const line = lineOf(f)
  const file = renderPath(f.file)
  return line === undefined ? file : `${file}:${line}`
}

/**
 * Render a path on one line. Git allows newlines, tabs, and other control
 * characters in filenames; inserting one raw into a prompt lets a changed file
 * name forge a new instruction line. The escaped form is still unambiguous and
 * searchable.
 */
export function renderPath(value: string): string {
  return value.replace(/[\u0000-\u001F\u007F-\u009F]/g, (c) => {
    // A tab stays readable inside a filename; only line breaks can forge a
    // new instruction line in the prompt.
    if (c === "\t") return c
    if (c === "\n") return "\\n"
    if (c === "\r") return "\\r"
    return `\\u{${(c.codePointAt(0) ?? 0).toString(16).toUpperCase()}}`
  })
}

/**
 * Truncate to a UTF-16 length without splitting a surrogate pair. A plain
 * `slice` can leave a lone high surrogate that serializes as U+FFFD.
 */
export function truncateText(text: string, max: number): string {
  if (text.length <= max) return text
  const cut = text.slice(0, max)
  const last = cut.charCodeAt(cut.length - 1)
  return last >= 0xd800 && last <= 0xdbff ? cut.slice(0, -1) : cut
}

/**
 * Parse a non-negative integer environment override. The one grammar is
 * shared by the scope, comment, and stall controls so a spelling cannot be
 * accepted by one subsystem and ignored by another. An explicit `0` is kept.
 */
export function envInt(name: string): number | undefined {
  const raw = process.env[name]
  if (raw === undefined || !/^\d+$/.test(raw.trim())) return undefined
  return Number(raw.trim())
}

/** JSON Schema `maxLength` counts Unicode code points, not UTF-16 units. */
export function codePointLength(text: string): number {
  return Array.from(text).length
}

/** Truncate to a code-point limit, matching the schema's length semantics. */
export function truncateCodePoints(text: string, max: number): string {
  if (codePointLength(text) <= max) return text
  return Array.from(text).slice(0, max).join("")
}

/** Compressed label: at most 60 characters, preferring a word boundary. */
export function shortSummary(summary: string): string {
  if (summary.length <= 60) return summary
  const cut = truncateText(summary, 60)
  const space = cut.lastIndexOf(" ")
  return (space > 30 ? cut.slice(0, space) : cut).trim()
}

export function pluralize(n: number, singular: string, plural = `${singular}s`): string {
  return `${n} ${pluralWord(n, singular, plural)}`
}

export function pluralWord(n: number, singular: string, plural = `${singular}s`): string {
  return n === 1 ? singular : plural
}
