#!/usr/bin/env python3
"""
check_shim_contract.py — AST-based shim contract scanner.

Given a test file that imports symbols from a module being refactored into
a compatibility shim, this script enumerates every name the test file
references on the module — via imports, attribute access, mock patches,
or getattr — and verifies that the shim re-exports all of them.

Usage:
    check_shim_contract.py <test_file> <scripts_dir> [<module_name>]

The <module_name> defaults to "run_quorum" if omitted.

Exit codes:
    0  — shim contract satisfied; every referenced name is re-exported.
    1  — shim is missing one or more required names (list printed).
    2  — test file uses constructs incompatible with static analysis
         (`from <module> import *`, dynamic `getattr(<module>, name_var)`).
         Such constructs must be refactored before the shim can be
         validated.

Trust boundary (security review finding R2-B2)
----------------------------------------------
This script ``import_module`` the named module from ``scripts_dir``,
which executes its top-level code. The module is treated as TRUSTED —
the script is a developer-only tool intended to run on the maintainer's
own working tree or in CI where the source has already been reviewed.
Do NOT run it against an untrusted clone or a path you do not control.
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path


def collect_references(tree: ast.AST, module_name: str) -> tuple[set[str], list[str]]:
    """Walk an AST and collect (required_names, errors)."""
    required: set[str] = set()
    errors: list[str] = []

    for node in ast.walk(tree):
        # Case A: from <module> import a, b, c    (incl. multiline, aliases)
        if isinstance(node, ast.ImportFrom) and node.module == module_name:
            for alias in node.names:
                if alias.name == "*":
                    errors.append(
                        f"line {node.lineno}: `from {module_name} import *` blocks "
                        "shim contract analysis. Replace with explicit imports."
                    )
                else:
                    required.add(alias.name)

        # Case B: import <module>; then  <module>.X  (attribute access)
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == module_name
        ):
            required.add(node.attr)

        # Cases C+D+E: function calls — mock.patch("X.Y"), patch.object(M, "Y"), getattr(M, "Y")
        elif isinstance(node, ast.Call):
            # Case C: patch(...) or mock.patch("module.X") — string-target patches.
            is_patch_str = (isinstance(node.func, ast.Attribute) and node.func.attr == "patch") or (
                isinstance(node.func, ast.Name) and node.func.id == "patch"
            )
            if is_patch_str:
                for arg in node.args:
                    if (
                        isinstance(arg, ast.Constant)
                        and isinstance(arg.value, str)
                        and arg.value.startswith(f"{module_name}.")
                    ):
                        required.add(arg.value.split(".", 1)[1].split(".", 1)[0])

            # Case D: patch.object(M, "X") / mock.patch.object(M, "X")
            is_patch_object = (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "object"
                and (
                    (
                        isinstance(node.func.value, ast.Name)
                        and node.func.value.id in ("patch", "mock")
                    )
                    or (
                        isinstance(node.func.value, ast.Attribute)
                        and node.func.value.attr == "patch"
                    )
                )
            )
            if is_patch_object and len(node.args) >= 2:
                target, attr = node.args[0], node.args[1]
                if (
                    isinstance(target, ast.Name)
                    and target.id == module_name
                    and isinstance(attr, ast.Constant)
                    and isinstance(attr.value, str)
                ):
                    required.add(attr.value)

            # Case E: getattr(<module>, "X" [, default])
            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "getattr"
                and len(node.args) >= 2
            ):
                target, attr = node.args[0], node.args[1]
                if isinstance(target, ast.Name) and target.id == module_name:
                    if isinstance(attr, ast.Constant) and isinstance(attr.value, str):
                        required.add(attr.value)
                    else:
                        errors.append(
                            f"line {node.lineno}: dynamic getattr({module_name}, <expr>) "
                            "prevents static shim analysis. Replace with explicit attribute "
                            "access or convert the test to enumerate the names."
                        )

    return required, errors


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2

    test_path = Path(argv[1]).resolve()
    scripts_dir = Path(argv[2]).resolve()
    module_name = argv[3] if len(argv) > 3 else "run_quorum"

    if not test_path.is_file():
        print(f"error: test file not found: {test_path}", file=sys.stderr)
        return 2

    tree = ast.parse(test_path.read_text())
    required, errors = collect_references(tree, module_name)

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 2

    if not scripts_dir.is_dir():
        print(f"error: scripts dir not found: {scripts_dir}", file=sys.stderr)
        return 2

    sys.path.insert(0, str(scripts_dir))
    try:
        shim = importlib.import_module(module_name)
    except ImportError as e:
        print(f"error: could not import {module_name} from {scripts_dir}: {e}", file=sys.stderr)
        return 2

    missing = sorted(n for n in required if not hasattr(shim, n))
    if missing:
        print(
            f"shim missing {len(missing)} required names: {missing}",
            file=sys.stderr,
        )
        return 1

    if "--list" in argv:
        # Names only on stdout (no header) so the output is consumable by `cut`/`wc`/`diff`.
        for name in sorted(required):
            print(name)
    else:
        print(f"shim contract OK: {len(required)} names re-exported")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
