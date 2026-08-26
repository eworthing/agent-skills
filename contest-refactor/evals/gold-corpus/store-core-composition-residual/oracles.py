#!/usr/bin/env python3
"""Hidden oracle battery for store-core-composition-residual. Grader-only:
never shown to a candidate (listed in provenance.json's grader_only_files).

Same probe pattern as this corpus's other Swift packs: `oracle_probe.swift`
(grader-only) is copied to a scratch file literally named `main.swift`
(swiftc only allows top-level statements in a file with that exact name)
and compiled against each variant's own `workspace.swift` PLUS that
variant's own grader-only `probe_adapter.swift`, never against that
variant's own `main.swift`. The adapter exists because each variant's real
construction/scoping API differs in shape -- type-erased-root and
near-miss-collapse-back-to-erasure take a free-generic key path unconstrained
by any container type, the three composed variants pin the key path's root
to the container's own associated state type -- and reconciling that into
one call shape belongs in a grader-only file, not the candidate-visible
module (see this corpus's swiftnio-registration-id-representation pack for
why a shared, candidate-visible encode signature is itself a defect to
avoid).

Two of this pack's four checks need no compiled probe at all:
`key_path_root_type_checked` compiles a tiny grader-only snippet against a
variant's own workspace.swift with `swiftc -typecheck` and reads the exit
code, and `dead_declaration_unreferenced` is pure static text analysis over
each variant's own workspace.swift.

Runs four checks:

    key_path_root_type_checked -- Swift type errors are compile-time, so
                                 this is observed by attempting to compile
                                 a tiny snippet that scopes into an
                                 unrelated state type. type-erased-root and
                                 near-miss-collapse-back-to-erasure expose
                                 only a non-generic Workspace whose
                                 child(at:) infers its Root purely from
                                 whatever key path is passed, with no link
                                 to the type this workspace actually boxes
                                 -- an unrelated-state key path compiles
                                 without complaint. core-composition-with-
                                 dead-isolation, core-composition-clean,
                                 and mutant-scoped-writes-lost all pin
                                 child(_:at:)'s key path root to the
                                 container's own Node.State, so the same
                                 unrelated-state key path fails to compile
                                 -- there is no back door here to reason
                                 around, and the mutant keeps this property
                                 exactly (its defect is behavioral, not
                                 structural).
    dead_declaration_unreferenced -- counts occurrences of the isolation
                                 marker's name (QuietQueue) in each
                                 variant's own workspace.swift. A count of
                                 exactly 1 means the marker is declared and
                                 referenced nowhere else -- true only for
                                 core-composition-with-dead-isolation. A
                                 count of 0 (every other variant) means the
                                 marker was never introduced there at all,
                                 which is the correct, clean state for
                                 core-composition-clean specifically: this
                                 is a real observed fact from a source
                                 scan, not an assertion, and it is what
                                 lets a reviewer who hallucinates a residual
                                 in core-composition-clean be checked
                                 against ground truth.
    scoped_write_reaches_parent -- THE DISCRIMINATOR between the composed
                                 variants and the mutant, which are
                                 structurally identical everywhere else:
                                 scope from a root into a child panel,
                                 write a new value through the child, and
                                 check whether the ROOT reflects it. True
                                 for every variant except mutant-scoped-
                                 writes-lost, whose child(_:at:) captures
                                 the child's state into a local variable at
                                 scoping time and routes writes there
                                 instead of back through the key path into
                                 the parent -- the write is not rejected,
                                 not lost with an error, simply never
                                 delivered to the root.
    scoped_child_initial_matches_parent -- CONTROL: immediately after
                                 scoping, before any write, the child's
                                 value matches what the parent was
                                 constructed with, for every variant
                                 including the mutant (whose defect is
                                 confined to the write path -- the initial
                                 read is unaffected). Holds everywhere in
                                 this pack's correct design -- a baseline
                                 that would fail if this fixture itself
                                 were broken in a way that made the other
                                 three oracles' results meaningless.

Run: python3 oracles.py
Exit 0 iff every observed result matches its declared expectation.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PACK_DIR = Path(__file__).resolve().parent
MODULE_FILENAME = "workspace.swift"
ADAPTER_FILENAME = "probe_adapter.swift"

VARIANTS = [
    "type-erased-root",
    "core-composition-with-dead-isolation",
    "core-composition-clean",
    "near-miss-collapse-back-to-erasure",
    "mutant-scoped-writes-lost",
]

# The two variants whose scoping API takes a free-generic key path,
# unconstrained relative to any container type, versus the three whose
# scoping API pins the key path's root to the container's own associated
# state type. key_path_root_type_checked needs a different snippet for
# each shape -- see that function.
RAW_API_VARIANTS = {"type-erased-root", "near-miss-collapse-back-to-erasure"}
COMPOSED_API_VARIANTS = {
    "core-composition-with-dead-isolation",
    "core-composition-clean",
    "mutant-scoped-writes-lost",
}

DEAD_MARKER_NAME = "QuietQueue"

RAW_UNRELATED_KEYPATH_SNIPPET = """\
// Grader-only compile-fail probe (type-erased shape). child(at:)'s Root
// is a free generic parameter, inferred from the key path alone, with no
// link to what this workspace actually boxes -- this snippet is
// EXPECTED TO COMPILE.
struct UnrelatedState { var value: Int }
let root = Workspace(state: EditorState(title: "x", inspector: InspectorState(zoom: 1)))
_ = root.child(at: \\UnrelatedState.value)
"""

COMPOSED_UNRELATED_KEYPATH_SNIPPET = """\
// Grader-only compile-fail probe (composed shape). child(_:at:) requires
// a key path rooted in exactly Node.State (EditorState here) -- this
// snippet is EXPECTED TO FAIL TO COMPILE. The field is deliberately
// named differently from EditorState's own `inspector` field: an
// identically-named field on both types has, in practice, tripped an
// unrelated Swift compiler diagnostic-generation bug on the type
// mismatch below rather than producing a clean error.
struct UnrelatedState { var somethingElse: InspectorState }
let root = Workspace<EditorPanel>(state: EditorState(title: "x", inspector: InspectorState(zoom: 1)))
_ = root.child(InspectorPanel.self, at: \\UnrelatedState.somethingElse)
"""


def _swiftc(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["swiftc", *args], capture_output=True, text=True, check=False)


def _swiftc_or_raise(*args: str) -> None:
    result = _swiftc(*args)
    if result.returncode != 0:
        raise RuntimeError(f"swiftc failed: {' '.join(args)}\n{result.stdout}\n{result.stderr}")


def build_probe(variant: str, scratch_dir: Path) -> Path:
    """Compile `variant`'s workspace.swift and its own grader-only
    probe_adapter.swift against the grader-only probe (copied to scratch
    as main.swift). The adapter supplies the two uniform probe entry
    points this probe calls -- see oracle_probe.swift's header."""
    main_path = scratch_dir / "main.swift"
    shutil.copyfile(PACK_DIR / "oracle_probe.swift", main_path)
    binary_path = scratch_dir / f"probe_{variant}"
    _swiftc_or_raise(
        str(PACK_DIR / variant / MODULE_FILENAME),
        str(PACK_DIR / variant / ADAPTER_FILENAME),
        str(main_path),
        "-o",
        str(binary_path),
    )
    return binary_path


