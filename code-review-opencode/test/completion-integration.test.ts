import { execFileSync } from "node:child_process"
import { stripTypeScriptTypes } from "node:module"
import { mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { test } from "node:test"
import assert from "node:assert/strict"

const pluginPath = new URL("../.opencode/plugins/code-review-opencode/index.ts", import.meta.url)

async function loadPlugin(runReview: (input: unknown) => Promise<unknown>) {
  let source = readFileSync(pluginPath, "utf8")
  source = source.replace('import { Plugin } from "@opencode/plugin"', "const Plugin = { define: (definition) => definition }")
  source = source.replace(
    /import \{ runReview, isInline, type AgentRunner, type EngineResult \} from "\.\/engine\.ts"/,
    "const runReview = (...args) => globalThis.__CODE_REVIEW_RUN_REVIEW__(...args); const isInline = (cell) => cell.inlineVariant !== undefined",
  )
  source = source.replace(/from "(\.\.?\/[^"\n]+)"/g, (_match, specifier: string) => {
    return `from ${JSON.stringify(new URL(specifier, pluginPath).href)}`
  })
  const oldRunner = (globalThis as Record<string, unknown>).__CODE_REVIEW_RUN_REVIEW__
  ;(globalThis as Record<string, unknown>).__CODE_REVIEW_RUN_REVIEW__ = runReview
  const js = stripTypeScriptTypes(source, { mode: "strip" })
  const encoded = Buffer.from(js).toString("base64")
  const plugin = (await import(`data:text/javascript;base64,${encoded}`)).default
  ;(globalThis as Record<string, unknown>).__CODE_REVIEW_OLD_RUN_REVIEW__ = oldRunner
  return plugin
}

async function runCommand(
  root: string,
  reportDir: string,
  runReview: (input: unknown) => Promise<unknown>,
  signal?: AbortSignal,
) {
  process.env.CODE_REVIEW_REPORT_DIR = reportDir
  const registered: Record<string, unknown>[] = []
  const synthetic: Array<{ sessionID: string; text: string }> = []
  const host = {
    location: { directory: root },
    session: {
      get: async () => ({ id: "session-parent", model: { providerID: "test", id: "stub" } }),
      create: async () => ({ id: "child" }),
      prompt: async () => {},
      wait: async () => {},
      context: async () => [],
      interrupt: async () => {},
      remove: async () => {},
      synthetic: async (item: { sessionID: string; text: string }) => synthetic.push(item),
    },
    storage: { get: async () => undefined, set: async () => {} },
    model: { default: async () => ({ providerID: "test", id: "stub" }) },
    tool: { transform: async (transform: (editor: { add: () => void }) => void) => transform({ add: () => {} }) },
    command: {
      transform: async (transform: (editor: { add: (command: Record<string, unknown>) => void }) => void) =>
        transform({ add: (command) => registered.push(command) }),
    },
  }
  const plugin = await loadPlugin(runReview)
  try {
    await plugin.setup(host)
    const command = registered.find((item) => item.name === "code-review-opencode")
    assert.ok(command)
    await (command.execute as (input: unknown) => Promise<void>)(
      { sessionID: "session-parent", prompt: { text: "max --json" }, delivery: "inline", signal },
    )
    return { synthetic, artifacts: readdirSync(reportDir).filter((name) => name.endsWith(".json")) }
  } finally {
    const globals = globalThis as Record<string, unknown>
    globals.__CODE_REVIEW_RUN_REVIEW__ = globals.__CODE_REVIEW_OLD_RUN_REVIEW__
    delete globals.__CODE_REVIEW_OLD_RUN_REVIEW__
  }
}

