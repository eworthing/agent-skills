import { test } from "node:test"
import assert from "node:assert/strict"
import { makeRunner, modelRef, trackActivity } from "../.opencode/plugins/code-review-opencode/runner.ts"
import type { AgentRequest } from "../.opencode/plugins/code-review-opencode/engine.ts"

type Msg = { type: string; content: Array<{ type: string; text: string }>; finish?: string }

function request(overrides: Partial<AgentRequest> = {}): AgentRequest {
  return {
    role: "finder",
    label: "angle-A",
    phase: "Find",
    prompt: "review this",
    agent: "review-finder",
    schemaName: "candidates",
    ...overrides,
  }
}

function fakeCtx(
  agentModels: Record<string, unknown> = {},
  opts: {
    hangWait?: boolean
    busyGet?: boolean
    idleGet?: boolean
    waitMs?: number
    agentGetFailures?: number
    interruptThrows?: boolean
    removeThrows?: boolean
    removeHangs?: boolean
    requireRemoveReceiver?: boolean
  } = {},
) {
  let next = 0
  let onPrompt: ((sessionID: string, text: string) => void) | undefined
  let agentGetFailures = opts.agentGetFailures ?? 0
  const sessions = new Map<string, Msg[]>()
  const created: string[] = []
  const createdInputs: Array<Record<string, unknown>> = []
  const removed: string[] = []
  const interrupted: string[] = []
  const prompts: Array<{ sessionID: string; text: string }> = []
  const push = (sessionID: string, text: string) => {
    const list = sessions.get(sessionID) ?? []
    list.push({ type: "assistant", content: [{ type: "text", text }], finish: "stop" })
    sessions.set(sessionID, list)
  }
  const pushStepLimit = (sessionID: string) => {
    const list = sessions.get(sessionID) ?? []
    list.push({
      type: "user",
      text: "CRITICAL - MAXIMUM STEPS REACHED The maximum number of steps allowed for this task has been reached. Tools are disabled until next user input. Respond with text only.",
    })
    sessions.set(sessionID, list)
  }
  const pushUser = (sessionID: string, text: string) => {
    const list = sessions.get(sessionID) ?? []
    list.push({ type: "user", text })
    sessions.set(sessionID, list)
  }
  const session = {
    async create(input: Record<string, unknown>) {
      const id = `ses_${++next}`
      created.push(id)
      createdInputs.push(input)
      sessions.set(id, [])
      return { id }
    },
    async prompt(input: { sessionID: string; text: string }) {
      prompts.push(input)
      onPrompt?.(input.sessionID, input.text)
    },
    async wait() {
      if (opts.hangWait) return new Promise<void>(() => {})
      if (opts.waitMs) await new Promise((resolve) => setTimeout(resolve, opts.waitMs))
    },
    async context(input: { sessionID: string }) {
      return sessions.get(input.sessionID) ?? []
    },
    async interrupt(input: { sessionID: string }) {
      interrupted.push(input.sessionID)
      if (opts.interruptThrows) throw new Error("session already removed")
    },
    async remove(input: { sessionID: string }) {
      if (opts.requireRemoveReceiver && this !== session) throw new Error("lost receiver")
      removed.push(input.sessionID)
      if (opts.removeThrows) throw new Error("session already removed")
      if (opts.removeHangs) return new Promise<void>(() => {})
    },
    ...(opts.busyGet || opts.idleGet
      ? {
          async get() {
            return opts.idleGet
              ? { data: { time: { idle: 1, updated: 1 } } }
              : { data: { time: { busy: 1, updated: 1 } } }
          },
        }
      : {}),
  }
  const ctx = {
    session,
    agent: {
      async get({ agentID }: { agentID: string }) {
        if (agentGetFailures > 0) {
          agentGetFailures--
          throw new Error("host not ready")
        }
        return { data: { model: agentModels[agentID] } }
      },
    },
  }
  return {
    ctx,
    created,
    createdInputs,
    removed,
    interrupted,
    prompts,
    push,
    pushStepLimit,
    pushUser,
    setOnPrompt: (fn: typeof onPrompt) => (onPrompt = fn),
  }
}

