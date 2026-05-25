# Agent Skills

Reusable skills for AI coding agents — Claude Code, Codex CLI, opencode, Gemini CLI, and Copilot CLI.

Single source of truth lives here; agent CLIs consume each skill through a symlink (see [Deployment](#deployment)).

## Skills

### Apple platform — SwiftUI / UIKit / Foundation

- **[apple-multiplatform](apple-multiplatform/)** — Cross-platform Apple SwiftUI compatibility reference for iOS, iPadOS, macOS, Mac Catalyst, and tvOS. Platform-conditional code, `#if os()` vs `#if canImport()`, gating `editMode` / drag-receiving / haptics for tvOS, `TabView` `.page` vs `.automatic`, Mac Catalyst sidebar/window defaults, `XCUICoordinate` / `NSToolbar` UI-test divergence.
- **[apple-tvos](apple-tvos/)** — Definitive tvOS reference for SwiftUI on Apple TV: focus engine, accessibility deltas, and design-regression checks. Settle delays, `.focusable()` container blocking, `.onExitCommand` Menu dismissal, destructive `confirmationDialog` default focus, modal focus containment, glass-on-glass on tvOS.
- **[ios-security-hardening](ios-security-hardening/)** — Input-validation and file-handling safeguards for untrusted data: path-traversal prevention, URL scheme/domain allowlisting, multi-source image-reference resolution, CSV/JSON sanitization, AI prompt sanitization, sandbox directory usage, iOS Data Protection levels.
- **[swift-file-splitting](swift-file-splitting/)** — Splits oversized Swift files into smaller units while preserving visibility and build correctness. SwiftLint `file_length` violations, type/extension extraction.
- **[swift-linting](swift-linting/)** — Resolves repository-specific SwiftFormat / SwiftLint rule violations. `function_body_length` / `type_body_length` / `file_length` / `cyclomatic_complexity` / `line_length` fixes, justified `// swiftlint:disable:next` with rationale, reconciling SwiftFormat output with hand-formatted code.
- **[swiftdata-persistence](swiftdata-persistence/)** — SwiftData patterns and gotchas for `@Model`, `ModelContext`, `ModelContainer`, `FetchDescriptor`, migrations, cascade-delete relationships. Bundled seed data, "data not showing" / "stale entity" / "images-show-placeholder-after-upgrade" diagnostics, auto-saving on a timer.
- **[swiftui-design-tokens](swiftui-design-tokens/)** — Applies project design tokens for colors, spacing, typography, motion, and button styling in SwiftUI on iOS, macOS, and tvOS. Spring/timed motion tokens, Reduce Motion alternatives, replacing hardcoded values, macOS form styling, modal frame sizing.
- **[swiftui-drag-drop](swiftui-drag-drop/)** — SwiftUI drag-and-drop architecture for iOS, iPadOS, macOS. `DropDelegate` vs `.onDrop`, drop-priority routing, multi-provider payload extraction, NSItemProvider lifecycle, Chrome image drag (`public.tiff` / `public.html` / `public.url`), Button drop-attachment pitfalls.
- **[swiftui-file-export](swiftui-file-export/)** — SwiftUI file export with the modern `Transferable` API on iOS 16+ / macOS 13+. `fileExporter` root-placement rules, `ShareLink` vs `fileExporter`, sandbox compliance, macOS entitlements, menu-bar `Commands` integration, "fileExporter silent failure on macOS" diagnosis.
- **[swiftui-native-ux](swiftui-native-ux/)** — Native iPhone/iPad SwiftUI design intelligence. `TabView` vs `NavigationStack` vs `NavigationSplitView`, empty/detail pane states, iPhone-to-iPad adaptation, sheet vs inspector vs sidebar, Liquid Glass placement, anti-web-smell critique, Dynamic Type / VoiceOver / Reduce Transparency review.
- **[xctest-ui-testing](xctest-ui-testing/)** — XCTest UI automation for iOS, macOS, tvOS. Typed-enum accessibility identifiers, wait-for-element, drag-and-drop testing, sheet/alert coverage, macOS window-pinning, `.xctestrun`-based selective execution (`-only-testing`, list/range/glob/match/class/id), zero-test detection, `-retry-tests-on-failure`.

### Cross-language tooling

- **[bash-macos](bash-macos/)** — Keeps shell scripts portable across macOS (Bash 3.2, BSD userland) and Linux (Bash 4+, GNU coreutils). Debugs "command not found" / "invalid option" / "mapfile: command not found", GNU-vs-BSD `sed`/`grep`/`date`/`readlink` issues, snake_case verb-first renames.
- **[doc-standardization](doc-standardization/)** — Standardizes documentation naming, organization, and cross-references in Markdown projects. Enforces `[domain]-[feature]-[type]-[status].md` filename pattern, valid internal links, ordered index files, code-to-doc identifier alignment.

### Workflow / meta

- **[contest-refactor](contest-refactor/)** — Autonomous Actor-Critic refactoring loop. Aggressively refactors the workspace to a 9.5+ standard using a strict ICA-grounded architectural rubric (deletion test, two-adapter rule, depth-as-leverage). Invoke via `/contest-refactor`.
- **[peer-plan-review](peer-plan-review/)** — Sends an implementation plan to another AI agent (Codex, Gemini CLI, Claude Code, Copilot, opencode) for iterative review, revises, and re-submits until approval or round limit. Provider adapters, session resume, process-tree timeout kill. Usage: `/peer-plan-review <codex|gemini|claude|copilot|opencode> [model] [effort]`.

### Experimental (not symlinked by default)

- **[quorum-review](quorum-review/)** — Multi-provider consensus review system (v3.1). Anonymous quorum reviews for plans/specs/diffs with canonical issue IDs, conservative merges, independent verifier. v3.1 refactor split the orchestrator into a `quorum/` package and vendored shared infrastructure from `/common/` (see [quorum-review/CHANGELOG.md](quorum-review/CHANGELOG.md)). Source in-repo only — install manually if you want to try it.

## Deployment

Each agent CLI looks for skills in its own per-user directory. Best practice: **symlink** the repo skill into each directory — never copy.

| Agent | Discovery path |
|---|---|
| Claude Code | `~/.claude/skills/<skill>` |
| Codex CLI | `~/.codex/skills/<skill>` |
| opencode | `~/.config/opencode/skills/<skill>` |
| Gemini CLI | `~/.agents/skills/<skill>` (shared community location) |
| Gemini Antigravity CLI | `~/.gemini/antigravity-cli/skills/<skill>` |

> **Note on `~/.agents/skills/`:** this directory is also used by external/community skills (swiftui-expert-skill, swift-concurrency, etc.). The install loop below skips any existing entry that isn't already a symlink to *this* repo — community skills are never clobbered. Gemini CLI also offers `gemini skills link <path>` as a first-party alternative.

### Why symlink, not copy

- One source of truth — edit the file in this repo and every agent picks it up immediately on the next session.
- No drift between agents.
- `git pull` updates all three CLIs simultaneously.
- Easy to opt out: `rm ~/.claude/skills/<skill>` disables for one agent without touching the repo.

### Install one skill

```bash
SRC="$(pwd)"            # run from this repo's root
SKILL=peer-plan-review  # change per skill

ln -s "$SRC/$SKILL" "$HOME/.claude/skills/$SKILL"
ln -s "$SRC/$SKILL" "$HOME/.codex/skills/$SKILL"
ln -s "$SRC/$SKILL" "$HOME/.config/opencode/skills/$SKILL"
ln -s "$SRC/$SKILL" "$HOME/.agents/skills/$SKILL"          # Gemini CLI
ln -s "$SRC/$SKILL" "$HOME/.gemini/antigravity-cli/skills/$SKILL"  # Gemini Antigravity CLI
```

### Install every published skill into all four agents

`quorum-review` is excluded — still under test. Add it manually if you want to try it.

```bash
SRC="$(pwd)"
SKILLS=(
  apple-multiplatform apple-tvos bash-macos contest-refactor
  doc-standardization ios-security-hardening peer-plan-review
  swift-file-splitting swift-linting swiftdata-persistence
  swiftui-design-tokens swiftui-drag-drop swiftui-file-export
  swiftui-native-ux xctest-ui-testing
)
DESTS=(
  "$HOME/.claude/skills"
  "$HOME/.codex/skills"
  "$HOME/.config/opencode/skills"
  "$HOME/.agents/skills"                   # Gemini CLI (shared with community skills)
  "$HOME/.gemini/antigravity-cli/skills"   # Gemini Antigravity CLI
)

for dest in "${DESTS[@]}"; do
  mkdir -p "$dest"
  for skill in "${SKILLS[@]}"; do
    target="$dest/$skill"
    if [ -e "$target" ] && [ ! -L "$target" ]; then
      echo "skip: $target exists and is not a symlink" >&2
      continue
    fi
    if [ -L "$target" ]; then
      current="$(readlink "$target")"
      expected="$SRC/$skill"
      if [ "$current" != "$expected" ]; then
        echo "skip: $target -> $current (different source; not overwriting)" >&2
        continue
      fi
    fi
    ln -snf "$SRC/$skill" "$target"
  done
done
```

The loop is idempotent and safe in shared dirs:

- Real files at the target path are skipped with a warning.
- Symlinks already pointing at *this* repo are refreshed via `ln -snf`.
- Symlinks pointing at a different source (e.g. community skills in `~/.agents/skills/`) are skipped, not clobbered.

### Verify

```bash
for dest in ~/.claude/skills ~/.codex/skills ~/.config/opencode/skills ~/.agents/skills ~/.gemini/antigravity-cli/skills; do
  echo "== $dest =="
  ls -la "$dest" | grep -- '-> '"$(pwd)" || echo "(none from this repo)"
done
```

Broken symlinks (target moved or renamed) appear as red entries under `ls -la` on most terminals; fix with `rm` + re-`ln`.

### Codex YAML alternative

Codex also accepts `agents/openai.yaml`-style declarations if you prefer YAML-configured agents over symlink discovery.

## Repo Conventions

- One directory per skill at the repo root.
- Each skill: `SKILL.md` (YAML frontmatter + body), optional `references/` (progressive disclosure), optional `scripts/` (helper executables), and `EVAL.md`.
- Skill descriptions lead with capabilities and contain a "Use when…" trigger phrase (required by `scripts/eval-skill.py`).
- Shell scripts target portable Bash (macOS 3.2 + Linux 4+) — see [`bash-macos`](bash-macos/).
- Each skill ships an `EVAL.md` scored against the multi-framework rubric in the local `skill-evaluator` plugin (`.claude/skills/skill-evaluator-1.0.0/`). Target ≥ 90/100 before publishing.
- Commit style: `feat(<skill>): <change> (<old>→<new> EVAL)` when an eval score shifts. Otherwise standard Conventional Commits.

## License

MIT
