/**
 * The one mapping from a review role to its OpenCode agent ID. The engine
 * spawns these agents; the policy installer patches the finder/verifier/sweep
 * IDs, while the synthesizer keeps its minimal tool-only policy in
 * review-synth.md. Keeping the IDs here means a rename cannot leave the
 * engine pointing at a different agent.
 */
export const AGENT_IDS = {
  finder: "review-finder",
  verifier: "review-verifier",
  sweep: "review-sweep",
  synthesize: "review-synth",
} as const