test("a trailing # does not create an empty model variant", () => {
  assert.deepEqual(modelRef("opencode-go/deepseek-v4.1-flash#"), {
    providerID: "opencode-go",
    id: "deepseek-v4.1-flash",
  })
  assert.deepEqual(modelRef({ providerID: "p", id: "m", variant: "" }), {
    providerID: "p",
    id: "m",
  })
})

test("a model ref with no id before the variant is rejected", () => {
  assert.equal(modelRef("provider/#max"), undefined)
  assert.equal(modelRef({ providerID: "p", id: "", variant: "max" }), undefined)
})

test("trackActivity ignores sessions outside the review child set", async () => {
  const ctx = {
    event: {
      async *subscribe() {
        yield { type: "session.reasoning.delta", data: { sessionID: "other" } }
        yield { type: "session.reasoning.delta", data: { sessionID: "ses_child" } }
      },
    },
  }
  const tracked = new Set(["ses_child"])
  const tracker = trackActivity(ctx, { shouldTrack: (id) => tracked.has(id) })
  await new Promise((resolve) => setTimeout(resolve, 20))
  assert.equal(tracker.last("other"), undefined)
  assert.ok(tracker.last("ses_child") !== undefined)
})

test("a captured schema result wins over assistant text", async () => {
  const fake = fakeCtx()
  const schemaResults = new Map<string, unknown>()
  fake.setOnPrompt((id) => {
    schemaResults.set(id, { candidates: [{ file: "a.ts", summary: "s", failure_scenario: "f" }] })
    fake.push(id, "prose that should be ignored")
  })
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent", schemaResults })
  const value = (await runner(request())) as { candidates: unknown[] }
  assert.equal(value.candidates.length, 1)
  assert.equal(fake.prompts.length, 1)
  assert.match(fake.prompts[0].text, /If it is not available, put the JSON object in your final text response/)
  assert.deepEqual(fake.removed, ["ses_1"])
})

test("a synchronous session.remove failure keeps the captured result", async () => {
  const fake = fakeCtx({}, { removeThrows: true })
  fake.setOnPrompt((id) =>
    fake.push(id, '{"candidates":[{"file":"a.ts","summary":"s","failure_scenario":"f"}]}'),
  )
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent" })
  const value = (await runner(request())) as { candidates: unknown[] }
  assert.equal(value.candidates.length, 1)
  assert.deepEqual(fake.removed, ["ses_1"])
})

test("session.remove keeps its receiver", async () => {
  const fake = fakeCtx({}, { requireRemoveReceiver: true })
  fake.setOnPrompt((id) =>
    fake.push(id, '{"candidates":[{"file":"a.ts","summary":"s","failure_scenario":"f"}]}'),
  )
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent" })
  const value = (await runner(request())) as { candidates: unknown[] }
  assert.equal(value.candidates.length, 1)
  assert.deepEqual(fake.removed, ["ses_1"])
})

test("a hanging session.remove is bounded", async () => {
  const fake = fakeCtx({}, { removeHangs: true })
  fake.setOnPrompt((id) =>
    fake.push(id, '{"candidates":[{"file":"a.ts","summary":"s","failure_scenario":"f"}]}'),
  )
  const runner = makeRunner(fake.ctx, {
    parentSessionID: "ses_parent",
    cleanupTimeoutMs: 10,
  })
  const value = (await runner(request())) as { candidates: unknown[] }
  assert.equal(value.candidates.length, 1)
})

test("a synchronous interrupt failure does not escape cancellation", async () => {
  const fake = fakeCtx({}, { hangWait: true, interruptThrows: true })
  fake.setOnPrompt(() => {})
  const controller = new AbortController()
  const runner = makeRunner(fake.ctx, {
    parentSessionID: "ses_parent",
    pollMs: 1,
    stallMs: 0,
  })
  const pending = runner(request({ signal: controller.signal }))
  setTimeout(() => controller.abort(), 10)
  assert.equal(await pending, null)
  assert.deepEqual(fake.interrupted, ["ses_1"])
})

