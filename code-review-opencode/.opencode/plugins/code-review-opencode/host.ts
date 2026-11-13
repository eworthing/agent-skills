/**
 * Small host-shape helpers kept free of the OpenCode plugin import so they can
 * be unit-tested without a running server.
 */

/** Files that do not give the diff a runtime surface (the reference's exemptions). */
const NON_RUNTIME =
  /(^|\/)(test|tests|spec|__tests__|fixtures?|testdata|docs?)\/|\.(md|mdx|txt|rst)$|(^|\/)[^/]+\.(test|spec)\.[^/]+$|_test\.[^/]+$/i

export function hasRuntimeSurface(files: string[]): boolean {
  return files.some((f) => !NON_RUNTIME.test(f))
}

export type SkillRef = { id?: string; name?: string }

/** `ctx.skill.list()` may return a bare array or a `{location, data}` envelope. */
export function skillEntries(listed: unknown): SkillRef[] {
  if (Array.isArray(listed)) return listed as SkillRef[]
  const data = (listed as { data?: unknown } | undefined)?.data
  return Array.isArray(data) ? (data as SkillRef[]) : []
}

export function hasSkill(listed: unknown, id: string): boolean {
  const wanted = id.toLowerCase()
  return skillEntries(listed).some(
    (s) => String(s?.id ?? "").toLowerCase() === wanted || String(s?.name ?? "").toLowerCase() === wanted,
  )
}

/**
 * Capability probe for the deterministic engine's child-session fan-out.
 * A host without session creation gets the recovered single-pass prompt
 * instead of an engine run that would return an empty, partial review.
 */
export function supportsChildSessions(ctx: unknown): boolean {
  const session = (ctx as { session?: Record<string, unknown> } | undefined)?.session
  // The engine needs get for the parent model and create/prompt/wait/context
  // for the child turn. Interrupt and cleanup are optional: the runner calls
  // them only when the host exposes them.
  return (
    typeof session?.get === "function" &&
    typeof session?.create === "function" &&
    typeof session?.prompt === "function" &&
    typeof session?.wait === "function" &&
    typeof session?.context === "function"
  )
}

export type SessionRecord = {
  id?: string
  parentID?: string | null
  model?: { providerID: string; id: string; variant?: string }
  time?: { busy?: number; idle?: number; updated?: number }
}

/**
 * `ctx.session.get` / `ctx.agent.get` may return the record itself or a
 * `{location, data}` envelope. Every reader must unwrap the same shape.
 */
export function sessionRecord(session: unknown): SessionRecord | undefined {
  if (!session || typeof session !== "object") return undefined
  const data = "data" in session ? (session as { data?: unknown }).data : session
  return data && typeof data === "object" ? (data as SessionRecord) : undefined
}

/**
 * A review child must not start another review. The engine creates one child
 * per role; without this guard a child that can call `code_review` could fan
 * out unboundedly.
 */
export function isChildSession(session: unknown): boolean {
  return Boolean(sessionRecord(session)?.parentID)
}

/**
 * `ctx.session.context` may return the bare message array or the same
 * `{location, data}` envelope as `session.get`. Unwrap both before reading
 * message counts or the final message.
 */
export function sessionMessages(value: unknown): readonly unknown[] | undefined {
  // Hosts have returned the bare array, `{ data: [...] }`, and
  // `{ data: { messages: [...] } }` across versions. Unwrap the known
  // envelopes instead of treating an unfamiliar one as an empty transcript.
  let current: unknown = value
  for (let depth = 0; depth < 5; depth++) {
    if (Array.isArray(current)) return current
    if (!current || typeof current !== "object") return undefined
    const record = current as { data?: unknown; messages?: unknown; items?: unknown }
    const next = record.data ?? record.messages ?? record.items
    if (next === undefined) return undefined
    current = next
  }
  return Array.isArray(current) ? current : undefined
}
