/**
 * The one mapping from a review role to its OpenCode agent ID. The engine
 * spawns these agents and the policy installer patches them; keeping the IDs
 * here means a rename cannot leave one side pointing at an agent the other
 * never uses.
 */
export const AGENT_IDS = {
  finder: "review-finder",
  verifier: "review-verifier",
  sweep: "review-sweep",
  synthesize: "review-synth",
} as const
