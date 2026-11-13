/**
 * OpenCode child-session agent runner.
 *
 * Every finder/verifier/sweep/synthesis call gets a fresh child session with
 * its own context. Nothing is shared except the prompt and the repository on
 * disk, which is the reference's isolation model for Agent-tool subagents.
 */
import type { AgentRequest, AgentRunner } from "./engine.ts"
import {
  extractJson,
  isSchemaEcho,
  normalizeCandidatesCall,
  normalizeDecisionsCall,
  normalizeGroupVerdictsCall,
  normalizeReportCall,
  normalizeVerdictCall,
  STEP_LIMIT_PLACEHOLDER,
} from "./json.ts"
import { SCHEMA_TOOL_NAMES, schemaExample } from "./schemas.ts"
import { sessionMessages, sessionRecord } from "./host.ts"
import { envInt } from "./finding.ts"

type AnyCtx = {
  session: {
    create(input: Record<string, unknown>): Promise<{ id: string }>
    get?(input: { sessionID: string }): Promise<unknown>
    prompt(input: Record<string, unknown>): Promise<unknown>
    wait(input: Record<string, unknown>): Promise<void>
    context(input: Record<string, unknown>): Promise<readonly unknown[]>
    interrupt(input: Record<string, unknown>): Promise<unknown>
    remove(input: Record<string, unknown>): Promise<void>
  }
  agent?: {
    get?(input: { agentID: string }): Promise<unknown>
  }
}

type ModelRef = { providerID: string; id: string; variant?: string }

/**
 * Accept both shapes the host may expose: the documented
 * `provider/model#variant` string and the Model.Ref record. The session API
 * only accepts the record, so a raw string would make every child create fail.
 */
export function modelRef(value: unknown): ModelRef | undefined {
  if (typeof value === "string") {
    const slash = value.indexOf("/")
    if (slash <= 0 || slash === value.length - 1) return undefined
    const providerID = value.slice(0, slash)
    const rest = value.slice(slash + 1)
    const hash = rest.indexOf("#")
    if (hash === -1) return { providerID, id: rest }
    const variant = rest.slice(hash + 1)
    const id = rest.slice(0, hash)
    // `provider/#variant` has no model id. An empty id makes every child
    // session.create fail, so reject it like the record form does.
    if (!id) return undefined
    // A trailing `#` is an empty variant, not a request for the variant named
    // "". Hosts match variants by exact id, so passing "" can make every child
    // fail to start.
    return variant ? { providerID, id, variant } : { providerID, id }
  }
  if (!value || typeof value !== "object") return undefined
  const record = value as { id?: unknown; modelID?: unknown; providerID?: unknown; variant?: unknown }
  const id =
    typeof record.id === "string" ? record.id : typeof record.modelID === "string" ? record.modelID : undefined
  const providerID = typeof record.providerID === "string" ? record.providerID : undefined
  if (!id || !providerID) return undefined
  return {
    providerID,
    id,
    ...(typeof record.variant === "string" && record.variant.length > 0
      ? { variant: record.variant }
      : {}),
  }
}

type RunnerOptions = {
  parentSessionID: string
  /** Fallback model for a role that has neither an agent model nor a role
   *  variant. This is normally the parent session's model. */
  model?: ModelRef
  /** Per-role override; return undefined to use the agent or fallback model. */
  modelFor?: (req: AgentRequest) => ModelRef | undefined
  /** Per-session typed results captured by the report_* tools. */
  schemaResults?: Map<string, unknown>
  /** Per-session validation-failure counts for the schema tools. */
  schemaFailures?: Map<string, number>
  /** Live review child session IDs, shared with the code_review recursion guard. */
  childSessions?: Set<string>
  /** Abort a child that produces no session activity for this long. 0 disables.
   *  This is a stall watchdog, not a wall-clock cap: healthy long work keeps
   *  re-arming it. Default 600s, matching Claude Code's foreground Agent
   *  watchdog. A max-effort step can reason for many minutes without a new
   *  transcript message, so a caller should also pass `activity`. */
  stallMs?: number
  /** Last observed stream event time for a child, in epoch milliseconds.
   *  `session.get().time.updated` only moves at turn boundaries, which makes a
   *  long single-step reasoning turn look stalled; the event stream moves on
   *  every reasoning/text/tool delta. */
  activity?: (sessionID: string) => number | undefined
  /** Poll interval for the idle/stall check. Tests set this lower. */
  pollMs?: number
  keepSessions?: boolean
  onLog?: (message: string) => void
}

type SchemaName = AgentRequest["schemaName"]

/**
 * Child sessions emit stream events continuously while the model reasons, but
 * `session.get().time.updated` only moves when a turn starts or ends. A
 * max-effort child can spend far longer than any reasonable watchdog inside a
 * single step, so liveness must come from the event stream: reasoning, text,
 * tool progress, step transitions, and usage updates. Without this, a healthy
 * 25-minute reasoning turn is indistinguishable from a hung provider and gets
 * interrupted at 10 minutes.
 */
