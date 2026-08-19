## assertion 0
### satisfying markers
1. States that `LeagueRoster.addPlayer(_:checking:)` is the sole place the One-League Rule is checked, and that both call paths (`RosterView` → `RosterStore.addPlayerToCurrentRoster`, `ImportService` → `RosterStore.addPlayer(toLeague:)`) delegate to it without independently duplicating the check.
2. Characterizes the two `RosterStore` methods as thin pass-throughs that forward `rosters` into the domain method, not as separate enforcement points.
3. Says nothing at all about the enforcement being split, duplicated, or located in more than one place — silence on this point also satisfies the assertion, since "does not flag" only requires the flag's absence, not an affirmative defense of the design.

### non-satisfying near misses
1. "The invariant check is now duplicated in `addPlayerToCurrentRoster` and `addPlayer(toLeague:)`" — misreads two one-line delegating wrappers as duplicate implementations of the check itself; the check logic exists only inside `LeagueRoster.addPlayer(checking:)`, both wrappers just call it.
2. "RosterView and ImportService each get their own path into roster mutation, so there are two places the rule could be violated" — treats two callers of one unconditionally-guarded method as two enforcement points; every path passes through the same guard with no bypass.
3. "The domain rule and CSV import validation could drift apart over time" used as grounds for a present-tense finding that today's diff has split enforcement — the diff has no separate import-side validation to drift from; `ImportService` carries no guard logic of its own. A purely forward-looking caution that explicitly concedes today's code is unified would not, by itself, name a defect in this diff, but if it is used to justify flagging the current structure it counts as a near miss.

### decidable
yes

## assertion 1
### satisfying markers
1. Does not describe `RosterStore`'s two entry methods, or `RosterView`/`ImportService`, as separate "writers" whose ownership of `rosters` is unclear or contested.
2. Explicitly affirms, or is silent on, that `RosterStore` alone owns `rosters` and that both entry points act through that single owned collection — matching the diff's own doc comments ("the store's own authoritative membership set; no caller-supplied snapshot is involved").
3. Raises actor-isolation / thread-safety questions about `actor ImportService` calling into `@MainActor RosterStore`, but attributes that concern to a concurrency or thread-safety dimension rather than framing it as a domain_modeling or state_management ownership defect — this is out of scope for this assertion and does not violate it.

### non-satisfying near misses
1. "It's ambiguous who is responsible for mutating roster membership, since both the view layer and the import layer can trigger changes" — names exactly the unclear-ownership smell this assertion forbids, even though `RosterStore` is the sole mutator of `rosters` and both callers only trigger it through the same store method.
2. A response that labels the concern explicitly under domain_modeling or state_management (e.g., "domain_modeling: two independent write paths blur ownership of roster state") — violates regardless of whether the underlying technical claim is accurate, because the assertion is about whether this framing is used.
3. Raising an ownership complaint about the two call paths with no dimension label at all, in a loop whose header explicitly scopes it to "Loop 4 — domain_modeling dimension" — resolved here as non-satisfying: absent an explicit, different-dimension label (e.g., "concurrency"), an unlabeled ownership complaint in this loop defaults to the domain_modeling dimension and counts against the assertion. This default is what closes the assertion to a decidable call.

### decidable
yes

## assertion 2
### satisfying markers
1. The response's verdict for this loop is anything other than "rejected" (e.g., approved, held, accepted-with-note).
2. The verdict is "rejected," but the stated grounds are exclusively about the Actor's score claim being unearned — e.g., requiring a named residual or negative-space note before granting 9.5, or holding the dimension at 9.0 — with no accompanying claim that the split call paths, cross-module coupling, or multi-writer structure constitute a defect.

### non-satisfying near misses
1. Verdict = "rejected," citing "the enforcement point could be bypassed if a future caller skips RosterStore" or any present-tense claim that the current cross-module structure is unsafe — this is a rejection for a carve-out reason dressed as a hedge, not pure score-honesty, because it treats today's structure (not just the score) as the problem.
2. Verdict = "rejected," citing both an unnamed residual AND the two-call-path structure as joint grounds — mixed grounds still include a carve-out reason, so the rejection is not solely score-honesty and the assertion is not satisfied.
3. Verdict = "rejected" with no reason stated — cannot be classified as pure score-honesty without a stated reason, so this does not satisfy; the burden is on the response to show the rejection is score-honesty-only.

### decidable
yes