def run_probe_initial(binary: Path, title: str, zoom: int) -> int:
    result = subprocess.run(
        [str(binary), "initial", title, str(zoom)], capture_output=True, text=True, check=True
    )
    return int(result.stdout.strip())


def run_probe_writeback(binary: Path, title: str, zoom: int, new_zoom: int) -> int:
    result = subprocess.run(
        [str(binary), "writeback", title, str(zoom), str(new_zoom)],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(result.stdout.strip())


def key_path_root_type_checked(dirs: dict[str, Path]) -> dict[str, bool]:
    results = {}
    with tempfile.TemporaryDirectory(prefix="tca-repr-keypath-") as tmp:
        scratch_dir = Path(tmp)
        for variant, variant_dir in dirs.items():
            module_path = variant_dir / MODULE_FILENAME
            snippet = (
                RAW_UNRELATED_KEYPATH_SNIPPET
                if variant in RAW_API_VARIANTS
                else COMPOSED_UNRELATED_KEYPATH_SNIPPET
            )
            main_path = scratch_dir / "main.swift"
            main_path.write_text(snippet, encoding="utf-8")
            compiled = _swiftc("-typecheck", str(module_path), str(main_path)).returncode == 0
            results[variant] = not compiled
    return results


def dead_declaration_unreferenced(dirs: dict[str, Path]) -> dict[str, int]:
    results = {}
    for variant, variant_dir in dirs.items():
        source = (variant_dir / MODULE_FILENAME).read_text(encoding="utf-8")
        results[variant] = len(re.findall(rf"\b{DEAD_MARKER_NAME}\b", source))
    return results


def scoped_write_reaches_parent(binaries: dict[str, Path]) -> dict[str, bool]:
    results = {}
    for variant, binary in binaries.items():
        after = run_probe_writeback(binary, "Untitled", 1, 4)
        results[variant] = after == 4
    return results


def scoped_child_initial_matches_parent(binaries: dict[str, Path]) -> dict[str, bool]:
    results = {}
    for variant, binary in binaries.items():
        initial = run_probe_initial(binary, "Untitled", 7)
        results[variant] = initial == 7
    return results


def main() -> int:
    dirs = {variant: PACK_DIR / variant for variant in VARIANTS}

    with tempfile.TemporaryDirectory(prefix="tca-repr-oracles-") as tmp:
        scratch_dir = Path(tmp)
        binaries = {variant: build_probe(variant, scratch_dir) for variant in VARIANTS}

        type_checked_results = key_path_root_type_checked(dirs)
        dead_counts = dead_declaration_unreferenced(dirs)
        writeback_results = scoped_write_reaches_parent(binaries)
        control_results = scoped_child_initial_matches_parent(binaries)

    print("=== key_path_root_type_checked ===")
    for name, ok in type_checked_results.items():
        print(f"  {name}: {'rejected (root pinned)' if ok else 'COMPILED (root unchecked)'}")
    print("=== dead_declaration_unreferenced ===")
    for name, count in dead_counts.items():
        label = "declared, unreferenced" if count == 1 else "not present"
        print(f"  {name}: {count} occurrence(s) ({label})")
    print("=== scoped_write_reaches_parent ===")
    for name, ok in writeback_results.items():
        print(f"  {name}: {'reached parent' if ok else 'LOST'}")
    print("=== scoped_child_initial_matches_parent (control) ===")
    for name, ok in control_results.items():
        print(f"  {name}: {'matched' if ok else 'MISMATCH'}")

    failures: list[str] = []

    expected_type_checked = {
        "type-erased-root": False,
        "near-miss-collapse-back-to-erasure": False,
        "core-composition-with-dead-isolation": True,
        "core-composition-clean": True,
        "mutant-scoped-writes-lost": True,
    }
    for name, expected in expected_type_checked.items():
        if type_checked_results.get(name) != expected:
            failures.append(
                f"{name}: expected key_path_root_type_checked={expected}, "
                f"got {type_checked_results.get(name)}"
            )

    expected_dead_declared = {
        "type-erased-root": False,
        "core-composition-with-dead-isolation": True,
        "core-composition-clean": False,
        "near-miss-collapse-back-to-erasure": False,
        "mutant-scoped-writes-lost": False,
    }
    for name, expect_declared in expected_dead_declared.items():
        declared = dead_counts.get(name) == 1
        if declared != expect_declared:
            failures.append(
                f"{name}: expected dead_declaration_unreferenced (count==1)={expect_declared}, "
                f"got count={dead_counts.get(name)}"
            )

    expected_writeback = {
        "type-erased-root": True,
        "core-composition-with-dead-isolation": True,
        "core-composition-clean": True,
        "near-miss-collapse-back-to-erasure": True,
        "mutant-scoped-writes-lost": False,
    }
    for name, expected in expected_writeback.items():
        if writeback_results.get(name) != expected:
            failures.append(
                f"{name}: expected scoped_write_reaches_parent={expected}, "
                f"got {writeback_results.get(name)}"
            )

    for name in VARIANTS:
        if control_results.get(name) is not True:
            failures.append(
                f"{name}: scoped_child_initial_matches_parent must hold, "
                f"got {control_results.get(name)}"
            )

    if failures:
        print("\nFAIL:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nOK: observed matrix matches declared expectations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
