import { test } from "node:test"
import assert from "node:assert/strict"
import {
  READ_ONLY_POLICY,
  REVIEW_AGENT_IDS,
  installReviewAgentPolicy,
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

test("installReviewAgentPolicy replaces each review agent's permissions", async () => {
  const agents = new Map(
    REVIEW_AGENT_IDS.map((id) => [
      id,
      {
        permissions: [
          { action: "shell", resource: "git -c core.hooksPath=/old diff*", effect: "allow" as const },
        ],
      },
    ]),
  )
  let transformed = false
  const ctx = {
    agent: {
      async transform(callback: (editor: { update: (id: string, update: (agent: { permissions: Array<{ action: string }> }) => void) => void }) => void) {
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
    assert.deepEqual(agents.get(id)?.permissions, reviewAgentPermissions(id))
  }
})

test("installReviewAgentPolicy is a no-op on hosts without agent transforms", async () => {
  await installReviewAgentPolicy({})
})
