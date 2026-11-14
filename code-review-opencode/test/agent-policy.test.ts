import { test } from "node:test"
import assert from "node:assert/strict"
import { execFileSync } from "node:child_process"
import { existsSync, readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"
import { AGENT_IDS } from "../.opencode/plugins/code-review-opencode/agent-ids.ts"
import {
  READ_ONLY_POLICY,
  REVIEW_AGENT_IDS,
  installReviewAgentPolicy,
  renderAgentPolicyYaml,
  replacePolicyBlock,
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

test("spilled output gets its separate external-directory approval without granting home access or writes", () => {
  // OpenCode 2.2.5 FileAccess authorizes a file's parent as <directory>/*;
  // Permission.evaluate uses the last matching glob, independently of read.
  const root = "/home/reviewer/custom-data/opencode"
  const rules = reviewAgentPermissions("review-finder", root)
  const effect = (action: string, resource: string) =>
    rules.findLast((rule) => globMatch(rule.action, action) && globMatch(rule.resource, resource))?.effect
  assert.equal(effect("external_directory", `${root}/shell/project-id/*`), "allow")
  assert.equal(effect("external_directory", `${root}/tool-output/*`), "allow")
  assert.equal(effect("read", `${root}/shell/project-id/sh_example.out`), "allow")
  for (const resource of ["/home/reviewer/.ssh/*", `${root}/credential/*`, "/tmp/untrusted/*"]) {
    assert.equal(effect("external_directory", resource), "deny")
  }
  for (const action of ["edit", "write", "patch"]) {
    assert.equal(effect(action, `${root}/shell/project-id/sh_example.out`), "deny")
  }
  assert.equal(
    reviewAgentPermissions("review-finder", "/tmp/data?wildcard/opencode").some((rule) => rule.action === "external_directory"),
    false,
  )
})

test("Markdown spill permissions use host-expanded home paths, never a developer's home", () => {
  const yaml = renderAgentPolicyYaml("review-finder")
  assert.ok(yaml.includes('resource: "~/.local/share/opencode/shell/*"'))
  assert.ok(yaml.includes('resource: "~/.local/share/opencode/tool-output/*"'))
  // The host's ConfigAgentPlugin expands these path-action resources before
  // evaluating them; its agent.transform API does not perform that expansion.
  const portable = reviewAgentPermissions("review-finder", "~/.local/share/opencode")
  const expanded = portable.map((rule) => ({ ...rule, resource: rule.resource.replace(/^~\//, "/home/another-user/") }))
  const external = expanded.filter((rule) => rule.action === "external_directory")
  assert.ok(external.some((rule) => globMatch(rule.resource, "/home/another-user/.local/share/opencode/shell/project/*")))
})

test("installReviewAgentPolicy replaces governed rules and keeps host extensions", async () => {
  const agents = new Map(
    REVIEW_AGENT_IDS.map((id) => [
      id,
      {
        permissions: [
          { action: "shell", resource: "git -c core.hooksPath=/old diff*", effect: "allow" as const },
          { action: "webfetch", resource: "https://example.com/*", effect: "allow" as const },
          { action: "edit", resource: "*", effect: "allow" as const },
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
    assert.equal(
      permissions.some((rule) => rule.action === "edit" && rule.effect === "allow"),
      false,
      `${id} kept a write-capable host allow`,
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

test("every agent id names a Markdown agent file", () => {
  const dir = fileURLToPath(new URL("../.opencode/agents/", import.meta.url))
  for (const id of Object.values(AGENT_IDS)) {
    assert.ok(existsSync(join(dir, `${id}.md`)), `${id}.md is missing`)
  }
})

test("the agent-policy sync check passes", () => {
  const script = fileURLToPath(new URL("../scripts/sync-agent-policy.ts", import.meta.url))
  execFileSync(process.execPath, [script, "--check"], { stdio: "pipe" })
})

test("the policy block replacement writes dollar patterns verbatim", () => {
  const text = "---\npermissions:\n  - action: old\n---\nbody\n"
  const block = 'permissions:\n  - action: "shell"\n    resource: "*$(*"\n    effect: deny'
  const next = replacePolicyBlock(text, block)
  assert.ok(next.includes('"*$(*"'))
  assert.ok(next.includes("body"))
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
