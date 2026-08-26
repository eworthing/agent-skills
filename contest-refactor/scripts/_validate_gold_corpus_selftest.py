#!/usr/bin/env python3
"""Self-test for validate-gold-corpus.py.

Subprocesses the SHIPPED validator against synthetic packs built fresh in a
tempdir -- never a reimplementation, same rule as _validate_gates_selftest.py.
No real corpus exists yet under evals/gold-corpus/, so every fixture here is
constructed on the fly: a minimal valid "baseline" pack (red + gold variants,
variant_roles tagging both, everything else empty/absent) that every case
either uses unmodified (restraint: must stay silent) or mutates one way
(RED: must fire exactly the rule under test).

Run: python3 scripts/_validate_gold_corpus_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
VALIDATOR = SCRIPTS / "validate-gold-corpus.py"

SHA_A = "a" * 40
SHA_B = "b" * 40
PR_NUMBER = 424242


def _baseline_manifest() -> dict:
    """A minimal, fully-valid provenance.json body (red + gold only)."""
    return {
        "source_repo": "example/fake-repo",
        "source_pr": PR_NUMBER,
        "base_sha": SHA_A,
        "accepted_sha": SHA_B,
        "accepted_state": "merged",
        "gold_confidence": "high",
        "prompt_exposure": "provenance_hidden",
        "fixture_role": "example",
        "variant_roles": {"red": "red", "gold": "green"},
        "expected_judgment": "example",
        "candidate_visible_files": [],
        "grader_only_files": ["provenance.json"],
        "must_find": [],
        "must_not_find": [],
        "allowed_findings": [],
        "residual_findings": [],
        "must_find_if_present": [],
        "hidden_oracles": [],
        "contamination": {"renamed": [], "minimized_from": None, "why": None},
    }


def _write_pack(root: Path, pack_name: str, manifest: dict, extra_dirs: list[str] = ()) -> Path:
    """Build one pack dir: variant dirs from variant_roles + extra_dirs, then provenance.json."""
    pack_dir = root / pack_name
    pack_dir.mkdir(parents=True, exist_ok=True)
    for variant in manifest.get("variant_roles", {}):
        (pack_dir / variant).mkdir(parents=True, exist_ok=True)
    for extra in extra_dirs:
        (pack_dir / extra).mkdir(parents=True, exist_ok=True)
    (pack_dir / "provenance.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return pack_dir


def _run(corpus_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(corpus_dir)],
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    failures: list[str] = []

    def expect(label: str, cond: bool, detail: str) -> None:
        if not cond:
            failures.append(f"{label}: {detail}")

    with tempfile.TemporaryDirectory(prefix="gold-corpus-selftest-") as td:
        root = Path(td)

        # --- absent / empty / bad-path corpus (shippable ahead of the corpus) ---

        absent = root / "does-not-exist"
        r = _run(absent)
        expect(
            "absent-corpus", r.returncode == 0, f"expected exit 0, got {r.returncode}: {r.stderr}"
        )
        expect(
            "absent-corpus", "no packs found" in r.stdout, f"expected 'no packs found': {r.stdout}"
        )

        empty_corpus = root / "empty-corpus"
        empty_corpus.mkdir()
        r = _run(empty_corpus)
        expect(
            "empty-corpus", r.returncode == 0, f"expected exit 0, got {r.returncode}: {r.stderr}"
        )
        expect(
            "empty-corpus", "no packs found" in r.stdout, f"expected 'no packs found': {r.stdout}"
        )

        bad_path = root / "a-plain-file"
        bad_path.write_text("not a directory", encoding="utf-8")
        r = _run(bad_path)
        expect("bad-path", r.returncode == 2, f"expected exit 2, got {r.returncode}: {r.stderr}")

        # --- clean baseline: fully valid pack must pass silently ---

        clean_root = root / "clean"
        _write_pack(clean_root, "pack", _baseline_manifest())
        r = _run(clean_root)
        expect(
            "clean-baseline", r.returncode == 0, f"expected exit 0, got {r.returncode}: {r.stderr}"
        )

        # --- missing-manifest: pack dir with no provenance.json ---

        no_manifest_root = root / "no-manifest"
        (no_manifest_root / "pack").mkdir(parents=True)
        r = _run(no_manifest_root)
        expect("missing-manifest", r.returncode == 1, f"expected exit 1, got {r.returncode}")
        expect("missing-manifest", "[missing-manifest]" in r.stderr, r.stderr)

        # --- manifest-parse: invalid JSON ---

        bad_json_root = root / "bad-json"
        pack_dir = bad_json_root / "pack"
        pack_dir.mkdir(parents=True)
        (pack_dir / "provenance.json").write_text("{not valid json", encoding="utf-8")
        r = _run(bad_json_root)
        expect("manifest-parse", r.returncode == 1, f"expected exit 1, got {r.returncode}")
        expect("manifest-parse", "[manifest-parse]" in r.stderr, r.stderr)

        # --- missing-variant-roles: required field absent ---

        no_roles_root = root / "no-roles"
        m = _baseline_manifest()
        del m["variant_roles"]
        _write_pack(no_roles_root, "pack", m, extra_dirs=["red", "gold"])
        r = _run(no_roles_root)
        expect("missing-variant-roles", r.returncode == 1, f"expected exit 1, got {r.returncode}")
        expect("missing-variant-roles", "[missing-variant-roles]" in r.stderr, r.stderr)

        # --- unknown-variant-role: closed-set violation ---

        bad_role_root = root / "bad-role"
        m = _baseline_manifest()
        m["variant_roles"] = {"red": "not_a_real_role", "gold": "green"}
        _write_pack(bad_role_root, "pack", m)
        r = _run(bad_role_root)
        expect("unknown-variant-role", r.returncode == 1, f"expected exit 1, got {r.returncode}")
        expect("unknown-variant-role", "[unknown-variant-role]" in r.stderr, r.stderr)

        # --- variant-role-dir-missing: role names a directory that doesn't exist ---

        phantom_root = root / "phantom-dir"
        m = _baseline_manifest()
        m["variant_roles"] = {"red": "red", "gold": "green", "phantom": "mutant"}
        _write_pack(phantom_root, "pack", m)  # writer creates a dir per variant_roles key...
        shutil.rmtree(phantom_root / "pack" / "phantom")  # ...remove it to force the real gap
        r = _run(phantom_root)
        expect(
            "variant-role-dir-missing", r.returncode == 1, f"expected exit 1, got {r.returncode}"
        )
        expect("variant-role-dir-missing", "[variant-role-dir-missing]" in r.stderr, r.stderr)

        # --- missing-red-or-green (check 1) ---

        no_red_root = root / "no-red"
        m = _baseline_manifest()
        m["variant_roles"] = {"gold": "green"}
        _write_pack(no_red_root, "pack", m)
        r = _run(no_red_root)
        expect("missing-red-or-green", r.returncode == 1, f"expected exit 1, got {r.returncode}")
        expect("missing-red-or-green", "[missing-red-or-green]" in r.stderr, r.stderr)

        # restraint: alternate_green counts as green-or-accepted, no bare "green" needed
        alt_green_root = root / "alt-green"
        m = _baseline_manifest()
        m["variant_roles"] = {"red": "red", "alt": "alternate_green"}
        _write_pack(alt_green_root, "pack", m)
        r = _run(alt_green_root)
        expect(
            "alternate-green-restraint",
            r.returncode == 0,
            f"alternate_green should satisfy check 1, got {r.returncode}: {r.stderr}",
        )

        # --- near-miss-missing-must-not-find (check 2) ---

        near_miss_bad_root = root / "near-miss-bad"
        m = _baseline_manifest()
        m["variant_roles"] = {"red": "red", "gold": "green", "nm": "near_miss"}
        m["must_not_find"] = []
        _write_pack(near_miss_bad_root, "pack", m)
        r = _run(near_miss_bad_root)
        expect(
            "near-miss-missing-must-not-find",
            r.returncode == 1,
            f"expected exit 1, got {r.returncode}",
        )
        expect(
            "near-miss-missing-must-not-find",
            "[near-miss-missing-must-not-find]" in r.stderr,
            r.stderr,
        )

        # restraint: same shape but must_not_find populated -> silent on this rule
        near_miss_good_root = root / "near-miss-good"
        m = _baseline_manifest()
        m["variant_roles"] = {"red": "red", "gold": "green", "nm": "near_miss"}
        m["must_not_find"] = ["scanner-must-not-praise-the-near-miss"]
        _write_pack(near_miss_good_root, "pack", m)
        r = _run(near_miss_good_root)
        expect(
            "near-miss-restraint",
            r.returncode == 0,
            f"expected exit 0, got {r.returncode}: {r.stderr}",
        )

        # --- legacy-alias (check 3) ---

        legacy_notice_root = root / "legacy-notice"
        m = _baseline_manifest()
        m["must_notice"] = ["something"]
        _write_pack(legacy_notice_root, "pack", m)
        r = _run(legacy_notice_root)
        expect("legacy-alias-notice", r.returncode == 1, f"expected exit 1, got {r.returncode}")
        expect(
            "legacy-alias-notice",
            "Use must_find, not must_notice." in r.stderr,
            r.stderr,
        )

        legacy_claim_root = root / "legacy-claim"
        m = _baseline_manifest()
        m["must_not_claim"] = ["something"]
        _write_pack(legacy_claim_root, "pack", m)
        r = _run(legacy_claim_root)
        expect("legacy-alias-claim", r.returncode == 1, f"expected exit 1, got {r.returncode}")
        expect(
            "legacy-alias-claim",
            "Use must_not_find, not must_not_claim." in r.stderr,
            r.stderr,
        )

        # --- dangling-variant-reference + variant-listed-both-sides (check 4) ---

        dangling_root = root / "dangling"
        m = _baseline_manifest()
        m["must_find_if_present"] = [
            {
                "evidence_id": "e1",
                "applies_to_variants": ["ghost"],
                "required_finding": "x",
                "not_required_in": [],
            }
        ]
        _write_pack(dangling_root, "pack", m)
        r = _run(dangling_root)
        expect(
            "dangling-variant-reference", r.returncode == 1, f"expected exit 1, got {r.returncode}"
        )
        expect(
            "dangling-variant-reference",
            "[dangling-variant-reference]" in r.stderr,
            r.stderr,
        )

        both_sides_root = root / "both-sides"
        m = _baseline_manifest()
        m["must_find_if_present"] = [
            {
                "evidence_id": "e1",
                "applies_to_variants": ["gold"],
                "required_finding": "x",
                "not_required_in": ["gold"],
            }
        ]
        _write_pack(both_sides_root, "pack", m)
        r = _run(both_sides_root)
        expect(
            "variant-listed-both-sides", r.returncode == 1, f"expected exit 1, got {r.returncode}"
        )
        expect(
            "variant-listed-both-sides",
            "[variant-listed-both-sides]" in r.stderr,
            r.stderr,
        )
        expect(
            "variant-listed-both-sides-no-false-dangle",
            "[dangling-variant-reference]" not in r.stderr,
            f"gold exists on disk; must not also report dangling: {r.stderr}",
        )

        # restraint: real, non-overlapping variant references -> silent
        check4_good_root = root / "check4-good"
        m = _baseline_manifest()
        m["must_find_if_present"] = [
            {
                "evidence_id": "e1",
                "applies_to_variants": ["gold"],
                "required_finding": "x",
                "not_required_in": ["red"],
            }
        ]
        _write_pack(check4_good_root, "pack", m)
        r = _run(check4_good_root)
        expect(
            "check4-restraint",
            r.returncode == 0,
            f"expected exit 0, got {r.returncode}: {r.stderr}",
        )

        # --- mutant-missing-oracle (check 5) ---

        mutant_bad_root = root / "mutant-bad"
        m = _baseline_manifest()
        m["variant_roles"] = {"red": "red", "gold": "green", "mut": "mutant"}
        m["hidden_oracles"] = []
        _write_pack(mutant_bad_root, "pack", m)
        r = _run(mutant_bad_root)
        expect("mutant-missing-oracle", r.returncode == 1, f"expected exit 1, got {r.returncode}")
        expect("mutant-missing-oracle", "[mutant-missing-oracle]" in r.stderr, r.stderr)

        mutant_good_root = root / "mutant-good"
        m = _baseline_manifest()
        m["variant_roles"] = {"red": "red", "gold": "green", "mut": "mutant"}
        m["hidden_oracles"] = [{"name": "trap", "variant_expected_to_fail": "mut"}]
        _write_pack(mutant_good_root, "pack", m)
        r = _run(mutant_good_root)
        expect(
            "mutant-restraint",
            r.returncode == 0,
            f"expected exit 0, got {r.returncode}: {r.stderr}",
        )

        # --- provenance-visible-without-label (check 6) ---

        prov_visible_root = root / "prov-visible"
        m = _baseline_manifest()
        m["candidate_visible_files"] = ["provenance.json"]
        m["prompt_exposure"] = "provenance_hidden"
        _write_pack(prov_visible_root, "pack", m)
        r = _run(prov_visible_root)
        expect(
            "provenance-visible-without-label",
            r.returncode == 1,
            f"expected exit 1, got {r.returncode}",
        )
        expect(
            "provenance-visible-without-label",
            "[provenance-visible-without-label]" in r.stderr,
            r.stderr,
        )

        prov_labeled_root = root / "prov-labeled"
        m = _baseline_manifest()
        m["candidate_visible_files"] = ["provenance.json"]
        m["prompt_exposure"] = "provenance_labeled"
        _write_pack(prov_labeled_root, "pack", m)
        r = _run(prov_labeled_root)
        expect(
            "provenance-labeled-restraint",
            r.returncode == 0,
            f"expected exit 0, got {r.returncode}: {r.stderr}",
        )

        # --- hidden-mode-leak (check 7): PR number, commit SHA, symbol name ---

        leak_pr_root = root / "leak-pr"
        m = _baseline_manifest()
        m["candidate_visible_files"] = ["fixture.txt"]
        pack_dir = _write_pack(leak_pr_root, "pack", m)
        (pack_dir / "fixture.txt").write_text(f"see #{PR_NUMBER} for context", encoding="utf-8")
        r = _run(leak_pr_root)
        expect("leak-pr", r.returncode == 1, f"expected exit 1, got {r.returncode}")
        expect("leak-pr", "[hidden-mode-leak]" in r.stderr and "pr-number" in r.stderr, r.stderr)

        leak_sha_root = root / "leak-sha"
        m = _baseline_manifest()
        m["candidate_visible_files"] = ["fixture.txt"]
        pack_dir = _write_pack(leak_sha_root, "pack", m)
        (pack_dir / "fixture.txt").write_text(f"base commit {SHA_A}", encoding="utf-8")
        r = _run(leak_sha_root)
        expect("leak-sha", r.returncode == 1, f"expected exit 1, got {r.returncode}")
        expect("leak-sha", "[hidden-mode-leak]" in r.stderr and "commit-sha" in r.stderr, r.stderr)

        leak_symbol_root = root / "leak-symbol"
        m = _baseline_manifest()
        m["candidate_visible_files"] = ["fixture.txt"]
        m["contamination"] = {
            "renamed": ["OriginalUpstreamSymbol"],
            "minimized_from": None,
            "why": None,
        }
        pack_dir = _write_pack(leak_symbol_root, "pack", m)
        (pack_dir / "fixture.txt").write_text("func OriginalUpstreamSymbol() { }", encoding="utf-8")
        r = _run(leak_symbol_root)
        expect("leak-symbol", r.returncode == 1, f"expected exit 1, got {r.returncode}")
        expect(
            "leak-symbol", "[hidden-mode-leak]" in r.stderr and "symbol-name" in r.stderr, r.stderr
        )

        # restraint: same leaky content, but sanitized text -> silent
        leak_clean_root = root / "leak-clean"
        m = _baseline_manifest()
        m["candidate_visible_files"] = ["fixture.txt"]
        pack_dir = _write_pack(leak_clean_root, "pack", m)
        (pack_dir / "fixture.txt").write_text(
            "renamed to FixtureThing, no leaked references here", encoding="utf-8"
        )
        r = _run(leak_clean_root)
        expect(
            "leak-restraint-clean-text",
            r.returncode == 0,
            f"expected exit 0, got {r.returncode}: {r.stderr}",
        )

        # restraint: leaky content, but provenance_labeled mode -> check 7 doesn't bind
        leak_labeled_root = root / "leak-labeled-mode"
        m = _baseline_manifest()
        m["candidate_visible_files"] = ["fixture.txt"]
        m["prompt_exposure"] = "provenance_labeled"
        pack_dir = _write_pack(leak_labeled_root, "pack", m)
        (pack_dir / "fixture.txt").write_text(f"see #{PR_NUMBER} for context", encoding="utf-8")
        r = _run(leak_labeled_root)
        expect(
            "leak-restraint-labeled-mode",
            r.returncode == 0,
            f"labeled mode must not trigger the hidden-mode leak check, got "
            f"{r.returncode}: {r.stderr}",
        )

        # --- role-leak (check 8): a fixture must not name its own concealed role ---

        # RED: the variant's own directory name printed inside a candidate-visible file.
        # This is the exact shape found in all four packs built before the check existed.
        role_dir_root = root / "role-leak-dirname"
        m = _baseline_manifest()
        m["variant_roles"] = {"red": "red", "gold": "green", "sneaky-plant": "mutant"}
        m["hidden_oracles"] = [{"name": "o", "variant_expected_to_fail": "sneaky-plant"}]
        m["candidate_visible_files"] = ["sneaky-plant/test_thing.py"]
        pack_dir = _write_pack(role_dir_root, "pack", m)
        (pack_dir / "sneaky-plant" / "test_thing.py").write_text(
            'print("OK: sneaky-plant test_thing.py")', encoding="utf-8"
        )
        r = _run(role_dir_root)
        expect("role-leak-dirname", r.returncode == 1, f"expected exit 1, got {r.returncode}")
        expect("role-leak-dirname", "[role-leak]" in r.stderr, r.stderr)

        # RED: the bare role token, even when the directory name is innocuous.
        role_token_root = root / "role-leak-token"
        m = _baseline_manifest()
        m["variant_roles"] = {"red": "red", "gold": "green", "variant-c": "near_miss"}
        m["must_not_find"] = ["something"]
        m["candidate_visible_files"] = ["variant-c/notes.md"]
        pack_dir = _write_pack(role_token_root, "pack", m)
        (pack_dir / "variant-c" / "notes.md").write_text(
            "this is the near-miss arm", encoding="utf-8"
        )
        r = _run(role_token_root)
        expect("role-leak-token", r.returncode == 1, f"expected exit 1, got {r.returncode}")
        expect("role-leak-token", "[role-leak]" in r.stderr, r.stderr)

        # restraint: a red/green variant naming itself is NOT a leak -- "red" and "green"
        # are ordinary words and matching them would false-positive on real fixtures.
        role_clean_root = root / "role-leak-clean"
        m = _baseline_manifest()
        m["candidate_visible_files"] = ["red/test_thing.py"]
        pack_dir = _write_pack(role_clean_root, "pack", m)
        (pack_dir / "red" / "test_thing.py").write_text(
            'print("OK: red test_thing.py")  # a red pepper is green when unripe',
            encoding="utf-8",
        )
        r = _run(role_clean_root)
        expect(
            "role-leak-restraint-plain-words",
            r.returncode == 0,
            f"expected exit 0, got {r.returncode}: {r.stderr}",
        )

        # restraint: labeled mode discloses provenance anyway, so check 8 must not bind.
        role_labeled_root = root / "role-leak-labeled"
        m = _baseline_manifest()
        m["variant_roles"] = {"red": "red", "gold": "green", "sneaky-plant": "mutant"}
        m["hidden_oracles"] = [{"name": "o", "variant_expected_to_fail": "sneaky-plant"}]
        m["prompt_exposure"] = "provenance_labeled"
        m["candidate_visible_files"] = ["sneaky-plant/test_thing.py", "provenance.json"]
        pack_dir = _write_pack(role_labeled_root, "pack", m)
        (pack_dir / "sneaky-plant" / "test_thing.py").write_text(
            'print("OK: sneaky-plant test_thing.py")', encoding="utf-8"
        )
        r = _run(role_labeled_root)
        expect(
            "role-leak-restraint-labeled-mode",
            r.returncode == 0,
            f"labeled mode must not trigger the role-leak check, got {r.returncode}: {r.stderr}",
        )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        print(f"\n{len(failures)} failure(s)")
        return 1
    print(
        "OK: validate-gold-corpus.py checks fire on synthetic RED packs and stay silent on restraint packs"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
