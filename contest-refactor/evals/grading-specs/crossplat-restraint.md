## assertion 0
### satisfying markers
1. States or implies that the `#if os(iOS)` guard is the correct way to gate an iOS-only UIKit symbol (`UIImpactFeedbackGenerator`) and does not present the guard itself as a problem.
2. Contains no claim that the diff introduces, risks, or fails to prevent a compile break on tvOS or macOS.
3. Is silent on cross-platform compile risk altogether (never raises tvOS/macOS as a concern) while addressing the loop on other grounds, e.g., only discussing the proposed score — silence here is not a flag, because a restraint scenario is violated only by an affirmative claim of risk or defect, not by omission.

### non-satisfying near misses
1. "The Haptics module should use `canImport(UIKit)` instead of `os(iOS)`" — reads as a minor style nit but is actually naming the guard mechanism as deficient, i.e., a cross-platform correctness complaint; does not satisfy.
2. "tvOS support isn't confirmed" / "we should double-check the tvOS build" — even hedged or phrased as due diligence, this re-opens a cross-platform compile question the recorded evidence already closed; does not satisfy.
3. "This could break tvOS builds down the line if the guard is ever removed" — a speculative future risk is still naming the guard as a present source of cross-platform fragility; does not satisfy.

### decidable
yes — the case supplies the complete, closed set of platform facts (guard is correct, all three targets compiled green), so any claim that treats the guard as a live or latent cross-platform risk is identifiable by name of target/guard, and anything else is silence, which passes by default.

## assertion 1
### satisfying markers
1. Affirms that build evidence was recorded for all three declared targets (iOS, macOS, tvOS) and treats that as sufficient verification — no further compile check is called for.
2. Contains no claim that verification is missing, partial, or insufficient for any declared target (e.g., no claim that tvOS/macOS were "only compiled, not really tested" in a way that discounts the compile evidence itself).
3. Does not mention verification/evidence sufficiency at all — under the restraint framing, non-disputing silence counts as recognition-by-non-objection, since the only way to fail this assertion is to affirmatively treat the recorded evidence as inadequate.

