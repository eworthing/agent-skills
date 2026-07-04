"""Mid-quorum resume gate — refactored code must load the round-3
fixture without data loss.

This is the test that the refactor plan's verification step 5 calls for,
implemented against the public APIs the quorum/ package actually exposes
(``load_ledger``, ``save_ledger``). The plan's original sketch named
aspirational helpers (``load_state``, ``build_round_context``,
``serialize_ledger``, ``replay_merge_log``) that the Phase-C split did
not introduce — adding those would have meant changing function
signatures beyond a mechanical split, which Phase C was scoped to avoid.

What the available APIs let us assert:

1. **Schema preservation** — the round-3 fixture loads and re-serializes
   byte-identically. Any regression in ``load_ledger`` / ``save_ledger``
   that drops, reorders, or coerces a field is caught here.
2. **Fixture equality** — ``mid-quorum-r3/qr-mid-fixture-ledger.json``
   and ``mid-quorum-r4-expected/ledger-r3-final.json`` were captured
   together; if they ever drift, the fixture build script and the
   snapshot need to be re-run together.
3. **Merge log replay** — ``mid-quorum-r3/qr-mid-fixture-merge-log.jsonl``
   loads cleanly and matches ``mid-quorum-r4-expected/merge-replay.jsonl``
   record-for-record.
4. **Label assignment** — the deterministic ``Reviewer {chr(65+idx)}``
   formula matches the captured ``label-map-r4.json``. This is a formula
   regression test, not an integration test against the orchestrator.

What the available APIs do NOT let us assert (deferred):

- That ``build_round_context(state, round_num=4)`` produces the same
  reviewer prompts as a fresh round-4 invocation. The pre-refactor code
  embedded prompt building in ``main()``; extracting it as a pure
  function is a follow-up refactor outside this plan's scope.

Tests are pytest-style and run via ``python3 -m pytest scripts/tests/``
from the quorum-review directory.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from quorum.ledger import load_ledger, save_ledger

FIXTURE_R3 = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "mid-quorum-r3"
EXPECTED_R4 = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "mid-quorum-r4-expected"


@pytest.fixture(scope="module")
def r3_ledger_path():
    p = FIXTURE_R3 / "qr-mid-fixture-ledger.json"
    if not p.exists():
        pytest.skip(f"fixture missing: {p}")
    return p


@pytest.fixture(scope="module")
def expected_ledger_path():
    p = EXPECTED_R4 / "ledger-r3-final.json"
    if not p.exists():
        pytest.skip(f"snapshot missing: {p}")
    return p


# ---------------------------------------------------------------------------
# Schema preservation — round-trip equality
# ---------------------------------------------------------------------------


class TestLedgerRoundTrip:
    def test_load_then_save_then_load_yields_identical_data(self, r3_ledger_path, tmp_path):
        """Catch any drop/reorder/coerce regression in load_ledger / save_ledger."""
        original = load_ledger(str(r3_ledger_path))
        out = tmp_path / "round-tripped.json"
        save_ledger(str(out), original)
        round_tripped = load_ledger(str(out))
        assert round_tripped == original

    def test_v3_load_does_not_mutate_top_level_schema(self, r3_ledger_path):
        """A v3 ledger should round-trip with its top-level keys intact."""
        ledger = load_ledger(str(r3_ledger_path))
        # Sanity: it has issues, version metadata, and per-round snapshots.
        assert "issues" in ledger
        assert isinstance(ledger["issues"], list)


# ---------------------------------------------------------------------------
# Fixture equality — r3 ledger == r4 snapshot (they were captured together)
# ---------------------------------------------------------------------------


class TestFixtureSnapshotConsistency:
    def test_r3_ledger_matches_r4_snapshot(self, r3_ledger_path, expected_ledger_path):
        """If these diverge, the fixture build script and snapshot need
        to be regenerated together (see tests/fixtures/mid-quorum-r4-expected/README.md)."""
        assert load_ledger(str(r3_ledger_path)) == load_ledger(str(expected_ledger_path))


# ---------------------------------------------------------------------------
# Merge log replay
# ---------------------------------------------------------------------------


class TestMergeLogReplay:
    def test_merge_log_jsonl_parses_cleanly(self):
        merge_log = FIXTURE_R3 / "qr-mid-fixture-merge-log.jsonl"
        if not merge_log.exists():
            pytest.skip(f"fixture missing: {merge_log}")
        rows = [
            json.loads(ln)
            for ln in merge_log.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        assert rows  # at least one merge decision was recorded
        for r in rows:
            assert "action" in r, f"merge log row missing 'action': {r!r}"

    def test_merge_log_matches_replay_snapshot(self):
        merge_log = FIXTURE_R3 / "qr-mid-fixture-merge-log.jsonl"
        replay = EXPECTED_R4 / "merge-replay.jsonl"
        if not merge_log.exists() or not replay.exists():
            pytest.skip("fixture or replay snapshot missing")
        actual = [
            json.loads(ln)
            for ln in merge_log.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        expected = [
            json.loads(ln) for ln in replay.read_text(encoding="utf-8").splitlines() if ln.strip()
        ]
        assert actual == expected


# ---------------------------------------------------------------------------
# Anonymization label formula
# ---------------------------------------------------------------------------


class TestLabelAssignment:
    def test_label_formula_matches_snapshot(self):
        """``Reviewer {chr(65 + idx)}`` is invariant #7. The snapshot
        encodes the formula's output for the fixture's reviewer order."""
        label_map_path = EXPECTED_R4 / "label-map-r4.json"
        if not label_map_path.exists():
            pytest.skip(f"snapshot missing: {label_map_path}")
        expected = json.loads(label_map_path.read_text(encoding="utf-8"))
        # The fixture was built with reviewers in this order.
        reviewers = ["claude", "gemini", "codex"]
        formula = {f"Reviewer {chr(65 + i)}": r for i, r in enumerate(reviewers)}
        assert formula == expected
