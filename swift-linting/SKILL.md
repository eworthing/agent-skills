---
name: swift-linting
author: eworthing
description: >-
  Resolves repository-specific SwiftFormat / SwiftLint rule violations on
  Apple-platform projects. Use when pre-commit hooks are blocking a
  commit with a lint error, when a `function_body_length` /
  `type_body_length` / `file_length` / `cyclomatic_complexity` /
  `line_length` violation surfaces, when planning a justified
  `// swiftlint:disable:next ...` with rationale, or when reconciling
  SwiftFormat output with hand-formatted code. Targets the
  repo-prescriptive lint config. For concurrency-specific lints like
  `async_without_await` see the authoritative community
  `swift-concurrency` (`references/linting.md`).
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
---

# Linting & Formatting Skill

## Overview

SwiftFormat and SwiftLint with clear separation of concerns, optimized for LLM-assisted development.

| Tool | Owns | Config |
|------|------|--------|
| **SwiftFormat** | Layout, whitespace, wrapping, punctuation | `.swiftformat` |
| **SwiftLint** | Semantics, safety, correctness, complexity | `.swiftlint.yml` |

**Key principle:** SwiftFormat handles *how code looks*, SwiftLint handles *what code does*.

## When to Use

- Lint errors or warnings during build or pre-commit
- Adding `swiftlint:disable` comments to suppress warnings
- Fixing `function_body_length` or `line_length` violations
- Understanding why code is formatted a certain way
- Adding new SwiftLint rules
- Swift 6 `Logger` `@autoclosure` build errors
- `superfluous_disable_command` or `orphaned_doc_comment` warnings

For `file_length` violations (file too long), use the `swift-file-splitting` skill instead — splitting is a refactor, not a lint fix.

## References

Load the relevant reference when working on a specific subtopic. Each is focused and self-contained.

- [SwiftFormat rules and gotchas](references/swiftformat.md) — vertical formatting, trailing commas, explicit-self, Swift 6 `@autoclosure` gotcha, MARK auto-generation, running SwiftFormat.
- [SwiftLint rules and execution](references/swiftlint.md) — rule categories (safety/accessibility/performance), run modes (lint/fix/analyze), pre-commit verification, `file_length` cross-link.
- [Disable comment placement](references/disable-comments.md) — `:next` vs `:this`, common mistakes (attributes, doc comments), diagnostic warnings, troubleshooting table.

## Constraints

- Never disable SwiftLint safety rules without good reason
- Keep files under 600 lines (overlays under 400) — split early
- Use `// swiftformat:disable` sparingly (mainly for Logger `@autoclosure`)
- Run `swiftformat . --lint && swiftlint lint --quiet` before commits