test("assistant JSON is salvaged without a retry", async () => {
  const fake = fakeCtx()
  fake.setOnPrompt((id) =>
    fake.push(id, '```json\n{"candidates":[{"file":"a.ts","summary":"s","failure_scenario":"f"}]}\n```'),
  )
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent" })
  const value = (await runner(request())) as { candidates: unknown[] }
  assert.equal(value.candidates.length, 1)
  assert.equal(fake.prompts.length, 1)
  assert.deepEqual(fake.removed, ["ses_1"])
})

test("a missing structured result triggers one retry and uses the captured value", async () => {
  const fake = fakeCtx()
  const schemaResults = new Map<string, unknown>()
  fake.setOnPrompt((id, text) => {
    if (text.includes("did not submit")) schemaResults.set(id, { verdict: "CONFIRMED", evidence: "retried" })
    else fake.push(id, "I could not decide.")
  })
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent", schemaResults })
  const value = await runner(request({ role: "verifier", schemaName: "verdict" }))
  assert.deepEqual(value, { verdict: "CONFIRMED", evidence: "retried" })
  // The prose verifier now gets a small formatter child before the same-session
  // retry; the formatter prompt contains "did not submit", so the fake answers
  // it with the captured verdict.
  assert.equal(fake.prompts.length, 2)
  assert.deepEqual(fake.removed, ["ses_2", "ses_1"])
})

test("JSON with the wrong shape triggers the retry instead of counting as a result", async () => {
  const fake = fakeCtx()
  fake.setOnPrompt((id, text) => {
    if (text.includes("did not submit")) {
      fake.push(id, '```json\n{"candidates":[{"file":"a.ts","summary":"s","failure_scenario":"f"}]}\n```')
    } else {
      fake.push(id, 'the config says {"enabled":true}')
    }
  })
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent" })
  const value = (await runner(request())) as { candidates: unknown[] }
  assert.equal(value.candidates.length, 1)
  assert.equal(fake.prompts.length, 2)
})

test("the retry is skipped after three schema validation failures", async () => {
  const fake = fakeCtx()
  const schemaFailures = new Map<string, number>()
  fake.setOnPrompt((id) => {
    schemaFailures.set(id, 3)
    fake.push(id, "no json here")
  })
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent", schemaFailures })
  const value = await runner(request())
  assert.equal(value, null)
  // The fresh formatter still gets one chance; the same-session retry is the
  // one skipped after three schema failures.
  assert.equal(fake.prompts.length, 2)
  assert.deepEqual(fake.removed, ["ses_2", "ses_1"])
})

test("keepSessions keeps the child session for debugging", async () => {
  const fake = fakeCtx()
  const schemaResults = new Map<string, unknown>()
  fake.setOnPrompt((id) => schemaResults.set(id, { candidates: [] }))
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent", schemaResults, keepSessions: true })
  await runner(request())
  assert.deepEqual(fake.removed, [])
})

test("a failed session create returns null and removes nothing", async () => {
  const fake = fakeCtx()
  fake.ctx.session.create = async () => {
    throw new Error("subagents unavailable")
  }
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent" })
  const value = await runner(request())
  assert.equal(value, null)
  assert.deepEqual(fake.removed, [])
})

test("an already-aborted request does not create a session", async () => {
  const fake = fakeCtx()
  const controller = new AbortController()
  controller.abort()
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent" })
  const value = await runner(request({ signal: controller.signal }))
  assert.equal(value, null)
  assert.deepEqual(fake.created, [])
})

test("the parent model is the fallback when the agent has no configured model", async () => {
  const fake = fakeCtx()
  fake.setOnPrompt((id) => fake.push(id, '{"candidates":[]}'))
  const model = { providerID: "opencode-go", id: "deepseek-v4.1-flash", variant: "max" }
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent", model })
  await runner(request())
  assert.deepEqual(fake.createdInputs[0].model, model)
})

