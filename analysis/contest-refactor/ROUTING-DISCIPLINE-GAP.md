# Routing Discipline Gap — contest-refactor lens dispatch + handoff routing

Source: `refs/competitors/alirezarezvani-claude-skills/` (16.1k★, MIT, added 2026-05-25 p.m.) — signal-based deterministic router with Matt-Pocock-style forcing-question pattern. Demonstrated in `business-operations/skills/business-operations-skills/SKILL.md` (lines 1-100).

## Baseline: contest-refactor today

Contest-refactor makes routing decisions at multiple points:

| Routing point | Current mechanism | Determinism |
|---|---|---|
| Step 0 lens selection (apple / generic) | heuristic stack detection (looks for `*.swift`, `Package.swift` → apple) | Mostly deterministic |
| Step 1 Critic specialty-lens dispatch (per SPECIALTY-LENS-DISPATCH-GAP) | heuristic per finding's risk type | Heuristic |
| Phase 1.4 Routing (per STATE-MACHINE-COMPOSITION-APPENDIX) | based on backlog state + halt subtypes + governance context | Rule-based |
| HALT subtype selection | rule-based per stagnation cause (`no_progress`, `oscillation`, `user_decision`, `no_backlog`) | Mostly deterministic |
| Backlog priority selection (per ROI-PRIORITIZATION-GAP) | Critic-assigned priority (1-3) + optional forensic-skills hotspot×complexity | Heuristic with optional formula |

What contest-refactor DOESN'T have:

