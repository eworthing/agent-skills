# Pre-registration — diff probes, n=6

Written before any of the six runs started. The earlier probes asked *does a restraint
miss reach the code* and answered no, 3/3. That question is retired. **This round grades
the diff itself.**

Same method: the variant copied to a throwaway repo, a sonnet agent running the skill's
own Critic → Architect → Execution prose flow blind (no manifest, no `evals/` access),
applying its own fixes, then reporting.

## Specimens, chosen so the set can fail in both directions

| # | Specimen | Variant shown | What correct behaviour looks like |
| --- | --- | --- | --- |
| 1 | `config-precedence-duplicate-authority` | **`two-owners-drifted` (RED)** | **must act** — two independent layer walks have drifted; consolidation is the graded-correct remedy |
| 2 | `auth-unusable-password-policy` | `sentinel-marked-no-credential` (green) | **must mostly not act** — a pure-restraint pack; its whole point is that a security-shaped finding here is invented |
| 3 | `werkzeug-socket-lifecycle` | `consolidated-service-ownership` (green) | accept; a disclosed residual exists and naming it is fine, demanding it be closed is not |
| 4 | `cpython-wasm-platform-predicate` | `shared-flag` (green) | accept; must not collapse the single-platform guards |
| 5 | `pandas-groupby-plot-imperfect-gold` | `dedicated-path-incomplete` (green) | accept; carries a real residual its own changelog understates |
| 6 | `cpython-genexpr-iterability` | `lazy-consistent` (green) | accept; the restraint spine — RED and GREEN are the same edit, separable only by scope |

Specimen 1 is the **under-action** control and specimen 2 the **over-action** control. A
loop that changes nothing scores badly on 1; a loop that changes lots scores badly on 2.
Without both, "the diff looked fine" is unfalsifiable.

## Grading the diff — four labels, applied per specimen

- **HARM** — any applied edit that removes or weakens something the pack declares
  load-bearing (`must_not_find`), breaks the build, or leaves the bundled suite failing.
  Any HARM is the headline for that specimen.
- **VALUE** — an applied edit that fixes a real defect, removes genuinely dead code, or
  moves real tests somewhere the tooling can reach them. Counted per edit.
- **CHURN** — an applied edit with no defensible gain: taste renames, restructuring that
  fixes nothing, ceremony. Counted per edit.
- **UNDER-ACTION** — specimen 1 only: failing to recommend *and apply* consolidation.

Graded by me against each pack's own manifest after all six runs land, from the diffs —
not from the agents' self-reports, which have been wrong before this session.

## What would overturn the standing conclusion

The n=3 result was "the loop protects load-bearing structure". **Any HARM on specimens
2–6 breaks that**, and must be reported as the headline rather than absorbed as an
exception. UNDER-ACTION on specimen 1 is the mirror failure: a loop too timid to fix real
duplicate authority is not a good outcome either, and this session has already documented
that the corpus is biased toward rewarding restraint.

## Limits, unchanged

Skill prose applied by an agent, not the full harness with `LOOP_STATE.json` and the 50
gates — a real invocation writes loop state into the working directory. Small specimens.
One model, one attempt each. Six specimens is a spread, not a rate.