const ACTIVITY_EVENTS = [
  "session.execution.started",
  "session.reasoning.delta",
  "session.text.delta",
  "session.step.started",
  "session.step.streamed",
  "session.step.ended",
  "session.tool.called",
  "session.tool.input.delta",
  "session.tool.progress",
  "session.tool.success",
  "session.tool.failed",
  "session.usage.updated",
]

type EventSource = {
  subscribe(options?: { types?: string[]; signal?: AbortSignal }): AsyncIterable<unknown>
}

type ActivityTracker = {
  /** Receipt time of the newest event for this session, if any. */
  last(sessionID: string): number | undefined
  /** Stop the subscription (plugin unload). */
  stop(): void
}

/**
 * Shared, process-wide activity index fed by the host event stream. The runner
 * reads it at each watchdog poll so a child that is streaming reasoning tokens
 * is never mistaken for a silent one.
 */
export function trackActivity(ctx: { event?: EventSource }): ActivityTracker {
  const seen = new Map<string, number>()
  const controller = new AbortController()
  const prune = (): void => {
    const cutoff = Date.now() - 60 * 60_000
    for (const [id, at] of seen) if (at < cutoff) seen.delete(id)
    // A long-lived server can outlive any plausible number of review children.
    // Keep the map bounded even if every entry is recent.
    while (seen.size > 500) {
      const oldest = seen.keys().next().value
      if (oldest === undefined) break
      seen.delete(oldest)
    }
  }
  const events = ctx.event
  if (events && typeof events.subscribe === "function") {
    void (async () => {
      try {
        for await (const event of events.subscribe({
          types: ACTIVITY_EVENTS,
          signal: controller.signal,
        })) {
          const record = event as { data?: { sessionID?: unknown } } | undefined
          const sessionID = record?.data?.sessionID
          if (typeof sessionID !== "string" || sessionID.length === 0) continue
          seen.set(sessionID, Date.now())
          if (seen.size > 500) prune()
        }
      } catch {
        // A host without the event stream, or a stream closed on unload, is
        // not a review failure: the watchdog falls back to session timestamps.
      }
    })()
  }
  return {
    last: (sessionID) => seen.get(sessionID),
    stop: () => controller.abort(),
  }
}

type SchemaSpec = {
  tool: string
  validate: (value: unknown) => string | undefined
  wrap: (value: unknown) => unknown
}

/**
 * One table per result kind. Keeping the tool name, validation, and shape
 * alias together makes adding a kind a single edit: TypeScript rejects a
 * missing entry instead of letting an unknown kind bypass validation.
 */
const SCHEMAS: Record<SchemaName, SchemaSpec> = {
  candidates: {
    tool: SCHEMA_TOOL_NAMES.candidates,
    validate: (value) => {
      const parsed = normalizeCandidatesCall(value, 64, { tolerateDropped: true })
      return parsed.ok ? undefined : parsed.error
    },
    wrap: (value) => {
      if (Array.isArray(value)) return { candidates: value }
      if (!value || typeof value !== "object") return value
      const record = value as Record<string, unknown>
      return !Array.isArray(record.candidates) && Array.isArray(record.findings)
        ? { candidates: record.findings }
        : value
    },
  },
  verdict: {
    tool: SCHEMA_TOOL_NAMES.verdict,
    validate: (value) => {
      const parsed = normalizeVerdictCall(value, { tolerateMissingEvidence: true })
      return parsed.ok ? undefined : parsed.error
    },
    wrap: (value) => value,
  },
  groupVerdicts: {
    tool: SCHEMA_TOOL_NAMES.groupVerdicts,
    validate: (value) => {
      const parsed = normalizeGroupVerdictsCall(value, 64, {
        tolerateMissingEvidence: true,
        tolerateDropped: true,
        tolerateOffset: true,
      })
      return parsed.ok ? undefined : parsed.error
    },
    wrap: (value) => {
      if (Array.isArray(value)) return { verdicts: value }
      if (!value || typeof value !== "object") return value
      const record = value as Record<string, unknown>
      return !Array.isArray(record.verdicts) && Array.isArray(record.results)
        ? { verdicts: record.results }
        : value
    },
  },
  report: {
    tool: SCHEMA_TOOL_NAMES.report,
    validate: (value) => {
      const parsed = normalizeReportCall(value)
      return parsed.ok ? undefined : parsed.error
    },
    wrap: (value) => {
      if (Array.isArray(value)) return { findings: value }
      if (!value || typeof value !== "object") return value
      const record = value as Record<string, unknown>
      return !Array.isArray(record.findings) && Array.isArray(record.candidates)
        ? { ...record, findings: record.candidates }
        : value
    },
  },
  decisions: {
    tool: SCHEMA_TOOL_NAMES.decisions,
    validate: (value) => {
      const parsed = normalizeDecisionsCall(value)
      return parsed.ok ? undefined : parsed.error
    },
    wrap: (value) => (Array.isArray(value) ? { decisions: value } : value),
  },
}

