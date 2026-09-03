#!/usr/bin/env python3
"""Selftest for audit_dead_surface.py (DD-16, W2). Run directly; exit 0 = pass.

Guards the properties the aid's usefulness rests on:
  - one dead fixture per row kind (enum_case, protocol_requirement, declaration);
  - one silent fixture per kind (construction elsewhere, a real call inside a
    conformance file, a same-file read) proving the exclusion rules work, not
    just the flagging;
  - test_only / preview_only classification;
  - every --access mode, including private/fileprivate file-scoping;
  - a shadowed name across two unrelated types is NEVER flagged (accepted
    false negative, spec'd restraint -- false positives are the enemy);
  - envelope shape, exit codes, `absent` on an empty root, `--scope` narrowing.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_dead_surface as A


def _repo(files: dict[str, str]) -> Path:
    d = Path(tempfile.mkdtemp(prefix="dead-surface-selftest-"))
    for rel, body in files.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return d


def _rows_by_name(doc: dict) -> dict[str, dict]:
    return {r["name"]: r for r in doc["rows"]}


def test_dead_enum_case() -> None:
    d = _repo(
        {
            "Values/Sample.swift": (
                "public enum Sample: Sendable {\n"
                "    case alive\n"
                "    case deadCase\n"
                "}\n\n"
                "public func use(_ s: Sample) -> String {\n"
                "    switch s {\n"
                "    case .alive:\n"
                '        return "alive"\n'
                "    case .deadCase:\n"
                '        return "dead"\n'
                "    }\n"
                "}\n"
            )
        }
    )
    doc = A.audit(d, None, "all")
    rows = _rows_by_name(doc)
    assert "deadCase" in rows, rows
    assert rows["deadCase"]["kind"] == "enum_case"
    assert rows["deadCase"]["status"] == "dead"
    assert rows["deadCase"]["references_production"] == 0, rows["deadCase"]
    # `.alive` is also only ever pattern-matched, so it is dead too -- both
    # switch arms are pattern positions, neither is a construction site.
    assert rows["alive"]["status"] == "dead"


def test_enum_case_constructed_elsewhere_silent() -> None:
    d = _repo(
        {
            "Values/Sample.swift": ("public enum Sample: Sendable {\n    case constructed\n}\n"),
            "Other/Builder.swift": ("public func build() -> Sample {\n    .constructed\n}\n"),
        }
    )
    doc = A.audit(d, None, "all")
    rows = _rows_by_name(doc)
    assert "constructed" not in rows, "real construction site must silence the case"


def test_dead_protocol_requirement() -> None:
    d = _repo(
        {"Ports/Foo.swift": "public protocol Foo: Sendable {\n    func bar() async -> Int\n}\n"}
    )
    doc = A.audit(d, None, "all")
    rows = _rows_by_name(doc)
    assert rows["bar"]["kind"] == "protocol_requirement"
    assert rows["bar"]["status"] == "dead"


def test_protocol_requirement_conformance_call_silences() -> None:
    d = _repo(
        {
            "Ports/Foo.swift": "public protocol Foo: Sendable {\n    func bar() async -> Int\n}\n",
            "Impl/RealFoo.swift": (
                "public struct RealFoo: Foo {\n"
                "    public func bar() async -> Int { 1 }\n"
                "    public func helper() async -> Int {\n"
                "        await bar()\n"
                "    }\n"
                "}\n"
            ),
        }
    )
    doc = A.audit(d, None, "all")
    rows = _rows_by_name(doc)
    # the impl's own `func bar()` signature line is a declaration occurrence,
    # excluded; the call inside `helper()` is a real use and must count.
    assert "bar" not in rows, "a real call inside the conformance file must silence the requirement"


def test_dead_declaration() -> None:
    d = _repo(
        {
            "Values/Widget.swift": (
                'public struct Widget: Sendable {\n    public var deadProp: String { "x" }\n}\n'
            )
        }
    )
    doc = A.audit(d, None, "all")
    rows = _rows_by_name(doc)
    assert rows["deadProp"]["kind"] == "declaration"
    assert rows["deadProp"]["status"] == "dead"


def test_declaration_read_in_own_file_silent() -> None:
    d = _repo(
        {
            "Values/Widget.swift": (
                "public struct Widget: Sendable {\n"
                '    public var liveProp: String { "x" }\n'
                "    public func show() -> String {\n"
                "        liveProp\n"
                "    }\n"
                "}\n"
            )
        }
    )
    doc = A.audit(d, None, "all")
    rows = _rows_by_name(doc)
    assert "liveProp" not in rows, "a read elsewhere in the same file must silence the member"


def test_test_only() -> None:
    d = _repo(
        {
            "Values/Thing.swift": (
                "public struct Thing: Sendable {\n"
                "    public var testOnlyProp: Int { 1 }\n"
                "    public init() {}\n"
                "}\n"
            ),
            "Tests/ThingTests.swift": (
                "import XCTest\n"
                "final class ThingTests: XCTestCase {\n"
                "    func testIt() {\n"
                "        let t = Thing()\n"
                "        _ = t.testOnlyProp\n"
                "    }\n"
                "}\n"
            ),
        }
    )
    doc = A.audit(d, None, "all")
    rows = _rows_by_name(doc)
    assert rows["testOnlyProp"]["status"] == "test_only", rows["testOnlyProp"]
    assert rows["testOnlyProp"]["references_production"] == 0
    assert rows["testOnlyProp"]["references_in_tests"] > 0
    assert doc["coverage"]["test_files_scanned"] >= 1


def test_preview_only() -> None:
    d = _repo(
        {
            "Values/Thing2.swift": (
                "public struct Thing2: Sendable {\n"
                "    public var previewOnlyProp: Int { 1 }\n"
                "    public init() {}\n"
                "}\n"
            ),
            "Views/ThingView.swift": (
                "import SwiftUI\n\n"
                "#Preview {\n"
                "    let t = Thing2()\n"
                '    return Text("\\(t.previewOnlyProp)")\n'
                "}\n"
            ),
        }
    )
    doc = A.audit(d, None, "all")
    rows = _rows_by_name(doc)
    assert rows["previewOnlyProp"]["status"] == "preview_only", rows["previewOnlyProp"]
    assert rows["previewOnlyProp"]["references_production"] == 0
    assert rows["previewOnlyProp"]["references_in_previews"] > 0


def test_access_modes_and_private_file_scoping() -> None:
    d = _repo(
        {
            "Values/Multi.swift": (
                "public struct Multi: Sendable {\n"
                "    public var pub: Int { 1 }\n"
                "    internal var intern: Int { 2 }\n"
                "    private var priv: Int { 3 }\n"
                "    fileprivate var filepriv: Int { 4 }\n"
                "}\n"
            ),
            # unrelated top-level `priv` elsewhere: must NOT silence Multi.priv,
            # since private is scoped to its declaring file only.
            "Other/Noise.swift": "public let priv = 42\n",
        }
    )
    pub_only = _rows_by_name(A.audit(d, None, "public"))
    assert set(pub_only) == {"pub"}, pub_only

    internal_mode = _rows_by_name(A.audit(d, None, "internal"))
    assert set(internal_mode) == {"pub", "intern"}, internal_mode

    all_mode = _rows_by_name(A.audit(d, None, "all"))
    assert set(all_mode) >= {"pub", "intern", "priv", "filepriv"}, all_mode
    assert all_mode["priv"]["status"] == "dead", (
        "private scoping must not be defeated by a cross-file shadow"
    )


def test_shadowed_name_never_flagged() -> None:
    d = _repo(
        {
            "Values/A.swift": "public struct A: Sendable {\n    public var shared: Int { 1 }\n}\n",
            "Values/B.swift": (
                "public struct B: Sendable {\n"
                "    public var shared: Int { 2 }\n"
                "    public func use() -> Int {\n"
                "        shared\n"
                "    }\n"
                "}\n"
            ),
        }
    )
    doc = A.audit(d, None, "all")
    a_shared = [r for r in doc["rows"] if r["type_name"] == "A" and r["name"] == "shared"]
    assert a_shared == [], "a name shadowed by a referenced member elsewhere must not be flagged"


def test_envelope_and_exit_codes() -> None:
    d = _repo(
        {"Values/X.swift": "public struct X: Sendable {\n    public var dead: Int { 1 }\n}\n"}
    )
    doc = A.audit(d, None, "all")
    assert doc["schema_version"] == 1
    assert doc["status"] == "ok"
    assert doc["promotion_allowed"] is False
    assert set(doc["coverage"]) == {
        "files_scanned",
        "files_failed",
        "test_files_scanned",
        "reference_files",
    }
    for row in doc["rows"]:
        assert set(row) == {
            "kind",
            "path",
            "line",
            "type_name",
            "name",
            "access",
            "references_production",
            "references_in_tests",
            "references_in_previews",
            "status",
        }, row

    assert A.main([str(d)]) == 0
    assert A.main(["/nonexistent/path/for/dead-surface-selftest"]) == 2
    assert A.main([str(d), "--scope", "NoSuchDir"]) == 2


def test_absent_on_empty_root() -> None:
    d = Path(tempfile.mkdtemp(prefix="dead-surface-empty-"))
    doc = A.audit(d, None, "all")
    assert doc["status"] == "absent"
    assert doc["rows"] == []


def test_scope_restricts_files_scanned() -> None:
    d = _repo(
        {
            "ModA/Values/X.swift": "public struct X: Sendable {\n    public var dead: Int { 1 }\n}\n",
            "ModB/Values/Y.swift": "public struct Y: Sendable {\n    public var dead2: Int { 1 }\n}\n",
        }
    )
    whole = A.audit(d, None, "all")
    scoped = A.audit(d, "ModA", "all")
    assert scoped["coverage"]["files_scanned"] < whole["coverage"]["files_scanned"]
    # --scope narrows declarations only -- the reference sweep is repo-wide either way.
    assert scoped["coverage"]["reference_files"] == whole["coverage"]["reference_files"]
    assert all(r["path"].startswith("ModA/") for r in scoped["rows"]), scoped["rows"]
    assert any(r["name"] == "dead" for r in scoped["rows"])
    assert not any(r["name"] == "dead2" for r in scoped["rows"])


def test_scope_reference_from_outside_scope_silences() -> None:
    # A declaration inside --scope, referenced only from a file OUTSIDE scope,
    # must NOT be flagged dead: the plan requires the reference sweep to cover
    # every production file regardless of --scope.
    d = _repo(
        {
            "ModA/Values/Widget.swift": (
                "public struct Widget: Sendable {\n    public var crossScopeProp: Int { 1 }\n}\n"
            ),
            "ModB/Consumer.swift": (
                "public func use(_ w: Widget) -> Int {\n    w.crossScopeProp\n}\n"
            ),
        }
    )
    scoped = A.audit(d, "ModA", "all")
    assert not any(r["name"] == "crossScopeProp" for r in scoped["rows"]), (
        "a reference from outside --scope must still silence an in-scope declaration"
    )


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("audit_dead_surface selftest: OK")
