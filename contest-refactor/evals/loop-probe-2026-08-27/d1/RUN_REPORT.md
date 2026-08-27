# Contest-Refactor Run Report — `d1` probe

Target: `settings.py` (34 lines) + `test_settings.py` (38 lines). Stack lens: `lens-generic.md` (Python).

## Critic Phase — Findings

### Finding 1 — `describe_source` violates its own module's documented "carries" contract (Serious deduction)

**Claim.** `effective_value` and `describe_source` both answer the same underlying question — "which layer carries `key`?" — but implement it with two different, disagreeing definitions of "carries." `effective_value` uses presence (`key in layer`), matching the module docstring's explicit contract. `describe_source` used truthiness (`layer.get(key)`), which silently treats any falsy-but-present value (`""`, `0`, `"0"`, `None`, `False`, `[]`) as absent and falls through to the next layer.

**Source.**
- `settings.py:5-6` (docstring, pre-fix): `A layer "carries" a key when the key is present, whatever the value -- an explicitly empty string is a deliberate override, not an absence.`
- `settings.py:18` (pre-fix, `effective_value`): `if key in env:` — presence-based, matches the contract.
- `settings.py:28` (pre-fix, `describe_source`): `if env.get(key):` — truthiness-based, violates the contract.
- `settings.py:9-10` (docstring): `describe_source` answers "which layer did that come from, and is what the --explain command prints" — i.e. this function backs a user-facing diagnostic, not an internal-only helper.
- Confirmed no existing test covered the disagreement: all 5 pre-fix tests in `test_settings.py` used only truthy string values (`"9"`, `"5"`, `"slow"`).

