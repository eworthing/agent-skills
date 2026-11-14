import assert from "node:assert/strict"
import { execFileSync } from "node:child_process"
import { stripTypeScriptTypes } from "node:module"
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { test } from "node:test"

const pluginPath = new URL("../.opencode/plugins/code-review-opencode/index.ts", import.meta.url)

async function loadPlugin(runReview: (input: unknown) => Promise<unknown>) {
  let source = readFileSync(pluginPath, "utf8")
  source = source.replace('import { Plugin } from "@opencode/plugin"', "const Plugin = { define: (definition) => definition }")
  source = source.replace(
    /import \{ runReview, isInline, type AgentRunner, type EngineResult \} from "\.\/engine\.ts"/,
    "const runReview = (...args) => globalThis.__CODE_REVIEW_DISPATCH_RUN_REVIEW__(...args); const isInline = (cell) => cell.inlineVariant !== undefined",
  )
  source = source.replace(/from "(\.\.?\/[^"\n]+)"/g, (_match, specifier: string) => {
    return `from ${JSON.stringify(new URL(specifier, pluginPath).href)}`
  })
  const globals = globalThis as Record<string, unknown>
  const previous = globals.__CODE_REVIEW_DISPATCH_RUN_REVIEW__
  globals.__CODE_REVIEW_DISPATCH_RUN_REVIEW__ = runReview
  const encoded = Buffer.from(stripTypeScriptTypes(source, { mode: "strip" })).toString("base64")
  const plugin = (await import(`data:text/javascript;base64,${encoded}`)).default
  return {
    plugin,
    restore: () => {
      if (previous === undefined) delete globals.__CODE_REVIEW_DISPATCH_RUN_REVIEW__
      else globals.__CODE_REVIEW_DISPATCH_RUN_REVIEW__ = previous
    },
  }
}