- A **routing-discipline framework** that systematizes routing decisions across all 5 routing points
- A **forcing-question protocol** when routing confidence is low — currently the Critic just picks (silently)
- A **canon vocabulary** for routing signals (what counts as a "signal" to trigger which route?)
- A **digest discipline** post-route (currently routes don't necessarily emit a structured rationale)

## alirezarezvani's mechanism

Documented in `business-operations/skills/business-operations-skills/SKILL.md` (synthesized via 2026-05-25 inspection):

1. **Signal classes**: orchestrator declares N keyword/pattern classes (PROCESS/VENDOR/CAPACITY/COMMS/KNOWLEDGE/PROCUREMENT in their case)
2. **Two-signal threshold**: 2 signals matched = confident route; orchestrator routes silently to chosen sub-skill
3. **One-signal forcing question**: 1 signal matched = ambiguous; orchestrator asks user a single forcing question WITH RECOMMENDED ANSWER ("It sounds like you want process-mapping for your X workflow. Confirm? [Y/n]")
4. **Never silent post-question**: after asking, orchestrator MUST surface its reasoning before executing the routed sub-skill
5. **Routed digest**: after sub-skill returns, orchestrator surfaces a ≤200-word digest citing the canon source (e.g., "Goldratt's Theory of Constraints for bottleneck findings")

This is a **Matt Pocock pattern** — surface the LLM's reasoning before it acts, give user one clear way to redirect.

## Gap matrix

Legend: **✓** = present, **partial** = weaker form, **—** = absent, **n/a** = doesn't apply.

| Routing point | contest-refactor | alirezarezvani | Adopt signal+forcing-question? |
|---|---|---|---|
| Lens selection (Step 0) | heuristic stack detection | signal-based router | PARTIAL — extend with explicit signal classes when stack is ambiguous (e.g., Swift + JS hybrid repo: ask "which lens primary?") |
| Critic specialty-lens dispatch | heuristic | signal-based + forcing question | YES — formalize "what signals trigger security lens vs perf lens vs concurrency lens" + ask user when ambiguous |
| Phase 1.4 Routing | rule-based | signal-based | PARTIAL — current rules work; could add ambiguity-detection that triggers forcing question |
| HALT subtype selection | rule-based | n/a (no halt states) | NO — current rule-based is correct |
| Backlog priority selection | heuristic + optional formula | signal-based per pod | NO — keep current; formula-based ordering is the right direction per ROI-PRIORITIZATION-GAP |
| Digest discipline post-route | partial (CURRENT_REVIEW.json captures decision but not always rationale) | ✓ ≤200-word digest | YES — add explicit `routing_rationale` field |

## Strategic insight

Contest-refactor's routing is MOSTLY correct as-is. The biggest gain from alirezarezvani's pattern is:

1. **Explicit signal classes documented in canon** (e.g., `canon/critic-lens-signals.toml`) — instead of heuristic "looks like a security finding"
2. **Forcing question on ambiguity** instead of silent guess — surfaces uncertainty to user
3. **`routing_rationale` digest** captured per route decision

These are LOW-cost additive improvements. Don't redesign the routing layer; instrument it.

## P2 GAPS — what to potentially adopt

### Gap A: Canon vocabulary for Critic specialty-lens signals (extends SPECIALTY-LENS-DISPATCH-GAP)

Today SPECIALTY-LENS-DISPATCH-GAP describes WHICH specialty lenses exist (security / perf / concurrency / accessibility / etc.). It doesn't describe HOW the Critic determines which lens applies to a given finding.

**Adopt** new canon file `canon/critic-lens-signals.toml`:

```toml
[security_lens]
signals = [
  "credential",
  "secret",
  "api_key",
  "token",
  "password",
  "ssh_key",
  "private_key",
  "shell_injection",
  "sql_injection",
  "xss",
  "path_traversal",
  "deserialization",
  "csrf",
  "open_redirect",
  "race_condition_with_security_implication"
]
threshold_confident = 2  # 2+ signals → security lens applied silently
threshold_forcing = 1    # 1 signal → ask user "this looks security-relevant; apply security lens?"
canon_reference = "references/lens-security.md"

[performance_lens]
signals = [
  "n_plus_one",
  "unbounded_loop",
  "synchronous_io_in_async_context",
  "memory_leak_pattern",
  "cache_miss",
  "premature_optimization",
  "big_o_violation"
]
threshold_confident = 2
threshold_forcing = 1
canon_reference = "references/lens-performance.md"

# ... per specialty lens
```

**Implementation**: Critic Phase 1.0 reads `canon/critic-lens-signals.toml`, scans each finding for signal matches. Per-finding signal counts feed lens-dispatch decision.

### Gap B: Forcing-question protocol in Critic Phase

When signal threshold is `>= threshold_forcing` but `< threshold_confident`, Critic emits a forcing question into `CURRENT_REVIEW.json.routing_question` field:

```jsonc
{
  "routing_question": {
    "finding_id": "F12",
    "ambiguous_lens": "security",
    "matched_signals": ["api_key"],
    "recommended_action": "Apply security lens (api_key matched but only 1/2 signals required)",
    "alternatives": ["Skip security lens; treat as ordinary refactor finding"]
  }
}
```

Step 12 loop dispatch checks for `routing_question` → if present AND `--non-interactive` not set, surfaces to user; if `--non-interactive`, accepts recommended action + logs to errors.jsonl.

### Gap C: Routing rationale digest

Every routing decision emits a structured `routing_rationale` field:

```jsonc
{
  "loop_routing": {
    "phase": "1.4",
    "decision": "CONTINUE",
    "rationale": "3 priority-1 findings remain; not yet HALT_SUCCESS candidate. Next action: Architect plan for F1+F3+F8.",
    "signals_considered": ["pending_findings: 3", "halt_candidate: false", "loop_cap: 7/15"],
    "alternatives_rejected": ["HALT_STAGNATION: rejected (progress made loop 6→7)", "HALT_LOOP_CAP: rejected (under cap)"]
  }
}
```

Useful for post-hoc debugging "why did loop 7 not halt?" — the routing rationale makes the decision one-line readable.

## What NOT to import

| Tempting | Why skip |
|---|---|
| Full keyword-based router for ALL routing decisions | Contest-refactor's halt-subtype + backlog-priority routing already work; keyword-based would regress to fragile string matching. |
| 200-word natural-language digest as primary record | Structured JSON > prose for autonomous-loop analytics. Use prose only as `rationale` field within JSON. |
| User-facing forcing question on every loop | Annoying. Forcing question only when signal threshold is genuinely ambiguous (`>= threshold_forcing` AND `< threshold_confident`). Otherwise silent confident route or silent rule-based decision. |
| Signal-class taxonomy across ALL contest-refactor decision points | Over-engineering. Signal classes for Critic specialty-lens dispatch (Gap A) where the heuristic is weakest; not for halt-state which is already deterministic. |

## Adoption order

1. **Gap C (routing_rationale digest)** — additive field per CURRENT_REVIEW.json; trivial schema bump. Useful immediately for post-hoc debugging.
2. **Gap A (canon/critic-lens-signals.toml)** — formalize the heuristic Critic already uses informally. Document signals + thresholds per lens. Medium lift; depends on SPECIALTY-LENS-DISPATCH-GAP being settled.
3. **Gap B (forcing-question protocol)** — depends on Gap A. Most user-visible change. Highest UX value; requires testing on real interactive runs to tune threshold ratios.

## Pairing with other gap docs

- **SPECIALTY-LENS-DISPATCH-GAP**: Gap A extends it (signal-canon). Defines HOW dispatch happens given the WHICH it documents.
- **TWO-LAYER-DETECTION-GAP**: complementary. Two-layer detection is per-finding (grep candidate → context verify). Routing-discipline is per-decision-point (which lens / which subagent / which halt-subtype).
- **HALT-STATE-GAP**: this doc's Gap C (routing_rationale) overlaps Gap D (session_resume_class) — both add audit-only fields. Different focus (per-decision vs per-resume); both worth shipping.
- **CRITIC-INDEPENDENCE-GAP**: when Critic is split into subagent, signal-canon (Gap A) lives in Critic subagent's read-set. No conflict.
- **STATE-MACHINE-COMPOSITION-APPENDIX**: Phase 1.4 Routing description should reference this doc's Gap C `routing_rationale` field.