function validationError(schemaName: SchemaName, value: unknown): string | undefined {
  return SCHEMAS[schemaName]?.validate(value)
}

/** Reject JSON that parses but is not the result shape the role asked for. */
function normalizeShape(schemaName: SchemaName, value: unknown): unknown {
  return SCHEMAS[schemaName]?.wrap(value) ?? value
}

/**
 * The step-limited summary is prose, so it may omit the failure scenario the
 * validator requires. Put a placeholder on each otherwise-valid finding
 * instead of losing the whole angle to a schema rejection.
 */
function withFailurePlaceholders(schemaName: string, value: unknown): unknown {
  if (schemaName !== "candidates" && schemaName !== "report") return value
  if (!value || typeof value !== "object" || Array.isArray(value)) return value
  const record = value as Record<string, unknown>
  const key = schemaName === "candidates" ? "candidates" : "findings"
  if (!Array.isArray(record[key])) return value
  return {
    ...record,
    [key]: record[key].map((item) => {
      if (!item || typeof item !== "object" || Array.isArray(item)) return item
      const finding = item as Record<string, unknown>
      if (typeof finding.failure_scenario === "string" && finding.failure_scenario.trim()) return item
      return { ...finding, failure_scenario: STEP_LIMIT_PLACEHOLDER }
    }),
  }
}

function withSchemaInstruction(prompt: string, schemaName: SchemaName, role?: string): string {
  const tool = SCHEMAS[schemaName]?.tool
  if (!tool) return prompt
  // Adapted from Claude Code's structured-output subagent contract. OpenCode
  // does not expose plugin-registered tools to every child agent, so the
  // orchestrator accepts the same JSON object from the final text response.
  // This is the fallback the runner's `extractJson` salvage already uses.
  const work =
    role === "synthesize"
      ? "- Do not explore, read files, or run commands; use only the review material above and return the object."
      : role === "format"
        ? "- Do not explore, read files, or run commands; convert only the text above into the object."
        : role === "verifier" || role === "sweep"
          ? "- Use read-only inspection (read, glob, grep, git diff/log/show/blame), then return the object."
          : "- Do your work (read files, run commands, etc.), then return the object."
  return `${prompt}

## Structured output

CRITICAL: Return exactly one JSON object matching the schema. If the \`${tool}\` tool is available in your tool list, call it exactly once with the object. If it is not available, put the JSON object in your final text response with no prose around it. The review orchestrator accepts either form.
Expected shape: \`${schemaExample(schemaName)}\`
${work}
- Do not put the answer in prose or a Markdown fence. The review orchestrator reads the tool call or the final text JSON.
- If the schema validation fails, read the error and return a corrected object.
- You have a limited number of steps. Reserve the final step for this result; if you are close to the limit, stop exploring and submit what you have.
- After returning the object successfully, end your turn. No acknowledgment needed.`
}

function retryInstruction(schemaName: SchemaName): string {
  const tool = SCHEMAS[schemaName]?.tool
  return `Your previous turn did not submit the required structured result. Return the JSON object now: call the \`${tool}\` tool if it is available; otherwise reply with only the JSON object. Do not do more exploration, and do not answer in prose.
Expected shape: \`${schemaExample(schemaName)}\``
}

/**
 * Record a host `wait` hint without closing over the polling activation. A
 * local `.then(() => (waitResolved = true))` keeps the whole waitForChild
 * scope, including the settled transcript with the embedded diff, alive for as
 * long as the host leaves the wait pending.
 */
function trackWait(wait: Promise<void>, state: { resolved: boolean }): void {
  void wait.then(
    () => {
      state.resolved = true
    },
    () => {
      /* a rejected wait is not a gone child; keep polling */
    },
  )
}

/** Text carried by a transcript message, from either its `text` or its parts. */
function messageText(m: unknown): string {
  const record = m as { text?: unknown; content?: unknown }
  if (typeof record?.text === "string") return record.text
  if (!Array.isArray(record?.content)) return ""
  // Walk text parts only. Stringifying a tool result to search it would
  // serialize the embedded diff or file read on every turn.
  return record.content
    .filter((p): p is { type: string; text: string } => {
      const part = p as { type?: unknown; text?: unknown }
      return part?.type === "text" && typeof part.text === "string"
    })
    .map((p) => p.text)
    .join("\n")
}

function assistantText(messages: readonly unknown[]): string {
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i] as { type?: string; content?: unknown }
    if (m?.type !== "assistant" || !Array.isArray(m.content)) continue
    const text = messageText(m).trim()
    if (text) return text
  }
  return ""
}