test("an agent's configured model wins over the parent fallback", async () => {
  const agentModel = { providerID: "opencode-go", id: "deepseek-v4.1-flash", variant: "high" }
  const fake = fakeCtx({ "review-finder": agentModel })
  fake.setOnPrompt((id) => fake.push(id, '{"candidates":[]}'))
  const parentModel = { providerID: "opencode-go", id: "deepseek-v4.1-flash", variant: "max" }
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent", model: parentModel })
  await runner(request())
  assert.deepEqual(fake.createdInputs[0].model, agentModel)
})

test("an agent model in provider/model#variant form is converted to a ModelRef", async () => {
  const fake = fakeCtx({ "review-finder": "opencode-go/deepseek-v4.1-flash#high" })
  fake.setOnPrompt((id) => fake.push(id, '{"candidates":[]}'))
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent" })
  await runner(request())
  assert.deepEqual(fake.createdInputs[0].model, {
    providerID: "opencode-go",
    id: "deepseek-v4.1-flash",
    variant: "high",
  })
})

test("a transient agent lookup failure is retried instead of cached", async () => {
  const agentModel = { providerID: "opencode-go", id: "deepseek-v4.1-flash", variant: "high" }
  const parentModel = { providerID: "opencode-go", id: "deepseek-v4.1-flash", variant: "max" }
  const fake = fakeCtx({ "review-finder": agentModel }, { agentGetFailures: 1 })
  fake.setOnPrompt((id) => fake.push(id, '{"candidates":[]}'))
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent", model: parentModel })
  await runner(request({ label: "angle-A" }))
  await runner(request({ label: "angle-B" }))
  assert.deepEqual(fake.createdInputs[0].model, parentModel)
  assert.deepEqual(fake.createdInputs[1].model, agentModel)
})

test("a retried child keeps its original role label for model lookup", async () => {
  const fake = fakeCtx()
  let calls = 0
  fake.setOnPrompt((id) => {
    calls++
    if (calls === 1) fake.push(id, '{"verdict":"MAYBE"}')
    else fake.push(id, '{"verdict":"CONFIRMED","evidence":"retried"}')
  })
  const labels: string[] = []
  const runner = makeRunner(fake.ctx, {
    parentSessionID: "ses_parent",
    modelFor: (req) => {
      labels.push(req.label)
      return { providerID: "p", id: "m", variant: "low" }
    },
  })
  const value = await runner(request({ role: "verifier", schemaName: "verdict" }))
  assert.deepEqual(value, { verdict: "CONFIRMED", evidence: "retried" })
  assert.ok(labels.length >= 2)
  assert.ok(labels.every((label) => label === "angle-A"))
})

test("a tool payload that echoes the schema example is not captured", async () => {
  const fake = fakeCtx()
  const schemaResults = new Map<string, unknown>()
  let calls = 0
  fake.setOnPrompt((id) => {
    calls++
    if (calls === 1) {
      schemaResults.set(id, { summary: "one sentence", decisions: [{ index: 0, merge: [1] }] })
      fake.push(id, "Decisions submitted.")
    } else {
      schemaResults.set(id, { summary: "real", decisions: [{ index: 0 }] })
      fake.push(id, "Decisions submitted.")
    }
  })
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent", schemaResults })
  const value = await runner(request({ role: "synthesize", schemaName: "decisions", label: "merge" }))
  assert.deepEqual(value, { summary: "real", decisions: [{ index: 0 }] })
  assert.equal(fake.prompts.length, 2)
})

test("a role variant is applied to the parent model", async () => {
  const fake = fakeCtx()
  fake.setOnPrompt((id) => fake.push(id, '{"candidates":[]}'))
  const parentModel = { providerID: "opencode-go", id: "deepseek-v4.1-flash", variant: "max" }
  const runner = makeRunner(fake.ctx, {
    parentSessionID: "ses_parent",
    model: parentModel,
    modelFor: () => ({ ...parentModel, variant: "high" }),
  })
  await runner(request())
  assert.deepEqual(fake.createdInputs[0].model, { ...parentModel, variant: "high" })
})