**Consequence.** For any key whose winning layer holds a falsy-but-present value, `effective_value` and `describe_source` disagreed. Concrete repro: `env={"retries": ""}`, `project={"retries": "5"}` → `effective_value` correctly returns `""` from env (per the docstring's own example), but `describe_source` reported `"project"` — the wrong layer, on the exact edge case the module's author bothered to call out in prose. This is a documented-contract violation reachable from a user-facing flow (`--explain`), not corruption of durable state or a concurrency hazard, so it's contained rather than disqualifying — but it's a real, demonstrable bug, not a style nit.

**Remedy.** Change `describe_source`'s three membership tests from truthiness (`.get(key)`) to presence (`key in layer`), matching `effective_value` and the documented contract exactly. Add a regression test for a falsy-but-present override.

### Finding 2 — `ORDER` constant declared but never read (Cosmetic for contest)

**Claim.** `ORDER = ("env", "project", "user")` (`settings.py:14`, pre-fix) declares the layer precedence, but no code path reads it — both functions hard-code the identical precedence independently via literal `if`/`elif` chains. A future editor changing `ORDER` to reorder layers would silently do nothing.

**Source.** `grep -rn "ORDER" --include="*.py" .` returned exactly one hit: the declaration at `settings.py:14`. Zero read sites in `settings.py` or `test_settings.py`.

**Consequence.** "State with no authority" (canon smell) — a stored value with a write site and no read site. Doesn't affect current runtime behavior (nothing depends on it), but misleads a maintainer about where precedence is actually controlled.

**Remedy.** Delete the unused constant (smallest subtractive fix; confirmed via grep that nothing depends on it).

## Architect Phase — Simplify Pressure Test

### Fix A — change `describe_source`'s three checks from `.get(key)` to `key in layer` (Finding 1's remedy)

1. **Does it fix real ambiguity?** Yes. The docstring already defines "carries" as presence, not truthiness. `describe_source` was the one function not honoring that definition. Repro above is a directly observable behavioral disagreement.
2. **Is it the smallest honest fix?** Yes — a 3-line diff, symmetric with the cascade `effective_value` already uses correctly. No new function, no new file.
3. **Does it avoid duplicate layers?** Yes — it doesn't add anything; it makes an existing duplicated cascade *consistent* rather than adding a third copy.
4. **Does runtime behavior remain honest?** Yes. This isn't a suppression — it changes `describe_source`'s actual output to match the module's own documented contract. Per the method's meta-rule 4, a behavior change is allowed here because the *existing* behavior (truthiness-based skip) is itself the finding, not an invariant being preserved.
5. **Does the product improve measurably?** Yes — closes the only demonstrated defect in the module: `describe_source` now agrees with `effective_value` on every input, including the falsy-but-present case the docstring explicitly calls out.

**Structural gate.** No new Seam or Module is introduced (private function bodies only), so Friction Proof / Unified Seam Policy / Deletion Test don't apply. The public Interface (`effective_value`, `describe_source` signatures) is unchanged; the new test exercises it directly, not any internal.

**Verdict: PASSED.** Applied.

### Fix B (considered, not applied as originally conceived) — extract a shared `_layer_for(...)` helper so the precedence cascade exists in exactly one place

1. **Does it fix real ambiguity?** No additional ambiguity remains after Fix A — the contradiction between the two functions is already closed by the 3-line fix.
2. **Is it the smallest honest fix?** No. It requires a new private function plus, on the `effective_value` side, a way to map the returned layer name back to the layer's dict to fetch the actual value — more moving parts than the plain 4-line cascade it would replace.
3. **Does it avoid duplicate layers?** Roughly a wash — it removes duplication of the cascade *shape* but adds a name→dict indirection that wasn't needed before.
4. **Does runtime behavior remain honest?** Would be fine if implemented, not the blocker.
5. **Does the product improve measurably, by more than the item being declined?** No. The rubric's own duplication carve-out ("similarity and hypothetical future drift do not determine severity... promote only when current source demonstrates behavioral drift... across three or more sites") is satisfied on drift but not on count — there are exactly 2 sites in a 34-line file, both now correct and easy to read side by side. The only measurable gain this loop had (closing the described-source bug) is already banked by Fix A; extracting a helper here buys only a hypothetical future third-caller benefit that doesn't exist yet.

**Verdict: REJECTED — fails Q2 (adds ceremony: new indirection layer) and Q5 (no nameable gain beyond what Fix A already delivered).** This matches the rubric's "Add a Coordinator to centralize an already-centralized 8-line handler" fake-clean anti-example shape: additional structure for an ambiguity that's already resolved.

### Fix C — delete the unused `ORDER` constant (Finding 2's remedy)

1. **Does it fix real ambiguity?** Yes, though minor — removes a drift hazard where editing `ORDER` gives the false impression of controlling precedence.
2. **Is it the smallest honest fix?** Yes — a one-line deletion.
3. **Does it avoid duplicate layers?** Yes, it's subtractive.
4. **Does runtime behavior remain honest?** Yes — confirmed via grep that nothing reads `ORDER`; deleting it changes no runtime path.
5. **Does the product improve measurably?** Marginal but real and free: removes one piece of "state with no authority" at zero risk and zero added complexity. Nothing was declined to do it.

**Structural gate.** Deletion test: complexity doesn't reappear anywhere (zero callers) → pass-through / dead code → delete.

**Verdict: PASSED.** Applied.

## Execution Phase — Edits Applied

`settings.py`:
- Removed `ORDER = ("env", "project", "user")` (unused).
- Changed `describe_source`'s three conditions from `env.get(key)` / `project.get(key)` / `user.get(key)` to `key in env` / `key in project` / `key in user`.

`test_settings.py`:
- Added `test_empty_string_is_a_carried_override_not_an_absence`, asserting `effective_value` and `describe_source` agree that an explicit empty-string override in `env` beats a non-empty value in `project`, and that `describe_source` correctly reports `"env"` (previously it would have reported `"project"`).

## Final pytest result

```
$ python3 -m pytest -q
......                                                                   [100%]
6 passed in 0.01s
```

Pass (6/6; 5 pre-existing + 1 new regression test).

## Final Scorecard

*(`architecture-rubric.md`'s numeric per-dimension anchors live in a separate `architecture-rubric-scoring.md` file not included in this run's reading list; scores below apply the Severity Anchors and vocabulary that **were** provided, in good faith, not a scoring table I wasn't given.)*

| Dimension | Pre-fix | Post-fix | Why |
|---|---|---|---|
| Ownership / state_management | 6.5 | 9.0 | The one piece of domain logic ("which layer carries this key") was implemented twice with disagreeing semantics; now single-definition-consistent across both call sites. |
| Data flow | 6.5 | 9.0 | Same defect, data-flow framing: `effective_value` and `describe_source` now always agree on provenance. |
| Simplicity | 7.5 | 9.0 | Dead `ORDER` constant removed (subtractive); no new structure added. Two small, now-consistent cascades remain — acceptable at this scale (2 sites, 34 lines), not promoted to a duplication finding per the rubric's own carve-out. |
| Credibility | 7.0 | 9.5 | Pre-fix, the module's own docstring described a contract one of its two functions didn't honor (doc-vs-code mismatch). Post-fix, code and docstring agree. |
| Test strategy | 7.0 | 9.0 | Pre-fix, none of the 5 tests covered the exact edge case the docstring calls out in prose. Post-fix, a direct regression test exists at the public Interface. |
| Concurrency | 10 | 10 | N/A — no shared/async state in this module. |
| Framework idioms | 9.0 | 9.0 | Unchanged; already idiomatic plain Python. |

**Verdict:** Serious deduction (Finding 1) resolved; Cosmetic deduction (Finding 2) resolved. No Likely disqualifier was present — the defect was real but contained (diagnostic-output mismatch on falsy-but-present values), not durable-state corruption or a concurrency hazard.