/**
 * OpenCode injects `CRITICAL - MAXIMUM STEPS REACHED ... Respond with text only`
 * on the final step. The message stays in the session context, so a retry
 * prompt is ignored and the model keeps answering in prose. Detect it before
 * spending two more turns on the same session.
 */
function hitStepLimit(messages: readonly unknown[]): boolean {
  // The injected notice stays in context, so a retry can see it many messages
  // later. Scan the whole transcript; `startsWith` prevents a diff that merely
  // quotes the literal from counting as the injected notice.
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messageText(messages[i]).trimStart().startsWith("CRITICAL - MAXIMUM STEPS REACHED")) return true
  }
  return false
}

export function makeRunner(ctx: AnyCtx, opts: RunnerOptions): AgentRunner {
  // Claude's Agent tool is bounded by maxTurns, not a wall-clock cap. The
  // per-agent `steps` field is the equivalent; cancellation is the abort signal.
  // Sessions are removed by default: a long review creates dozens of them, and
  // keeping them is a debugging aid, not a normal-mode cost.
  const keep = opts.keepSessions ?? false
  const log = opts.onLog ?? (() => {})
  const stallMs =
    opts.stallMs ??
    (() => {
      const n = envInt("CODE_REVIEW_STALL_MS")
      // Keep an explicit 0: it is the documented way to disable the watchdog.
      // `time.updated` changes per turn, not per streamed token, so a max-effort
      // final answer can legitimately be silent for minutes. 180s interrupted
      // healthy finders in self-review 5 and 6; 10 minutes still catches a
      // provider that has genuinely stopped responding.
      return n === undefined ? 600_000 : n
    })()
  // A stall is measured in minutes, so a seconds-scale poll is enough. A
  // 500ms poll fetched the child's full context twice a second on hosts
  // without `time`, transferring the embedded diff for the whole run.
  const pollMs = opts.pollMs ?? 2000
  // Resolve the model once per agent. An agent's own `model` is the most
  // specific choice; otherwise a role variant, otherwise the parent model.
  // A child created without a model produced an empty response in OpenCode,
  // so the fallback must be passed explicitly.
  const agentModels = new Map<string, Promise<ModelRef | undefined>>()
  const modelFor = async (req: AgentRequest): Promise<ModelRef | undefined> => {
    let pending = agentModels.get(req.agent)
    if (!pending) {
      pending = (async () => {
        if (!ctx.agent?.get) return undefined
        const info = await ctx.agent.get({ agentID: req.agent })
        return modelRef(sessionRecord(info)?.model)
      })()
      // Cache the in-flight lookup so concurrently started children share one
      // host call. A rejection is removed so the next request retries, as the
      // transient-failure test requires.
      agentModels.set(req.agent, pending)
      pending.catch(() => {
        if (agentModels.get(req.agent) === pending) agentModels.delete(req.agent)
      })
    }
    let agentModel: ModelRef | undefined
    try {
      agentModel = await pending
    } catch {
      /* fall through to the role/parent fallback and retry on the next turn */
    }
    return agentModel ?? opts.modelFor?.(req) ?? opts.model
  }

  /**
   * `session.wait` can miss an already-idle child, and a child removed after a
   * failed retry leaves the wait pending forever. Race it with a session poll
   * so a completed or vanished child cannot hang the engine. The same poll is
   * the stall watchdog: if the session's `updated` timestamp (or, on hosts
   * without `get`, its message count) does not change for `stallMs`, interrupt
   * the child. Healthy long work keeps re-arming it, so this is not a
   * wall-clock cap.
   */
  type SessionTime = { busy?: number; idle?: number; updated?: number }
  const sessionTime = async (sessionID: string): Promise<SessionTime | undefined> => {
    if (!ctx.session.get) return undefined
    try {
      return sessionRecord(await ctx.session.get({ sessionID }))?.time
    } catch {
      return undefined
    }
  }

  /**
   * On hosts whose session record omits `time`, the retry path needs a message
   * count from before the prompt: an already-finished assistant message from
   * the previous turn must not count as this turn's answer.
   */
  const sessionBaseline = async (
    sessionID: string,
    opts: { messages?: number } = {},
  ): Promise<{ time?: SessionTime; messages?: number }> => {
    const time = await sessionTime(sessionID)
    // A session that was just created cannot have a pre-prompt message. The
    // caller can supply that known zero instead of transferring the child's
    // full transcript (which may include the diff-sized prompt) over RPC.
    if (opts.messages !== undefined) {
      return { ...(time !== undefined ? { time } : {}), messages: opts.messages }
    }
    // Keep the message count even on hosts with timestamps: `session.wait` may
    // resolve before the queued turn starts, and the transcript is the only
    // way to tell that turn's answer from the previous one.
    try {
      const messages = sessionMessages(await ctx.session.context({ sessionID }))
      if (!messages) return time !== undefined ? { time } : {}
      return { ...(time !== undefined ? { time } : {}), messages: messages.length }
    } catch {
      return time !== undefined ? { time } : {}
    }
  }

  type WaitResult = {
    outcome: "idle" | "stalled" | "gone"
    /** The transcript that proved completion, so the caller can parse it
     *  without fetching the same diff-sized context a second time. */
    messages?: readonly unknown[]
  }

  const waitForChild = async (
    sessionID: string,
    label: string,
    baseline?: SessionTime,
    baselineMessages?: number,
    /** A typed schema result is itself a completion signal: the child may
     *  submit it without another assistant text message. */
    hasResult?: () => boolean,
    signal?: AbortSignal,
  ): Promise<WaitResult> => {
    let settled = false
    let outcome: "idle" | "stalled" | "gone" = "idle"
    let settledMessages: readonly unknown[] | undefined
    let lastActivity = Date.now()
    let lastUpdated = -1
    let lastLength = -1
    const interrupt = async (): Promise<void> => {
      log(`[code-review-opencode] ${label}: no activity for ${stallMs}ms; interrupting the child`)
      try {
        await ctx.session.interrupt({ sessionID })
      } catch {
        /* the session may already be gone */
      }
      outcome = "stalled"
      settled = true
    }
    // `session.wait` is only a hint: it can resolve as soon as the prompt is
    // queued, before the child's turn starts. A rejection is not proof the
    // child vanished either. Settle only from a new transcript message or a
    // real busy/idle edge; the stall watchdog bounds the wait.
    const waitState = { resolved: false }
    trackWait(ctx.session.wait({ sessionID }), waitState)
    // Fallback for hosts whose session.get omits `time`: use the message
    // stream instead of declaring the live child gone.
    const settleFromMessages = async (): Promise<boolean> => {
      let messages: readonly unknown[] = []
      try {
        const read = sessionMessages(await ctx.session.context({ sessionID }))
        // A host returning an unexpected envelope shape is a read failure, not
        // an empty transcript that proves completion.
        if (!read) return false
        messages = read
      } catch {
        // A transient context failure is not proof the child is gone. The
        // stall watchdog or the get-failure path will bound the wait.
        return false
      }
      if (messages.length !== lastLength) {
        lastLength = messages.length
        lastActivity = Date.now()
      }
      const last = messages[messages.length - 1] as { type?: string; finish?: unknown } | undefined
      const afterBaseline = baselineMessages === undefined || messages.length > baselineMessages
      if (
        afterBaseline &&
        last &&
        (last.type === "idle" ||
          (last.type === "assistant" && last.finish !== undefined && last.finish !== "tool-calls"))
      ) {
        settled = true
        settledMessages = messages
        return true
      }
      if (stallMs > 0 && Date.now() - lastActivity >= stallMs) {
        await interrupt()
        return true
      }
      return false
    }
    const poll = async (): Promise<void> => {
      // Hosts without `time` are polled by reading the transcript, which can
      // include the diff-sized prompt. Back off exponentially instead of
      // copying that whole context every 2 seconds for an hour-long child.
      let messageDelay = pollMs
      let getFailures = 0
      while (!settled) {
        // Cancellation must work on hosts without `session.interrupt`: the
        // abort listener cannot stop the child there, but it can stop waiting.
        if (signal?.aborted) {
          settled = true
          return
        }
        if (hasResult?.()) {
          settled = true
          return
        }
        // Stream deltas are the real liveness signal for a long reasoning
        // step. `time.updated` only changes at turn boundaries, so on its own
        // it reports a healthy max-effort child as stalled after 10 minutes.
        const streamed = opts.activity?.(sessionID)
        if (streamed !== undefined && streamed > lastActivity) lastActivity = streamed
        if (ctx.session.get) {
          let info: unknown
          try {
            info = await ctx.session.get({ sessionID })
          } catch {
            // A single RPC hiccup is not proof the child vanished. Only after
            // repeated failures fall back to the transcript/gone decision.
            getFailures++
            if (getFailures >= 3) {
              if (await settleFromMessages()) return
              outcome = "gone"
              settled = true
              return
            }
            await new Promise((resolve) => setTimeout(resolve, pollMs))
            continue
          }
          const data = sessionRecord(info)
          if (!data) {
            getFailures++
            if (getFailures >= 3) {
              if (await settleFromMessages()) return
              outcome = "gone"
              settled = true
              return
            }
            await new Promise((resolve) => setTimeout(resolve, pollMs))
            continue
          }
          getFailures = 0
          const time = data.time
          if (!time) {
            if (await settleFromMessages()) return
            await new Promise((resolve) => setTimeout(resolve, messageDelay))
            messageDelay = Math.min(messageDelay * 2, 30_000)
            continue
          }
          const updated = typeof time.updated === "number" ? time.updated : 0
          if (updated !== lastUpdated) {
            lastUpdated = updated
            lastActivity = Date.now()
          }
          // A host that only reports created/updated has no busy/idle edge to
          // wait for; use its transcript, which is also the completion signal.
          if (time.busy === undefined && time.idle === undefined) {
            if (await settleFromMessages()) return
            if (stallMs > 0 && Date.now() - lastActivity >= stallMs) {
              await interrupt()
              return
            }
            // This branch reads the full transcript, so it needs the same
            // exponential backoff as the no-time branch above.
            await new Promise((resolve) => setTimeout(resolve, messageDelay))
            messageDelay = Math.min(messageDelay * 2, 30_000)
            continue
          }
          // Compare against the timestamps read before the prompt. A retry
          // still sees the previous turn's idle >= busy; only a new busy/idle
          // edge means this prompt completed. `updated` changes when the
          // prompt is admitted, so it cannot prove the turn finished.
          // A missing baseline (a transient session.get failure) is not an
          // idle edge. Treating it as one lets the previous turn's
          // `idle >= busy` settle the retry before the new turn starts; fall
          // through to the transcript check instead.
          const changed =
            baseline !== undefined &&
            (time.busy !== baseline.busy || time.idle !== baseline.idle)
          if (changed && time.busy !== undefined && time.idle !== undefined && time.idle >= time.busy) {
            settled = true
            return
          }
          if (changed && time.busy === undefined && time.idle !== undefined) {
            settled = true
            return
          }
          // `session.wait` may have resolved before the queued turn started.
          // Before trusting it, require a new assistant message after the
          // pre-prompt baseline. Each check reads the full transcript (the
          // prompt embeds the diff), so use the same exponential backoff as
          // the other transcript-reading branches.
          if (waitState.resolved) {
            // The hint triggered one transcript read; clear it so later
            // iterations use the backoff path instead of re-reading the full
            // transcript every poll.
            waitState.resolved = false
            if (await settleFromMessages()) return
            if (stallMs > 0 && Date.now() - lastActivity >= stallMs) {
              await interrupt()
              return
            }
            await new Promise((resolve) => setTimeout(resolve, messageDelay))
            messageDelay = Math.min(messageDelay * 2, 30_000)
            continue
          }
          if (stallMs > 0 && Date.now() - lastActivity >= stallMs) {
            await interrupt()
            return
          }
        } else {
          if (await settleFromMessages()) return
          await new Promise((resolve) => setTimeout(resolve, messageDelay))
          messageDelay = Math.min(messageDelay * 2, 30_000)
          continue
        }
        await new Promise((resolve) => setTimeout(resolve, pollMs))
      }
    }
    await poll()
    return settledMessages !== undefined ? { outcome, messages: settledMessages } : { outcome }
  }

  /**
   * Create one child, arm cancellation, and tear it down on every exit path.
   * The finder/verifier path and the step-limit formatter share this lifecycle
   * so a cleanup or watchdog fix cannot land in only one of them.
   */
  const runInChild = async <T>(
    req: AgentRequest,
    label: string,
    run: (sessionID: string) => Promise<T | null>,
  ): Promise<T | null> => {
    // The attempt label (`reuse retry`, `reuse (format)`) must not reach the
    // label-keyed role-variant lookup: a retry has to run at the same effort as
    // the attempt it replaces.
    const model = await modelFor(req)
    const created = await ctx.session.create({
      parentID: opts.parentSessionID,
      title: `code-review-opencode · ${label}`,
      agent: req.agent,
      ...(model ? { model } : {}),
    })
    // `session.create` may return the record directly or the host's
    // `{location, data}` envelope, like every other session read.
    const id = sessionRecord(created)?.id
    if (!id) throw new Error("session.create returned no session id")
    opts.childSessions?.add(id)
    const onAbort = () => {
      void ctx.session.interrupt?.({ sessionID: id })?.catch(() => {})
    }
    req.signal?.addEventListener("abort", onAbort, { once: true })
    try {
      if (req.signal?.aborted) {
        onAbort()
        return null
      }
      return await run(id)
    } finally {
      req.signal?.removeEventListener("abort", onAbort)
      opts.schemaResults?.delete(id)
      opts.schemaFailures?.delete(id)
      opts.childSessions?.delete(id)
      if (!keep) await ctx.session.remove?.({ sessionID: id })?.catch(() => {})
    }
  }

  return async (req: AgentRequest): Promise<unknown | null> => {
    if (req.signal?.aborted) return null
    const startedAt = Date.now()
    try {
      const runAttempt = async (
        label: string,
      ): Promise<{ value: unknown | null; stalled: boolean }> => {
        let stalled = false
        const value = await runInChild(req, label, async (sessionID) => {
        // A session created above has no pre-prompt messages; skip the
        // transcript RPC that would only confirm the known zero.
        const baseline = await sessionBaseline(sessionID, { messages: 0 })
        await ctx.session.prompt({ sessionID, text: withSchemaInstruction(req.prompt, req.schemaName, req.role) })
        const waited = await waitForChild(
          sessionID,
          req.label,
          baseline.time,
          baseline.messages,
          () => opts.schemaResults?.has(sessionID) === true,
          req.signal,
        )
        const waitOutcome = waited.outcome
        if (waitOutcome === "stalled") stalled = true
        if (req.signal?.aborted) return null
        let cachedMessages = waited.messages
        // The transcript we already read is the pre-prompt baseline for the
        // next retry. Reusing its count avoids transferring the diff-sized
        // context again merely to learn how many messages preceded the retry.
        let messageCount = waited.messages?.length ?? 0

      const captured = (): unknown | undefined => {
        if (!sessionID) return undefined
        const value = opts.schemaResults?.get(sessionID)
        if (value !== undefined) opts.schemaResults?.delete(sessionID)
        // A tool call can echo the prompt's `Expected shape` example. The text
        // path already rejects that echo; the tool path must not accept it as
        // a real result, or a placeholder merge becomes the report.
        return value === undefined || isSchemaEcho(value) ? undefined : value
      }
      let lastText = ""
      let stepLimited = false
      const fromText = async (): Promise<unknown | null> => {
        if (!sessionID) return null
        // waitForChild may already have read the transcript to detect
        // completion. Reuse it instead of paying a second full-context RPC.
        let read = cachedMessages
        if (read === undefined) {
          try {
            read = await ctx.session.context({ sessionID })
          } catch (error) {
            log(
              `[code-review-opencode] ${req.label}: transcript read failed (${error instanceof Error ? error.message : String(error)})`,
            )
            return null
          }
        }
        const messages = sessionMessages(read)
        cachedMessages = undefined
        if (messages === undefined) {
          log(`[code-review-opencode] ${req.label}: unrecognized transcript envelope`)
          return null
        }
        messageCount = messages.length
        stepLimited = stepLimited || hitStepLimit(messages)
        const text = assistantText(messages)
        lastText = text
        if (!text) {
          log(`[code-review-opencode] ${req.label}: empty assistant response`)
          return null
        }
        const raw = extractJson(text)
        if (raw === null) {
          const preview = text.replace(/\s+/g, " ").slice(0, 240)
          log(`[code-review-opencode] ${req.label}: no JSON found in assistant response (${text.length} chars): ${preview}`)
          return null
        }
        const parsed = normalizeShape(req.schemaName, raw)
        if (parsed === null) {
          log(`[code-review-opencode] ${req.label}: JSON found but did not match the ${req.schemaName} shape`)
          return null
        }
        const error = validationError(req.schemaName, parsed)
        if (error) {
          log(`[code-review-opencode] ${req.label}: JSON response did not match the ${req.schemaName} result shape (${error})`)
          return null
        }
        return parsed
      }

      // A step-limited session cannot be recovered by prompting it again: the
      // CRITICAL summary instruction stays in context. A fresh child with the
      // previous summary and a small context can still turn the prose into the
      // schema without re-reading the diff.
      const formatFresh = async (text: string): Promise<unknown | null> => {
        if (!text) return null
        const preservation =
          req.schemaName === "candidates" || req.schemaName === "report"
            ? `Preserve every finding. Each candidate must include \`file\`, \`summary\`, and \`failure_scenario\`; when the text does not state a failure scenario, use the closest concrete consequence it implies (or "${STEP_LIMIT_PLACEHOLDER}") rather than omitting the field.`
            : req.schemaName === "verdict" || req.schemaName === "groupVerdicts"
              ? "Preserve every verdict and its evidence; do not omit a verdict whose evidence is quoted in the text."
              : "Preserve every decision and its merge list; do not drop an index the text names."
        const prompt = `A previous review attempt did not submit a parseable structured result (it may have reached its step limit or replied in prose). Convert the completed review below into the required structured result. Do not explore, do not read files, and do not run commands. Use only this text.

${preservation}

Review:
${text}`
        return runInChild(req, `${req.label} (format)`, async (id) => {
          const baseline = await sessionBaseline(id, { messages: 0 })
          await ctx.session.prompt({
            sessionID: id,
            // `format` suppresses the "do your work (read files, run commands)"
            // line; this child is told to use only the supplied text.
            text: withSchemaInstruction(prompt, req.schemaName, "format"),
          })
          if (req.signal?.aborted) return null
          const waited = await waitForChild(
            id,
            `${req.label} (format)`,
            baseline.time,
            baseline.messages,
            () => opts.schemaResults?.has(id) === true,
            req.signal,
          )
          if (req.signal?.aborted) return null
          const direct = opts.schemaResults?.get(id)
          if (direct !== undefined) {
            opts.schemaResults?.delete(id)
            return direct
          }
          // A `gone` wait outcome can still leave a readable transcript (a
          // transient get/wait miss). Only a watchdog stall proves there is no
          // answer; otherwise try the context before discarding the child.
          if (waited.outcome === "stalled") return null
          let read = waited.messages
          if (read === undefined) {
            try {
              read = await ctx.session.context({ sessionID: id })
            } catch (error) {
              log(
                `[code-review-opencode] ${req.label}: formatter transcript read failed (${error instanceof Error ? error.message : String(error)})`,
              )
              return null
            }
          }
          const messages = sessionMessages(read)
          if (messages === undefined) {
            log(`[code-review-opencode] ${req.label}: unrecognized formatter transcript envelope`)
            return null
          }
          const answer = assistantText(messages)
          if (!answer) return null
          const parsed = withFailurePlaceholders(
            req.schemaName,
            normalizeShape(req.schemaName, extractJson(answer)),
          )
          if (parsed === null) return null
          const error = validationError(req.schemaName, parsed)
          return error ? null : parsed
        })
      }

      const direct = captured()
      if (direct !== undefined) return direct
      const salvaged = await fromText()
      if (salvaged !== null) return salvaged

      // A watchdog interrupt is a timeout, not a validation failure: prompting
      // the same interrupted session again just stalls for another full window.
      // Record the failure and let the engine mark the run partial.
      if (waitOutcome === "stalled") {
        log(`[code-review-opencode] ${req.label}: child stalled; not retrying the same session`)
        return null
      }

      // Try the small formatter child for every schema, not only candidates
      // and reports: a verifier or synthesizer that answers in prose would
      // otherwise be retried in place and eventually dropped. Formatting costs
      // one small child only after the original child failed; the schema-tool
      // failure count belongs to the original child and must not suppress it.
      if (lastText) {
        log(
          `[code-review-opencode] ${req.label}: ${stepLimited ? "step limit reached" : "no structured result"}; trying a fresh formatter`,
        )
        const formatted = await formatFresh(lastText)
        if (formatted !== null) return formatted
        if (stepLimited) {
          log(`[code-review-opencode] ${req.label}: fresh formatter could not recover the summary`)
          return null
        }
        log(`[code-review-opencode] ${req.label}: fresh formatter could not recover; retrying the same session`)
      }

      // The reference's StructuredOutput loop re-prompts on a validation
      // error; allow up to two retries for an empty or wrong-shaped response.
      // The schema-failure counter still caps a child that keeps calling the
      // tool with invalid payloads.
      for (let attempt = 0; attempt < 2; attempt++) {
        const failures = sessionID ? (opts.schemaFailures?.get(sessionID) ?? 0) : 0
        if (req.signal?.aborted || failures >= 3) break
        log(`[code-review-opencode] ${req.label}: no structured result captured; retrying the tool call (attempt ${attempt + 1})`)
        const retryBaseline = await sessionBaseline(sessionID, { messages: messageCount })
        await ctx.session.prompt({ sessionID, text: retryInstruction(req.schemaName) })
        const retriedWait = await waitForChild(
          sessionID,
          req.label,
          retryBaseline.time,
          retryBaseline.messages,
          () => opts.schemaResults?.has(sessionID) === true,
          req.signal,
        )
        if (req.signal?.aborted) return null
        const retried = captured()
        if (retried !== undefined) return retried
        cachedMessages = retriedWait.messages
        const recovered = await fromText()
        if (recovered !== null) return recovered
        if (retriedWait.outcome === "stalled") {
          stalled = true
          log(`[code-review-opencode] ${req.label}: retry stalled; giving up on this child`)
          break
        }
        if (stepLimited) {
          log(`[code-review-opencode] ${req.label}: retry hit the step limit; trying a fresh formatter`)
          const formatted = await formatFresh(lastText)
          if (formatted !== null) return formatted
          break
        }
      }

        const failures = opts.schemaFailures?.get(sessionID) ?? 0
        log(`[code-review-opencode] ${req.label}: unusable structured output (${failures} validation failure(s))`)
        return null
        })
        return { value, stalled }
      }
      const first = await runAttempt(req.label)
      if (first.value !== null || !first.stalled) return first.value
      // A stall is a provider/session failure, not a schema decision. One
      // fresh child can still complete the same work.
      log(`[code-review-opencode] ${req.label}: stalled; retrying once with a fresh child`)
      return (await runAttempt(`${req.label} retry`)).value
    } catch (error) {
      log(`[code-review-opencode] ${req.label}: ${error instanceof Error ? error.message : String(error)}`)
      return null
    } finally {
      log(`[code-review-opencode] ${req.label}: ${((Date.now() - startedAt) / 1000).toFixed(1)}s`)
    }
  }
}