test("a hung session.wait does not hang the runner when the child is already idle", async () => {
  const fake = fakeCtx({}, { hangWait: true })
  fake.setOnPrompt((id) => fake.push(id, '{"candidates":[]}'))
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent" })
  const value = (await runner(request())) as { candidates: unknown[] }
  assert.equal(value.candidates.length, 0)
})

test("an idle timestamp without a busy timestamp does not settle before the child answers", async () => {
  const fake = fakeCtx({}, { idleGet: true, waitMs: 20 })
  fake.setOnPrompt((id) => {
    setTimeout(() => fake.push(id, '{"candidates":[]}'), 10)
  })
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent", pollMs: 1 })
  const value = (await runner(request())) as { candidates: unknown[] }
  assert.equal(value.candidates.length, 0)
  assert.equal(fake.prompts.length, 1)
})

test("a verdict the engine would reject triggers the runner retry", async () => {
  const fake = fakeCtx()
  fake.setOnPrompt((id, text) => {
    if (text.includes("did not submit")) fake.push(id, '{"verdict":"CONFIRMED","evidence":"retried"}')
    else fake.push(id, '{"verdict":"MAYBE","evidence":"unsure"}')
  })
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent" })
  const value = await runner(request({ role: "verifier", schemaName: "verdict" }))
  assert.deepEqual(value, { verdict: "CONFIRMED", evidence: "retried" })
  assert.equal(fake.prompts.length, 2)
})

test("a bare candidate array is salvaged as a candidates result", async () => {
  const fake = fakeCtx()
  fake.setOnPrompt((id) =>
    fake.push(id, '[{"file":"a.ts","summary":"s","failure_scenario":"f"}]'),
  )
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent" })
  const value = (await runner(request())) as { candidates: Array<{ file: string }> }
  assert.equal(value.candidates[0].file, "a.ts")
})

test("stream activity re-arms the watchdog for a long reasoning step", async () => {
  const fake = fakeCtx({}, { hangWait: true, busyGet: true })
  fake.setOnPrompt(() => {})
  let reads = 0
  const runner = makeRunner(fake.ctx, {
    parentSessionID: "ses_parent",
    stallMs: 40,
    pollMs: 5,
    // Six live readings then silence: the first attempt outlives the raw
    // timeout, so only the event-driven re-arm can explain the delay.
    activity: () => (++reads <= 6 ? Date.now() : undefined),
  })
  const value = await runner(request())
  assert.equal(value, null)
  assert.deepEqual(fake.interrupted, ["ses_1", "ses_2"])
  assert.ok(reads >= 12, `expected repeated activity reads, got ${reads}`)
})

test("trackActivity indexes stream events by child session", async () => {
  const types: string[][] = []
  const ctx = {
    event: {
      async *subscribe(options?: { types?: string[] }) {
        types.push(options?.types ?? [])
        yield { type: "session.reasoning.delta", data: { sessionID: "ses_child" } }
        yield { type: "session.usage.updated", data: { sessionID: "ses_child" } }
        yield { type: "session.reasoning.delta", data: {} }
      },
    },
  }
  const tracker = trackActivity(ctx)
  await new Promise((resolve) => setTimeout(resolve, 20))
  assert.ok(tracker.last("ses_child") !== undefined)
  assert.equal(tracker.last("ses_other"), undefined)
  assert.ok(types[0].includes("session.reasoning.delta"))
  tracker.stop()
})

test("a silent child is interrupted by the stall watchdog and retried once fresh", async () => {
  const fake = fakeCtx({}, { hangWait: true, busyGet: true })
  fake.setOnPrompt(() => {})
  const runner = makeRunner(fake.ctx, {
    parentSessionID: "ses_parent",
    stallMs: 30,
    pollMs: 5,
  })
  const value = await runner(request())
  assert.equal(value, null)
  assert.deepEqual(fake.interrupted, ["ses_1", "ses_2"])
  // One attempt, then one fresh-child retry; the retry also stalls.
  assert.equal(fake.prompts.length, 2)
})

