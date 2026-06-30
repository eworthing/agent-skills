# Efficacy pass — 2026-06-29

writing-skills TDD on `peer-plan-review`. Live baseline (RED) + micro-test (GREEN/REJECT).
Cost-capped: Haiku/Sonnet/Codex-mini only, effort=medium, no Opus reviewers.

## Live baseline — 5 runs, fixture `digest-plan.md`

| Run | Model / effort | Stance | Verdict | B-SEQ | B-ROLLBACK | B-UNDEF | B-UNDERSPEC | B-TOOLARGE | B-DOMAIN | N-OBS | FP | Format/parse |
|-----|----------------|--------|---------|-------|-----------|---------|-------------|-----------|----------|-------|----|--------------|
| haiku-std | haiku / low | standard | REVISE ✅ | ✅B | ✅B | ✅B | reasoning | ✅B | n/a | ✗ | none | ✅ |
| son-std | sonnet / med | standard | REVISE ✅ | ✅B | ✅B | ✅B | ⚠N | ✅B | ✗ (no block) | ✗ | none | ✅ |
| son-adv | sonnet / med | adversarial | REVISE ✅ | ✅B | ✅B | ⚠N | folded | ✅B | n/a | ✗ | none | ✅ |
| son-dom | sonnet / med | domain 2-pass | REVISE ✅ | ✅B | ✅B | ✅/N | ⚠ | ✅B | ✅B (Pass B) | ✅B (Pass B) | none | ✅ |
| cdx-std | gpt-5.4-mini / low | standard | REVISE ✅ | ✗ | ✅B | ✅B | folded | ✅B | n/a | ✗ | Task6 (MED) | ✅ |

Validated (no change): verdict 5/5; format+parse 5/5 (incl. bold tags + two-pass);
**domain-context two-pass works** (controlled std-vs-dom catches B-DOMAIN); adversarial
elevates the high-cost race as designed.

RED signals: **N-OBS missed by every non-domain run** (incl. adversarial, whose focus
list names observability); executability-seam severity oscillates blocking↔non-blocking.

## Micro-tests — 5 reps/arm

| Candidate | Control | Treatment | Decision |
|-----------|---------|-----------|----------|
| **L-OBS** observability in Execution-risk lens | 1/5 flag | **5/5** flag | **SHIP** |
| **L-SEV** seam-severity heuristic | undef 3/4, 1 miss | undef **5/5** + recall | **SHIP (marginal)** |
| **F4** worked example | mean 10.6 sd 0.49 | mean 10.6 sd 0.49 | **REJECT** — no effect, pure weight |
| **F2** Pass-B positive reframe (audit HIGH) | **5/5** challenge bad criterion | 5/5 | **REJECT** — control already passes |
| **F3/F8** adversarial reframe (audit HIGH) | **5/5** attack the hedge | 5/5 | **REJECT** — control already passes |

Shipped to `references/output-format.md`: L-OBS clause + L-SEV heuristic (wording
byte-identical to the validated `treat` arms). Clarity edits to `SKILL.md` (agy dedup,
STOP rationale, domain predicate, per-round-ID hoist) — host-side, not reviewer-behavioral.

## Reproduce

```bash
cd peer-plan-review/evals
python3 run_reviews.py baseline  && python3 score.py baseline
python3 run_reviews.py microtest && python3 score.py microtest
```
