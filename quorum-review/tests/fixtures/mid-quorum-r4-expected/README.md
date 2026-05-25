# mid-quorum-r4-expected — Round 4 reference state

This directory contains the expected state for the Phase C mid-quorum resume gate.

## What's captured now

| File | Determinism | Source |
|---|---|---|
| `label-map-r4.json` | full (deterministic from reviewer index) | computed |
| `merge-replay.jsonl` | full (round-3 merge log replayed verbatim) | copied from fixture |
| `ledger-r3-final.json` | full (frozen state at end of round 3) | copied from fixture |

## What's deferred to Phase C

| File | Why deferred |
|---|---|
| `ledger-r4-prior.json` | Identical to `ledger-r3-final.json` after `load_state()` round-trip — the refactored `quorum.ledger.serialize_ledger` is the pure function that confirms this. |
| `prompts-r4.json` | Round-4 cross-critique prompts depend on the orchestrator's internal prompt-building functions. The pre-refactor code embeds these in `main()`. Phase C's pure functions (`build_round_context`) will produce the canonical snapshot once they exist. |

## How the resume gate uses these

`tests/test_mid_quorum_resume.py` (added in Phase C) does:

```python
state = load_state(FIXTURE)
ctx = build_round_context(state, round_num=4)
assert serialize_ledger(state.ledger) == json.load(open(EXPECTED / "ledger-r3-final.json"))
assert assign_labels(state.reviewers, state.quorum_id) == json.load(open(EXPECTED / "label-map-r4.json"))
assert replay_merge_log(FIXTURE / "...merge-log.jsonl") == [json.loads(ln) for ln in open(EXPECTED / "merge-replay.jsonl") if ln.strip()]
# prompts-r4.json captured during Phase C from refactored pure functions
assert ctx.reviewer_prompts == json.load(open(EXPECTED / "prompts-r4.json"))
```