test("a step-limited finder is recovered by a fresh formatter child", async () => {
  const fake = fakeCtx()
  fake.setOnPrompt((id, text) => {
    if (text.includes("Convert the completed review")) {
      fake.push(id, '{"candidates":[{"file":"a.ts","summary":"s","failure_scenario":"f"}]}')
      return
    }
    fake.pushStepLimit(id)
    fake.push(id, "I found one issue in a.ts but ran out of steps.")
  })
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent" })
  const value = (await runner(request())) as { candidates: Array<{ file: string }> }
  assert.equal(value.candidates[0].file, "a.ts")
  assert.equal(fake.created.length, 2)
  assert.match(String(fake.createdInputs[1].title), /\(format\)/)
  const formatterPrompt = fake.prompts.find((p) => p.text.includes("Convert the completed review"))?.text ?? ""
  // The formatter must not follow the old "omit what the text lacks" rule:
  // the validator requires failure_scenario.
  assert.match(formatterPrompt, /must include/)
  assert.match(formatterPrompt, /failure_scenario/)
})

test("a step-limited formatter repairs a missing failure scenario instead of dropping the finding", async () => {
  const fake = fakeCtx()
  fake.setOnPrompt((id, text) => {
    if (text.includes("Convert the completed review")) {
      fake.push(id, '{"candidates":[{"file":"a.ts","summary":"found bug"}]}')
      return
    }
    fake.pushStepLimit(id)
    fake.push(id, "I found a bug in a.ts but ran out of steps.")
  })
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent" })
  const value = (await runner(request())) as { candidates: Array<{ file: string; failure_scenario: string }> }
  assert.equal(value.candidates.length, 1)
  assert.equal(value.candidates[0].file, "a.ts")
  assert.match(value.candidates[0].failure_scenario, /not stated/)
})

test("a prose-only finder is recovered by a fresh formatter before a retry", async () => {
  const fake = fakeCtx()
  fake.setOnPrompt((id, text) => {
    if (text.includes("Convert the completed review")) {
      fake.push(id, '{"candidates":[{"file":"a.ts","summary":"s","failure_scenario":"f"}]}')
      return
    }
    fake.push(id, "I found one issue in a.ts.")
  })
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent" })
  const value = (await runner(request())) as { candidates: Array<{ file: string }> }
  assert.equal(value.candidates[0].file, "a.ts")
  assert.equal(fake.created.length, 2)
  assert.equal(fake.prompts.length, 2)
})

test("a findings array is salvaged as candidates", async () => {
  const fake = fakeCtx()
  fake.setOnPrompt((id) =>
    fake.push(id, '{"findings":[{"file":"a.ts","summary":"s","failure_scenario":"f"}]}'),
  )
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent" })
  const value = (await runner(request())) as { candidates: Array<{ file: string }> }
  assert.equal(value.candidates[0].file, "a.ts")
})

test("an empty response gets a second structured-output retry", async () => {
  const fake = fakeCtx()
  let retries = 0
  fake.setOnPrompt((id, text) => {
    if (text.includes("did not submit")) {
      retries++
      fake.push(id, retries >= 2 ? '{"candidates":[]}' : "still nothing")
    } else {
      fake.push(id, "nothing")
    }
  })
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent" })
  const value = (await runner(request())) as { candidates: unknown[] }
  assert.equal(value.candidates.length, 0)
  assert.equal(fake.prompts.length, 3)
})

test("a stale idle timestamp does not settle a retry before the new turn finishes", async () => {
  const fake = fakeCtx({}, { hangWait: true })
  fake.ctx.session.get = async () => ({ data: { time: { busy: 100, idle: 200, updated: 1 } } })
  fake.setOnPrompt(() => {})
  const runner = makeRunner(fake.ctx, {
    parentSessionID: "ses_parent",
    stallMs: 30,
    pollMs: 5,
  })
  const value = await runner(request())
  assert.equal(value, null)
  // The stale idle must not be mistaken for a completed turn: one attempt,
  // then one fresh-child retry after the watchdog.
  assert.equal(fake.prompts.length, 2)
  assert.deepEqual(fake.interrupted, ["ses_1", "ses_2"])
})