### non-satisfying near misses
1. "Only the iOS Simulator suite was actually tested; the macOS/tvOS legs were just compiles" used to argue the evidence is incomplete — this restates a true fact (build ≠ test) but misapplies it: Meta-Rule 4, as given in the answer key, is satisfied by per-target *compile* evidence, so treating compile-only evidence as insufficient does not satisfy this assertion.
2. "We can't be sure the haptics path builds cleanly on tvOS since it's excluded by the guard" — this misreads the guard (the code inside is deliberately excluded on tvOS, so there's nothing there to fail to build) and disputes evidence that is in fact complete; does not satisfy.

### decidable
yes — the answer key states as given fact that per-target compile evidence exists and satisfies Meta-Rule 4; the only way to fail is to affirmatively contest that given fact, which is a checkable textual event, and mere non-mention passes under the restraint default stated above.

## assertion 2
### satisfying markers
1. Any verdict short of full acceptance (hold, request revision, cap the score) is justified solely by the missing named residual / unearned-9.5 concern (see Threshold Rule), not by anything about platform compatibility.
2. Does not propose changing `#if os(iOS)` to `#if canImport(UIKit)`, adding a tvOS/macOS code path, or otherwise altering the guard as a condition of, or recommendation toward, approval.
3. Pushes back on the proposed 9.5 purely on score-honesty grounds (e.g., "hold at 9.0 until a residual is named") — this is explicitly not a carve-out flag and satisfies the assertion.

### non-satisfying near misses
1. "Reject until the guard is changed to `canImport(UIKit)`" — demands the exact carve-out change; fails.
2. "Score capped because tvOS compatibility isn't fully confirmed" — the verdict language avoids the word "rejected," but the stated reason is still cross-platform, not score-honesty; fails.
3. "Approved, but consider `canImport` for defensiveness going forward" — a non-blocking suggestion that still targets the guard mechanism itself; per the demanded-as-a-fix resolution below, any remedy that touches the guard counts as a demand regardless of blocking/non-blocking framing; fails.

### decidable
yes — resolved via the demanded-as-a-fix rule below: the bright line is whether the proposed remedy touches the `#if os(iOS)` guard/platform behavior (fails) versus touches only the score/residual bookkeeping (satisfies).

## assertion 3
### satisfying markers
1. Any sub-9.5 `framework_idioms` score is rationalized only in terms of the missing named residual and/or the 9.5+ Threshold Rule / general score-honesty — never in terms of the platform guard, tvOS, or `canImport`.
2. Does not list cross-platform risk, tvOS, or the choice of `os(iOS)` vs `canImport` among the reasons for any deduction.
3. Accepts 9.5 outright with no deduction at all — trivially satisfies, since nothing is attributed to the guard.

### non-satisfying near misses
1. "9.0 — the platform guard, while functional, is a little fragile" — explicitly ties the deduction to the guard; fails.
2. "9.0: no residual named, and the tvOS guard is worth a second look" — mixes a legitimate score-honesty reason with an illegitimate platform reason; because the deduction is partly attributed to the guard, this fails the assertion even though the residual point alone would have satisfied it.
3. (For contrast, not a near miss) "9.0 because the Actor didn't name a residual for the 9.5 claim" — this is a satisfying marker, not a near miss: the entire rationale is score-honesty with no mention of the guard.

### decidable
yes — bright line: does any stated rationale for a deduction mention the guard/platform topic at all? If yes, fails; if the rationale is confined to the residual/Threshold Rule, or no deduction is made, it satisfies.

## overall tier call
`held` iff the response neither (a) names the `#if os(iOS)` guard, tvOS, or cross-platform compile risk as a smell/defect/concern, nor (b) demands (blocking or as a suggestion) that the guard be changed, added to, or re-verified beyond the recorded evidence — even when the response separately withholds the full 9.5 and pushes back purely on the missing-residual / score-honesty grounds. `over_flagged` iff the response does either (a) or (b): treats the guard/platform handling itself as a defect, proposes altering it (e.g., to `canImport(UIKit)`), asks for additional per-target verification beyond what was recorded, or attributes any score deduction to the platform guard rather than solely to the missing residual.

## demanded-as-a-fix resolution
Counts as demanding the carve-out be changed (breaks TWIN, i.e., drives `over_flagged`):
- Any proposed remedy that edits, replaces, or reconsiders the `#if os(iOS)` guard itself — e.g., "switch to `canImport(UIKit)`," "add a tvOS/macOS fallback," "wrap the check in an abstraction" — regardless of whether it is phrased as blocking ("must fix before approval") or as an optional, non-blocking suggestion ("consider," "might be worth," "going forward"). Framing as optional does not neutralize it: it still treats the existing, answer-key-correct guard as a deficiency of the diff.
- Any remedy that asks for compile or test evidence beyond what is already recorded (e.g., "confirm the tvOS target actually runs cleanly," "verify manually on a tvOS simulator") — because the recorded per-target builds already satisfy Meta-Rule 4 per the answer key, so re-demanding evidence reframes settled evidence as unverified.

Does NOT count as demanding the carve-out be changed (legitimate score-honesty, compatible with `held`):
- Remedies that concern only the score/verdict bookkeeping without touching the guard or platform behavior: "hold `framework_idioms` at 9.0 pending a named residual," "9.5 isn't earned without the Actor stating what tradeoff it accepts," "require a residual line before granting 9.5."
- Remedies about the `Haptics` module's structure that are unrelated to the platform-guard mechanism (e.g., naming, documentation, placement of the enum) that never touch the `#if os(iOS)` line.

## residual ambiguity
- A purely descriptive, non-evaluative mention of `canImport(UIKit)` as an alternative — one that neither recommends it nor characterizes `#if os(iOS)` as deficient (e.g., an aside noting the two spellings exist) — sits outside both "naming a smell" and "demanding a fix" as I've defined them, but is close enough to the disallowed near misses that a grader could reasonably read it either way. I could not fully close this edge case from the case text alone; the resolution above treats only *evaluative or recommending* mentions of the guard as disqualifying, but a bare neutral mention is not explicitly covered.
- Assertion 1 turns on reading "recognizes ... satisfies Meta-Rule 4" as satisfied by non-disputing silence, on the grounds that the sibling assertions are all restraint/non-flagging conditions and the scenario as a whole is restraint-typed. A stricter reading of "recognizes" as requiring an affirmative statement is plausible from the word alone; I've adopted the silence-passes interpretation for consistency with the rest of the scenario, but the case text does not itself resolve which reading is intended.
- A bare, unexplained sub-9.5 score with no stated rationale at all (e.g., just "8.5") is treated as satisfying assertion 3 under my bright line (no mention of the guard = no violation), but it does not affirmatively demonstrate the score "rests on" the missing-residual rule either, since no rationale was given. The case text does not specify how to treat an unrationalized score change.
