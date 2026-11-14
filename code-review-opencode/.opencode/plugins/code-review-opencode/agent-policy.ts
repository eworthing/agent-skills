/**
 * Shared read-only policy for the three review agents.
 *
 * The same rules used to live in each agent's Markdown frontmatter, three
 * copies of a 150-line table. The plugin now installs this policy with
 * `ctx.agent.transform` at setup, so the git hardening and the permission
 * patterns are generated from `GIT_HARDENING` and cannot drift from the
 * commands `scope.ts` renders.
 */
import { AGENT_IDS } from "./agent-ids.ts"
import { GIT_HARDENING } from "./scope.ts"
import { SHELL_DENY_RESOURCES } from "./shell-policy.ts"

export type AgentPermission = {
  action: string
  resource: string
  effect: "allow" | "deny" | "ask"
}

/** The read-only git subcommands, in the forms the prompt advertises. */
const GIT_SUBCOMMANDS = [
  "diff --no-ext-diff --no-textconv",
  "log --no-ext-diff --no-textconv",
  "show --no-ext-diff --no-textconv",
  "blame --no-textconv",
  "status",
  "rev-parse",
  "ls-files",
  "grep",
]

const hardening = GIT_HARDENING.join(" ")

const GIT_ALLOW: AgentPermission[] = GIT_SUBCOMMANDS.flatMap((subcommand) => [
  { action: "shell", resource: `git ${hardening} ${subcommand}*`, effect: "allow" as const },
  { action: "shell", resource: `git -C * ${hardening} ${subcommand}*`, effect: "allow" as const },
])

const SHELL_ALLOW: AgentPermission[] = [
  { action: "shell", resource: "gh pr diff*", effect: "allow" },
  { action: "shell", resource: "gh pr view*", effect: "allow" },
  { action: "shell", resource: "tail *", effect: "allow" },
  { action: "shell", resource: "head *", effect: "allow" },
  { action: "shell", resource: "ls *", effect: "allow" },
  { action: "shell", resource: "wc *", effect: "allow" },
]

/**
 * These commands can write (echo/sort/uniq, redirection, or `--output` on
 * git diff/log/show). A prefix allow matches the whole command string, so a
 * chained command after an allowed git command could still run; deny shell
 * control operators and process substitution outright. The pager and
 * config-env flags would turn an allowed read-only command into arbitrary
 * code execution. The same resource list is used by `labelFor`, so a
 * displayed command cannot contain a pattern the policy denies.
 */
const SHELL_DENY: AgentPermission[] = SHELL_DENY_RESOURCES.map((resource) => ({
  action: "shell",
  resource,
  effect: "deny",
}))

/** The policy every review child gets, before its role-specific tools. */
export const READ_ONLY_POLICY: AgentPermission[] = [
  { action: "*", resource: "*", effect: "deny" },
  { action: "read", resource: "*", effect: "allow" },
  { action: "glob", resource: "*", effect: "allow" },
  { action: "grep", resource: "*", effect: "allow" },
  ...GIT_ALLOW,
  ...SHELL_ALLOW,
  ...SHELL_DENY,
]

/** The structured-output tool each role may call. */
const ROLE_TOOLS: Record<string, readonly string[]> = {
  [AGENT_IDS.finder]: ["code_review_candidates"],
  [AGENT_IDS.verifier]: ["code_review_verdict", "code_review_group_verdicts"],
  [AGENT_IDS.sweep]: ["code_review_candidates"],
}

export const REVIEW_AGENT_IDS = Object.keys(ROLE_TOOLS)

/** Full permission list for one review agent. */
export function reviewAgentPermissions(agentID: string): AgentPermission[] {
  const tools = (ROLE_TOOLS[agentID] ?? []).map(
    (action): AgentPermission => ({ action, resource: "*", effect: "allow" }),
  )
  return [...READ_ONLY_POLICY, ...tools]
}

/**
 * Render the fallback permissions block for a Markdown agent. The static
 * `.opencode/agents/*.md` files are the host fallback when `agent.transform`
 * is unavailable; generating their block from this module keeps them in sync
 * with the installed policy instead of maintaining a second hand-copied table.
 */
export function renderAgentPolicyYaml(agentID: string): string {
  const lines = ["permissions:"]
  for (const rule of reviewAgentPermissions(agentID)) {
    lines.push(`  - action: ${JSON.stringify(rule.action)}`)
    lines.push(`    resource: ${JSON.stringify(rule.resource)}`)
    lines.push(`    effect: ${rule.effect}`)
  }
  return lines.join("\n")
}

/**
 * Merge the read-only policy into an agent's existing rules without dropping
 * host rules for actions the policy does not govern.
 *
 * OpenCode evaluates permissions last-match-wins. The policy's broad deny is
 * kept first; preserved host rules follow it, then the policy's specific
 * allows and denies. That keeps host extensions for unrelated concrete
 * actions (for example `webfetch`) working while the read-only rules remain
 * authoritative for shell, read, glob, grep, and the review tools. Existing
 * broad (`*`) rules are replaced by the policy's deny-all: a host rule such
 * as `*:/tmp/* allow` would otherwise sit after the deny and bypass it for
 * every action. A stale shell allow from an older hardening version is
 * likewise replaced rather than surviving behind the broad deny.
 */
export function mergeReviewAgentPermissions(
  existing: readonly AgentPermission[],
  policy: readonly AgentPermission[],
): AgentPermission[] {
  const governed = new Set(
    policy.filter((rule) => rule.action !== "*").map((rule) => rule.action),
  )
  const broad = policy.filter((rule) => rule.action === "*")
  const specific = policy.filter((rule) => rule.action !== "*")
  const preserved = existing.filter(
    (rule) => rule.action !== "*" && !governed.has(rule.action),
  )
  return [...broad, ...preserved, ...specific]
}

type AgentEditor = {
  update(id: string, update: (agent: { permissions: AgentPermission[] }) => void): void
}

/**
 * Install the shared policy on the three review agents. Called from setup;
 * a host without `agent.transform` keeps the safe fallback in each Markdown
 * agent, so this is an enhancement, not a prerequisite for read-only review.
 */
export async function installReviewAgentPolicy(ctx: {
  agent?: { transform?(callback: (editor: AgentEditor) => void): Promise<unknown> }
}): Promise<void> {
  if (typeof ctx.agent?.transform !== "function") return
  await ctx.agent.transform((editor) => {
    for (const id of REVIEW_AGENT_IDS) {
      editor.update(id, (agent) => {
        // Merge rather than replace: host rules for actions the policy does
        // not govern stay in place. The merge is idempotent because every
        // governed action is rebuilt from the policy on each load.
        agent.permissions = mergeReviewAgentPermissions(
          agent.permissions ?? [],
          reviewAgentPermissions(id),
        )
      })
    }
  })
}