function repoFixture() {
  const root = mkdtempSync(join(tmpdir(), "cr-dispatch-"))
  writeFileSync(join(root, "source.ts"), "export const value = 1\n")
  execFileSync("git", ["init", "-q", "-b", "main"], { cwd: root })
  execFileSync("git", ["-c", "user.name=Test", "-c", "user.email=test@example.com", "add", "source.ts"], { cwd: root })
  execFileSync("git", ["-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "initial"], { cwd: root })
  writeFileSync(join(root, "source.ts"), "export const value = 2\n")
  return root
}

async function commandRun(root: string, raw: string, runReview: (input: unknown) => Promise<unknown>) {
  const commands: Array<Record<string, unknown>> = []
  const prompts: Array<{ text?: string }> = []
  const synthetic: Array<{ text: string }> = []
  const reportDir = process.env.CODE_REVIEW_REPORT_DIR
  delete process.env.CODE_REVIEW_REPORT_DIR
  const { plugin, restore } = await loadPlugin(runReview)
  const host = {
    location: { directory: root },
    session: {
      get: async () => ({ id: "dispatch-parent", model: { providerID: "test", id: "stub" } }),
      create: async () => ({ id: "child" }),
      prompt: async (args: { text?: string }) => prompts.push(args),
      wait: async () => {},
      context: async () => [],
      interrupt: async () => {},
      remove: async () => {},
      synthetic: async (args: { text: string }) => synthetic.push(args),
    },
    storage: { get: async () => undefined, set: async () => {} },
    model: { default: async () => ({ providerID: "test", id: "stub" }) },
    tool: { transform: async (fn: (editor: { add: () => void }) => void) => fn({ add: () => {} }) },
    command: {
      transform: async (fn: (editor: { add: (command: Record<string, unknown>) => void }) => void) =>
        fn({ add: (command) => commands.push(command) }),
    },
  }
  try {
    await plugin.setup(host)
    const command = commands.find((item) => item.name === "code-review-opencode")
    assert.ok(command)
    await (command.execute as (input: unknown) => Promise<void>)(
      { sessionID: "dispatch-parent", prompt: { text: raw }, delivery: "inline" },
    )
    return { prompts, synthetic }
  } finally {
    restore()
    if (reportDir === undefined) delete process.env.CODE_REVIEW_REPORT_DIR
    else process.env.CODE_REVIEW_REPORT_DIR = reportDir
  }
}

function completeResult() {
  return {
    level: "high",
    summary: "No findings",
    findings: [],
    refuted: [],
    stats: { finders: 1, candidates: 0, verifierAgents: 1, verified: 0, refuted: 0, dupes: 0, budgetDropped: 0, reported: 0 },
    partial: false,
    warnings: [],
    cell: "high",
  }
}

test("registered command keeps action flags mentioned in prose inert", async () => {
  const root = repoFixture()
  try {
    const run = await commandRun(root, "high --driver prompt review the --fix --comment parsing", async () => {
      return completeResult()
    })
    assert.equal(run.synthetic.length, 0)
    assert.ok(run.prompts.length > 0)
    assert.ok(run.prompts.every((prompt) => !prompt.text?.includes("Applying fixes")))
    assert.ok(run.prompts.every((prompt) => !prompt.text?.includes("Post these findings as inline PR comments")))
  } finally {
    rmSync(root, { recursive: true, force: true })
  }
})

test("prompt driver rejects model overrides explicitly and preserves bare JSON", async () => {
  const root = repoFixture()
  let callCount = 0
  try {
    const run = await commandRun(root, "high --driver prompt --model other/provider", async () => {
      callCount++
      return completeResult()
    })
    assert.equal(callCount, 0)
    assert.equal(run.synthetic[0]?.text, "Cannot run this prompt-driven review with --model other/provider: the host API cannot select a model for the parent prompt turn. Remove --model or use a supported engine-driven review.")

    const json = await commandRun(root, "high --driver prompt --model other/provider --json", async () => {
      callCount++
      return completeResult()
    })
    assert.equal(callCount, 0)
    assert.equal(json.synthetic[0]?.text, "[]")
  } finally {
    rmSync(root, { recursive: true, force: true })
  }
})

test("prompt driver rejects unsupported legacy high workflows and keeps low fallback", async () => {
  const root = repoFixture()
  let callCount = 0
  try {
    const rejected = await commandRun(root, "high --mode cc-workflow-2.1.221 --driver prompt", async () => {
      callCount++
      return completeResult()
    })
    assert.equal(callCount, 0)
    assert.match(rejected.synthetic[0]?.text ?? "", /Cannot run workflow cc-workflow-2\.1\.221 through the prompt driver/)

    const rejectedJson = await commandRun(
      root,
      "high --mode cc-workflow-2.1.221 --driver prompt --json",
      async () => {
        callCount++
        return completeResult()
      },
    )
    assert.equal(rejectedJson.synthetic[0]?.text, "[]")

    const fallback = await commandRun(root, "low --mode cc-workflow-2.1.221 --driver prompt", async () => {
      callCount++
      return completeResult()
    })
    assert.equal(callCount, 0)
    assert.match(fallback.prompts[0]?.text ?? "", /has no low-effort recipe; using the current/)
  } finally {
    rmSync(root, { recursive: true, force: true })
  }
})

test("prompt driver accepts a deleted tracked path target", async () => {
  const root = repoFixture()
  writeFileSync(join(root, "obsolete.ts"), "export const gone = true\n")
  execFileSync("git", ["add", "obsolete.ts"], { cwd: root })
  execFileSync("git", ["-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "add obsolete"], { cwd: root })
  execFileSync("git", ["rm", "obsolete.ts"], { cwd: root })
  try {
    const run = await commandRun(root, "high --driver prompt ./obsolete.ts", async () => {
      throw new Error("prompt fallback must not start the deterministic engine")
    })
    assert.match(run.prompts[0]?.text ?? "", /Review target: `\.\/obsolete\.ts`/)
    assert.doesNotMatch(run.synthetic[0]?.text ?? "", /path not found/)
  } finally {
    rmSync(root, { recursive: true, force: true })
  }
})