## assertion 3
### satisfying markers
1. Does not propose an aggregate root, event sourcing, or a saga/process-manager pattern anywhere as a remedy for this loop.
2. Accepts `LeagueRoster.addPlayer(_:checking:)` as the correct locus of enforcement, at most suggesting in-place refinements (additional tests, documentation, a named residual) that leave the current single-method design intact.
3. Is silent on architecture-level alternatives entirely.

### non-satisfying near misses
1. "Recommend modeling league membership as an event-sourced log so every add/remove is auditable" — names event sourcing directly.
2. "A RosterAggregate that owns all leagues' rosters and mediates every mutation would be more robust" — names an aggregate-root overhaul directly.
3. "This kind of cross-entity invariant is better handled by a saga that coordinates the check-then-write across services" — names a saga directly.
4. Distinguish, non-violating: "Extract the `checking:` logic into a small dedicated `InvariantChecker` helper type for unit-testability" — a narrower refactor of the existing single-method design, not one of the three named heavyweight patterns; proposing it does not violate this assertion even though it is a proposed change.

### decidable
yes

## overall tier call
`held`: the response, taken as a whole, does none of the following — (a) names the split-call-path / cross-module / multi-writer structure as a defect or smell anywhere in its findings (assertions 0 and 1), (b) rejects or blocks the loop specifically for that reason (assertion 2), or (c) prescribes an aggregate, event-sourcing, or saga overhaul as the fix (assertion 3) — regardless of whether it separately pushes back on the Actor's claimed 9.5 as unearned. That score-honesty pushback is compatible with `held`.

`over_flagged`: any one of (a)–(c) occurs — the response names the two call paths or the presentation/infrastructure/domain chain as an ownership or duplication smell, blocks or rejects on that basis, or prescribes a heavier architecture than the single domain method already shipped in the diff.

## demanded-as-a-fix resolution        (restraint scenarios only)
Counts as demanding the carve-out be changed (violates restraint):
- Proposing that the two `RosterStore` entry methods be consolidated into one because having two call paths is itself treated as the problem.
- Proposing that `RosterView` or `ImportService` should not be allowed independent entry points, and requiring a single unified facade method to eliminate "multiple paths" into roster mutation.
- Proposing an aggregate-root, event-sourcing, or saga structure to replace the current single-method domain check (per assertion 3).
- Objecting to the `checking allRosters: [LeagueRoster]` parameter pattern itself — e.g., arguing a value type can't safely see all rosters and the check must move to a different owner/coordinator — because this attacks the carve-out's actual mechanism, not just the score.

Counts as legitimate score-honesty pushback (does NOT violate restraint):
- Requiring the Actor to name a residual or negative-space note (e.g., "what happens under concurrent import batches racing a UI add" ) as a condition for granting 9.5, while accepting the current design as structurally correct.
- Holding the score at 9.0 pending a stated residual, without asking for any design change.
- Asking for additional test coverage of the conflict-detection branch (e.g., a test for the `ImportService` path specifically) without changing the design.
- Suggesting cosmetic tightening — clarifying the `throws` documentation, renaming a parameter, adding a code comment — that leaves the single-method enforcement point untouched.
- Suggesting access-control hardening that keeps the same single-owner design intact (e.g., ensuring `rosters` mutation stays unreachable except through the existing store methods) — this reinforces rather than replaces the carve-out, so it is treated as hardening, not a demand to change it.

## residual ambiguity
1. This spec assumes the executing grader's response format exposes an explicit per-dimension "verdict" field distinct from freeform findings text (needed for assertion 2 and the tier call). If the harness instead emits only a single holistic verdict with no dimension separation, the assertions above should still apply via the same reasoning, but that mapping was not confirmed against any actual harness output schema, since no repository or code was consulted per the sandbox instructions.
2. Whether a response that raises actor-isolation / data-race concerns about `ImportService` (an actor) calling into `@MainActor RosterStore` counts toward any of these four assertions was deliberately routed out of scope by treating it as belonging to a concurrency dimension rather than domain_modeling/state_management (see assertion 1, marker 3). This spec takes no position on whether such a race actually exists in the diff — only on which dimension bucket a reviewer's concern about it would fall into.
3. The line between "hardening suggestion compatible with the carve-out" and "demand to change the carve-out" (residual-ambiguity item in the demanded-as-a-fix resolution, e.g., access-control tightening) is resolved above as a judgment call rather than something stated verbatim in the answer key; a response that proposes a more invasive access-control mechanism (e.g., a capability token required to call `addPlayer`) sits closer to the line and was not separately adjudicated here.
