import { test } from "node:test"
import assert from "node:assert/strict"
import { execFileSync } from "node:child_process"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"
import {
  READ_ONLY_POLICY,
  REVIEW_AGENT_IDS,
  installReviewAgentPolicy,
  renderAgentPolicyYaml,
  reviewAgentPermissions,
} from "../.opencode/plugins/code-review-opencode/agent-policy.ts"
import { GIT_HARDENING } from "../.opencode/plugins/code-review-opencode/scope.ts"

/** OpenCode permission globs: `*` spans everything, `?` is one character. */
function globMatch(pattern: string, value: string): boolean {
  const escaped = pattern.replace(/[.+^${}()|[\]\\]/g, "\\$&")
  const regex = escaped.replaceAll("*", ".*").replaceAll("?", ".")
  return new RegExp(`^${regex}$`, "s").test(value)
}

test("the shared policy starts with a deny-all and has no blanket -c deny", () => {
  assert.deepEqual(READ_ONLY_POLICY[0], { action: "*", resource: "*", effect: "deny" })
  assert.equal(
    READ_ONLY_POLICY.some((rule) => rule.action === "shell" && rule.resource === "* -c*"),
    false,
    "the blanket -c deny contradicts the hardened git allow rules",
  )
})

test("the rendered diff command matches a generated allow rule", () => {
  const hardening = GIT_HARDENING.join(" ")
  const permissions = reviewAgentPermissions("review-finder")
  const allows = permissions.filter((rule) => rule.action === "shell" && rule.effect === "allow")
  const sameDir = `git ${hardening} diff --no-ext-diff --no-textconv --end-of-options HEAD`
  const withC = `git -C /tmp/repo ${hardening} diff --no-ext-diff --no-textconv --end-of-options HEAD`
  assert.ok(
    allows.some((rule) => globMatch(rule.resource, sameDir)),
    `no allow rule matches ${sameDir}`,
  )
  assert.ok(
    allows.some((rule) => globMatch(rule.resource, withC)),
    `no allow rule matches ${withC}`,
  )
})

test("every git allow rule carries the hardening flags", () => {
  const gitRules = reviewAgentPermissions("review-finder").filter(
    (rule) => rule.action === "shell" && rule.effect === "allow" && rule.resource.startsWith("git"),
  )
  assert.ok(gitRules.length > 0)
  for (const rule of gitRules) {
    assert.match(rule.resource, /core\.hooksPath=\/dev\/null/)
    assert.match(rule.resource, /core\.fsmonitor=/)
  }
})

test("role tool permissions are role-specific", () => {
  const finder = reviewAgentPermissions("review-finder").map((rule) => rule.action)
  const verifier = reviewAgentPermissions("review-verifier").map((rule) => rule.action)
  assert.ok(finder.includes("code_review_candidates"))
  assert.equal(finder.includes("code_review_verdict"), false)
  assert.ok(verifier.includes("code_review_verdict"))
  assert.ok(verifier.includes("code_review_group_verdicts"))
  assert.equal(verifier.includes("code_review_candidates"), false)
})

test("installReviewAgentPolicy replaces governed rules and keeps host extensions", async () => {
  const agents = new Map(
    REVIEW_AGENT_IDS.map((id) => [
      id,
      {
        permissions: [
          { action: "shell", resource: "git -c core.hooksPath=/old diff*", effect: "allow" as const },
          { action: "webfetch", resource: "https://example.com/*", effect: "allow" as const },
          { action: "*", resource: "*", effect: "ask" as const },
          { action: "*", resource: "/tmp/*", effect: "allow" as const },
        ],
      },
    ]),
  )
  let transformed = false
  const ctx = {
    agent: {
      async transform(callback: (editor: { update: (id: string, update: (agent: { permissions: Array<{ action: string; resource: string; effect: string }> }) => void) => void }) => void) {
        transformed = true
        callback({
          update(id, update) {
            const agent = agents.get(id)
            if (agent) update(agent)
          },
        })
      },
    },
  }
  await installReviewAgentPolicy(ctx)
  // A second load must not append a duplicate policy or keep a stale rule.
  await installReviewAgentPolicy(ctx)
  assert.equal(transformed, true)
  for (const id of REVIEW_AGENT_IDS) {
    const permissions = agents.get(id)?.permissions ?? []
    const stale = permissions.find(
      (rule) => rule.action === "shell" && rule.resource.includes("core.hooksPath=/old"),
    )
    assert.equal(stale, undefined, `${id} kept a stale shell allow`)
    assert.equal(
      permissions.some((rule) => rule.action === "*" && rule.resource === "/tmp/*"),
      false,
      `${id} kept a broad host allow that would bypass the deny-all`,
    )
    assert.ok(
      permissions.some(
        (rule) =>
          rule.action === "webfetch" &&
          rule.resource === "https://example.com/*" &&
          rule.effect === "allow",
      ),
      `${id} dropped the host webfetch rule`,
    )
    const policy = reviewAgentPermissions(id)
    assert.equal(
      permissions.filter((rule) => rule.action === "*" && rule.resource === "*").length,
      1,
      `${id} should have exactly one broad deny`,
    )
    for (const rule of policy) {
      assert.ok(
        permissions.some(
          (candidate) =>
            candidate.action === rule.action &&
            candidate.resource === rule.resource &&
            candidate.effect === rule.effect,
        ),
        `${id} is missing the policy rule ${rule.action}:${rule.resource}`,
      )
    }
  }
})

test("installReviewAgentPolicy is a no-op on hosts without agent transforms", async () => {
  await installReviewAgentPolicy({})
})

test("the agent-policy sync check passes", () => {
  const script = fileURLToPath(new URL("../scripts/sync-agent-policy.ts", import.meta.url))
  execFileSync(process.execPath, [script, "--check"], { stdio: "pipe" })
})

test("the Markdown fallback permissions are generated from the shared policy", () => {
  const dir = fileURLToPath(new URL("../.opencode/agents/", import.meta.url))
  for (const id of REVIEW_AGENT_IDS) {
    const text = readFileSync(join(dir, `${id}.md`), "utf8")
    const match = text.match(/^permissions:\n[\s\S]*?(?=^---$)/m)
    assert.ok(match, `${id}.md has no permissions block`)
    assert.equal(
      match[0].trimEnd(),
      renderAgentPolicyYaml(id),
      `${id}.md is stale; run node scripts/sync-agent-policy.ts`,
    )
  }
})
