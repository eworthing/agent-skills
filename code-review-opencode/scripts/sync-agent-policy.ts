/**
 * Rewrite the fallback `permissions:` block in each review agent's Markdown
 * frontmatter from the shared policy module. The static block is only a
 * fallback for hosts without `ctx.agent.transform`; keeping it generated
 * prevents a hand-copied table from drifting from `READ_ONLY_POLICY`.
 *
 * Run from the skill root:
 *   node scripts/sync-agent-policy.ts
 */
import { readFileSync, writeFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"
import {
  REVIEW_AGENT_IDS,
  renderAgentPolicyYaml,
} from "../.opencode/plugins/code-review-opencode/agent-policy.ts"

const agentsDir = fileURLToPath(new URL("../.opencode/agents/", import.meta.url))
const BLOCK = /^permissions:\n[\s\S]*?(?=^---$)/m
const check = process.argv.includes("--check")
let stale = false

for (const id of REVIEW_AGENT_IDS) {
  const path = join(agentsDir, `${id}.md`)
  const text = readFileSync(path, "utf8")
  if (!BLOCK.test(text)) {
    throw new Error(`${path}: no permissions block found before the closing frontmatter fence`)
  }
  const next = text.replace(BLOCK, `${renderAgentPolicyYaml(id)}\n\n`)
  if (check) {
    if (next !== text) {
      stale = true
      console.error(`stale: ${path}`)
    }
  } else {
    writeFileSync(path, next)
    console.log(`updated ${path}`)
  }
}
if (check && stale) process.exitCode = 1