function repoFixture() {
  const root = mkdtempSync(join(tmpdir(), "cr-completion-host-"))
  writeFileSync(join(root, "source.ts"), "export const value = 1\n")
  execFileSync("git", ["init", "-q"], { cwd: root })
  execFileSync("git", ["-c", "user.name=Test", "-c", "user.email=test@example.com", "add", "source.ts"], { cwd: root })
  execFileSync("git", ["-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "initial"], { cwd: root })
  writeFileSync(join(root, "source.ts"), "export const value = 2\n")
  return root
}

test("registered command records session-bound JSON completion without a parent model outcome", async () => {
  const root = repoFixture()
  const reportDir = mkdtempSync(join(tmpdir(), "cr-completion-reports-"))
  try {
    const outcome = await runCommand(root, reportDir, async () => ({
      level: "max",
      summary: "1 verified finding",
      findings: [{ file: "source.ts", line: 1, summary: "missing guard", failure_scenario: "invalid input passes", verdict: "CONFIRMED", kind: "correctness" }],
      refuted: [],
      stats: { finders: 1, candidates: 1, verifierAgents: 1, verified: 1, refuted: 0, dupes: 0, budgetDropped: 0, reported: 1 },
      partial: false,
      warnings: [],
      cell: "max",
    }))
    assert.equal(outcome.artifacts.length, 1)
    assert.equal(JSON.parse(outcome.synthetic[0].text)[0].summary, "missing guard")
    const artifact = JSON.parse(readFileSync(join(reportDir, outcome.artifacts[0]), "utf8"))
    assert.equal(artifact.terminal_status, "complete")
    assert.equal(artifact.parent_session_id, "session-parent")
    assert.equal(artifact.requested_target, "")
    assert.deepEqual(artifact.model, { provider_id: "test", id: "stub" })
  } finally {
    delete process.env.CODE_REVIEW_REPORT_DIR
    rmSync(root, { recursive: true, force: true })
    rmSync(reportDir, { recursive: true, force: true })
  }
})

test("registered command records scope failure as terminal status while preserving bare JSON", async () => {
  const root = mkdtempSync(join(tmpdir(), "cr-completion-nogit-"))
  const reportDir = mkdtempSync(join(tmpdir(), "cr-completion-error-"))
  try {
    const outcome = await runCommand(root, reportDir, async () => {
      throw new Error("runReview must not run after scope failure")
    })
    assert.equal(outcome.artifacts.length, 1)
    assert.equal(outcome.synthetic[0].text, "[]")
    const artifact = JSON.parse(readFileSync(join(reportDir, outcome.artifacts[0]), "utf8"))
    assert.equal(artifact.terminal_status, "failed")
    assert.equal(artifact.terminal_outcome, "scope_error")
    assert.match(artifact.diagnostics[0], /Code review could not start/)
    assert.equal(artifact.findings.length, 0)
  } finally {
    delete process.env.CODE_REVIEW_REPORT_DIR
    rmSync(root, { recursive: true, force: true })
    rmSync(reportDir, { recursive: true, force: true })
  }
})

test("terminal provider failure is recorded without fallback and without dropping JSON output", async () => {
  const root = repoFixture()
  const reportDir = mkdtempSync(join(tmpdir(), "cr-completion-provider-"))
  try {
    const outcome = await runCommand(root, reportDir, async () => ({
      level: "max",
      summary: "Review could not complete",
      findings: [],
      refuted: [],
      stats: { finders: 1, candidates: 0, verifierAgents: 0, verified: 0, refuted: 0, dupes: 0, budgetDropped: 0, reported: 0, finderFailures: 1 },
      partial: true,
      warnings: ["provider failed"],
      terminalFailure: "provider.go-limit: weekly usage limit",
      cell: "max",
    }))
    const artifact = JSON.parse(readFileSync(join(reportDir, outcome.artifacts[0]), "utf8"))
    assert.equal(artifact.terminal_status, "failed")
    assert.equal(artifact.terminal_outcome, "provider_error")
    assert.ok(artifact.diagnostics.includes("provider.go-limit: weekly usage limit"))
    assert.equal(outcome.synthetic[0].text, "[]")
  } finally {
    delete process.env.CODE_REVIEW_REPORT_DIR
    rmSync(root, { recursive: true, force: true })
    rmSync(reportDir, { recursive: true, force: true })
  }
})

test("cancelled engine completion is recorded as cancelled", async () => {
  const root = repoFixture()
  const reportDir = mkdtempSync(join(tmpdir(), "cr-completion-cancelled-"))
  const controller = new AbortController()
  controller.abort()
  try {
    const outcome = await runCommand(root, reportDir, async () => ({
      level: "max",
      summary: "Review cancelled",
      findings: [],
      refuted: [],
      stats: { finders: 0, candidates: 0, verifierAgents: 0, verified: 0, refuted: 0, dupes: 0, budgetDropped: 0, reported: 0 },
      partial: true,
      warnings: [],
      cell: "max",
    }), controller.signal)
    const artifact = JSON.parse(readFileSync(join(reportDir, outcome.artifacts[0]), "utf8"))
    assert.equal(artifact.terminal_status, "cancelled")
    assert.equal(artifact.terminal_outcome, "cancelled")
  } finally {
    delete process.env.CODE_REVIEW_REPORT_DIR
    rmSync(root, { recursive: true, force: true })
    rmSync(reportDir, { recursive: true, force: true })
  }
})
