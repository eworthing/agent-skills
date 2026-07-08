# Lens Registry

Map from detected stack → lens reference. Step 0 of the protocol selects exactly one **stack lens** AND loads every entry under [Always-included lenses](#always-included-lenses). Universal architectural rubric (`architecture-rubric.md`) applies regardless.

## Selected stack lens (one of; first match wins)

| Signal in CWD | Stack | Lens |
|---|---|---|
| `Package.swift` OR `*.xcodeproj` OR `*.xcworkspace` OR Swift sources dominate | Apple / SwiftUI | [lens-apple.md](lens-apple.md) |
| `Cargo.toml` | Rust | [lens-generic.md](lens-generic.md) (Rust section) |
| `go.mod` | Go | [lens-generic.md](lens-generic.md) (Go section) |
| `pyproject.toml` OR `tox.ini` OR `pytest.ini` OR `setup.py` | Python | [lens-generic.md](lens-generic.md) (Python section) |
| `package.json` (no Swift signals) | Node / TypeScript | [lens-generic.md](lens-generic.md) (Node section) |
| `build.gradle` OR `pom.xml` OR `*.kts` | JVM (Java/Kotlin) | [lens-generic.md](lens-generic.md) (JVM section) |
| Anything else | Generic fallback | [lens-generic.md](lens-generic.md) |

Multi-stack repos: pick the stack lens for the directory containing the source root with the most lines of source code. Record selection in Discovery.

## Always-included lenses

Loaded unconditionally alongside the selected stack lens. These cover cross-cutting concerns that are not stack-specific.

| Lens | Scope |
|---|---|
| [lens-security.md](lens-security.md) | Input validation, secrets, PII in logs, Keychain, biometric, transport security, dependency hygiene |

Record loaded lenses (selected + always-included) in Discovery as a list: `["lens-apple.md", "lens-security.md"]`.

## Opt-in lenses (loaded only via `--force-lens <name>`)

Not loaded by default. A user-supplied `--force-lens <name>` naming one of these **adds** it alongside the selected stack lens rather than replacing it (see [startup.md § flag catalog](startup.md) for the additive-vs-override distinction).

| Lens | Scope |
|---|---|
| [lens-efficiency.md](lens-efficiency.md) | Recomputed derived values, sequential independent effects — opt-in, not loaded by default |

## Adding a new lens

1. Create `lens-<name>.md` in this directory. Mirror `lens-apple.md` structure: stack-specific concurrency rules, hidden state machine signals, idiomatic checks, language-specific Core Questions. For always-included cross-cutting lenses, mirror `lens-security.md` structure (no stack-specific assumptions). Opt-in lenses (loaded only via `--force-lens <name>`) mirror `lens-security.md`'s structure the same way.
2. Reuse `architecture-rubric.md` vocabulary + tests. Lens describes language idioms or cross-cutting concerns, not architectural tests (those are universal).
3. Add a row to the appropriate table above (Selected stack lens for stack-specific; Always-included for cross-cutting; Opt-in for `--force-lens`-only lenses).
4. Do not edit SKILL.md. Step 0 reads this registry to pick the stack lens and load always-included lenses.
