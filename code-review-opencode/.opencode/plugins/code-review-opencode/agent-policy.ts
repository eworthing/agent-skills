/**
 * Shared read-only policy for the three review agents.
 *
 * The same rules used to live in each agent's Markdown frontmatter, three
 * copies of a 150-line table. The plugin now installs this policy with
 * `ctx.agent.transform` at setup, so the git hardening and the permission
 * patterns are generated from `GIT_HARDENING` and cannot drift from the
 * commands `scope.ts` renders.
 */
import { GIT_HARDENING } from "./scope.ts"

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

const SHELL_DENY: AgentPermission[] = [
  // These commands can write (echo/sort/uniq, redirection, or `--output` on
  // git diff/log/show). The review agents must stay read-only.
  { action: "shell", resource: "*--output*", effect: "deny" },
  { action: "shell", resource: "*>*", effect: "deny" },
  // A prefix allow matches the whole command string, so a chained command
  // after an allowed git command could still run. Deny shell control operators
  // and process substitution outright; these rules come last, so they win.
  { action: "shell", resource: "*;*", effect: "deny" },
  { action: "shell", resource: "*|*", effect: "deny" },
  { action: "shell", resource: "*&&*", effect: "deny" },
  { action: "shell", resource: "*&*", effect: "deny" },
  { action: "shell", resource: "*$(*", effect: "deny" },
  { action: "shell", resource: "*`*", effect: "deny" },
  { action: "shell", resource: "*<(*", effect: "deny" },
  { action: "shell", resource: "*\n*", effect: "deny" },
  // A pager option would turn an allowed read-only command into arbitrary
  // code execution. The allowlist already requires --no-ext-diff/--no-textconv.
  { action: "shell", resource: "*--open-files-in-pager*", effect: "deny" },
  { action: "shell", resource: "*difftool*", effect: "deny" },
  // Space-prefixed patterns match a separate unsafe flag but not the safe
  // `--no-textconv` / `--no-ext-diff` spellings.
  { action: "shell", resource: "* --textconv*", effect: "deny" },
  { action: "shell", resource: "* --ext-diff*", effect: "deny" },
  // A config-env flag can point a read-only command at an external helper or
  // pager that executes arbitrary code. The hardened `-c` form is allowed;
  // every other config-env spelling and the short pager option stay denied.
  { action: "shell", resource: "*--config-env*", effect: "deny" },
  { action: "shell", resource: "*--paginate*", effect: "deny" },
  { action: "shell", resource: "* -O*", effect: "deny" },
]

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
  "review-finder": ["code_review_candidates"],
  "review-verifier": ["code_review_verdict", "code_review_group_verdicts"],
  "review-sweep": ["code_review_candidates"],
}

export const REVIEW_AGENT_IDS = Object.keys(ROLE_TOOLS)

/** Full permission list for one review agent. */
export function reviewAgentPermissions(agentID: string): AgentPermission[] {
  const tools = (ROLE_TOOLS[agentID] ?? []).map(
    (action): AgentPermission => ({ action, resource: "*", effect: "allow" }),
  )
  return [...READ_ONLY_POLICY, ...tools]
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
        const existing = agent.permissions ?? []
        // The plugin can be loaded more than once (global plus project
        // discovery). A policy already installed by another instance must not
        // be appended again: the rule list would grow on every load.
        if (existing.some((rule) => rule.action === "shell" && rule.resource.includes("core.hooksPath=/dev/null"))) {
          return
        }
        // Replace the Markdown fallback rules rather than stacking on them.
        // The full policy carries the same read/glob/grep/tool allows.
        const shared = new Set(["*", "read", "glob", "grep", ...(ROLE_TOOLS[id] ?? [])])
        const kept = existing.filter((rule) => !shared.has(rule.action))
        agent.permissions = [...kept, ...reviewAgentPermissions(id)]
      })
    }
  })
}
