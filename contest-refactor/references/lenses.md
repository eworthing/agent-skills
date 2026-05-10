# Lens Registry

Map from detected stack → lens reference. Step 0 of the protocol selects exactly one lens. Universal architectural rubric (`architecture-rubric.md`) applies regardless.

## Detection rules (first match wins)

| Signal in CWD | Stack | Lens |
|---|---|---|
| `Package.swift` OR `*.xcodeproj` OR `*.xcworkspace` OR Swift sources dominate | Apple / SwiftUI | [lens-apple.md](lens-apple.md) |
| `Cargo.toml` | Rust | [lens-generic.md](lens-generic.md) (Rust section) |
| `go.mod` | Go | [lens-generic.md](lens-generic.md) (Go section) |
| `pyproject.toml` OR `tox.ini` OR `pytest.ini` OR `setup.py` | Python | [lens-generic.md](lens-generic.md) (Python section) |
| `package.json` (no Swift signals) | Node / TypeScript | [lens-generic.md](lens-generic.md) (Node section) |
| `build.gradle` OR `pom.xml` OR `*.kts` | JVM (Java/Kotlin) | [lens-generic.md](lens-generic.md) (JVM section) |
| Anything else | Generic fallback | [lens-generic.md](lens-generic.md) |

Multi-stack repos: pick the lens for the directory containing the source root with the most lines of source code. Record selection in Discovery.

## Adding a new lens

1. Create `lens-<name>.md` in this directory. Mirror `lens-apple.md` structure: stack-specific concurrency rules, hidden state machine signals, idiomatic checks, language-specific Core Questions.
2. Reuse `architecture-rubric.md` vocabulary + tests. Lens describes language idioms, not architectural tests (those are universal).
3. Add a row to the table above.
4. Do not edit SKILL.md. Step 0 reads this registry to pick the lens.