test("a live child whose session record omits time is not treated as gone", async () => {
  const fake = fakeCtx({}, { hangWait: true })
  fake.ctx.session.get = async () => ({ data: { id: "ses_1" } })
  fake.setOnPrompt((id) => {
    setTimeout(() => fake.push(id, '{"candidates":[]}'), 10)
  })
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent", pollMs: 1 })
  const value = (await runner(request())) as { candidates: unknown[] }
  assert.equal(value.candidates.length, 0)
  assert.equal(fake.prompts.length, 1)
})

test("the step-limit literal in the initial prompt does not force step-limit recovery", async () => {
  const fake = fakeCtx()
  fake.setOnPrompt((id, text) => {
    if (text.includes("Convert the completed review")) {
      fake.push(id, "no json")
      return
    }
    if (text.includes("did not submit")) {
      fake.push(id, '{"candidates":[]}')
      return
    }
    // The initial prompt quotes the diff, which contains the injected-notice
    // literal. A substring search treats the child as step-limited and stops
    // after the formatter fails; the marker must be at the start of a message.
    fake.pushUser(id, "review this\nCRITICAL - MAXIMUM STEPS REACHED appears in the diff")
    fake.push(id, "I found one issue in a.ts but ran out of steps.")
  })
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent" })
  const value = (await runner(request())) as { candidates: unknown[] }
  assert.equal(value.candidates.length, 0)
  // Initial prompt, failed formatter, and same-session retry. A false
  // step-limit match would return null after the formatter (two prompts).
  assert.equal(fake.prompts.length, 3)
})

test("the synthesizer prompt does not tell it to read files or run commands", async () => {
  const fake = fakeCtx()
  fake.setOnPrompt((id) => fake.push(id, '{"decisions":[],"summary":"none"}'))
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent" })
  await runner(request({ role: "synthesize", label: "synthesize", schemaName: "decisions" }))
  const prompt = fake.prompts[0]?.text ?? ""
  assert.doesNotMatch(prompt, /Do your work/)
  assert.match(prompt, /Do not explore, read files, or run commands/)
})

test("a step-limited formatter is not told to read files or run commands", async () => {
  const fake = fakeCtx()
  fake.setOnPrompt((id, text) => {
    if (text.includes("Convert the completed review")) {
      fake.push(id, '{"candidates":[{"file":"a.ts","summary":"s","failure_scenario":"f"}]}')
      return
    }
    fake.pushStepLimit(id)
    fake.push(id, "I found one issue in a.ts but ran out of steps.")
  })
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent" })
  await runner(request())
  const formatterPrompt = fake.prompts.find((p) => p.text.includes("Convert the completed review"))?.text ?? ""
  assert.doesNotMatch(formatterPrompt, /Do your work/)
  assert.doesNotMatch(formatterPrompt, /read files, run commands/)
})

test("cancelling the request stops the wait even when interrupt is unavailable", async () => {
  const fake = fakeCtx({}, { hangWait: true, busyGet: true })
  delete (fake.ctx.session as { interrupt?: unknown }).interrupt
  const controller = new AbortController()
  fake.setOnPrompt(() => {
    setTimeout(() => controller.abort(), 10)
  })
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent", pollMs: 1 })
  const started = Date.now()
  const value = await runner(request({ signal: controller.signal }))
  assert.equal(value, null)
  assert.ok(Date.now() - started < 2000, "the runner kept polling after cancellation")
})

test("a {location,data} session.create envelope is unwrapped", async () => {
  const fake = fakeCtx()
  fake.ctx.session.create = async () => ({ location: {}, data: { id: "ses_env" } })
  fake.ctx.session.context = async () => [
    { type: "assistant", content: [{ type: "text", text: '{"candidates":[]}' }], finish: "stop" },
  ]
  const runner = makeRunner(fake.ctx, { parentSessionID: "ses_parent" })
  const value = await runner(request())
  assert.deepEqual(value, { candidates: [] })
  assert.deepEqual(fake.removed, ["ses_env"])
})
