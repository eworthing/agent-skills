# Multi-Harness Adapter Gap — contest-refactor cross-harness distribution

Sources:

- `refs/competitors/wshobson-agents/` (35.9k★, MIT, added 2026-05-25 p.m.) — **adapter-driven** multi-harness generation. One markdown source under `plugins/` → adapters (`tools/adapters/{base,codex,cursor,opencode,gemini}.py`) transform per harness → gitignored per-harness artifacts. Five harnesses: Claude Code, Codex CLI, Cursor, OpenCode, Gemini CLI.
- `refs/competitors/alirezarezvani-claude-skills/` (16.1k★, MIT, added 2026-05-25 p.m.) — **sync-script-driven** alternative. Stdlib-Python scripts (`sync-codex-skills.py`, `sync-gemini-skills.py`, `sync-hermes-skills.py`, `sync-vibe-skills.py`) generate symlinks + index from single domain-folder source-of-truth. 4 harnesses via symlinks.

## Baseline: contest-refactor today

- Single-source skill at `contest-refactor/` directory
- Installed per harness via symlinks per project CLAUDE.md:
  ```bash
  ln -s "$PWD/contest-refactor" "$HOME/.claude/skills/contest-refactor"
  ln -s "$PWD/contest-refactor" "$HOME/.codex/skills/contest-refactor"
  ln -s "$PWD/contest-refactor" "$HOME/.config/opencode/skills/contest-refactor"
  ln -s "$PWD/contest-refactor" "$HOME/.agents/skills/contest-refactor"
  ln -s "$PWD/contest-refactor" "$HOME/.gemini/antigravity-cli/skills/contest-refactor"
  ```
- `references/provider-adapters.md` handles per-harness adapter logic AT RUNTIME (loop_model, reviewer_model, spawn_isolation defaults per provider)
- No build-time transformation; the same `SKILL.md` body works for all harnesses

## Gap matrix

Legend: **✓** = present, **partial** = weaker form, **—** = absent.

| Mechanism | contest-refactor | wshobson | alirezarezvani |
|---|:--:|:--:|:--:|
| Single source-of-truth per skill | ✓ `contest-refactor/SKILL.md` | ✓ `plugins/<name>/skills/<n>/SKILL.md` | ✓ `<domain>/skills/<n>/SKILL.md` |
| Per-harness build artifacts | — (same SKILL.md used as-is) | ✓ gitignored generated artifacts per harness | ✓ symlinked + index per harness (4 sync scripts) |
| Adapter framework (transforms not symlinks) | — | ✓ Python adapter ABC + per-harness subclasses | partial (symlinks only; no transform) |
| Harnesses supported | 5 (Claude Code, Codex, opencode, Agents CLI, Gemini Antigravity) via symlinks | 5 (Claude Code, Codex, Cursor, OpenCode, Gemini CLI) via adapters | 4 (Claude Code, Codex, Gemini, Hermes/Vibe) via sync scripts |
| Per-harness body-size cap enforcement | — | ✓ Codex 8 KB hard cap; overflow auto-shunted to `references/details.md` | — |
| Per-harness model-alias mapping | partial (`references/provider-adapters.md` runtime-only) | ✓ `tools/adapters/capabilities.py` MODEL_ALIASES (opus→GPT-5 family for Codex; opus→`anthropic/claude-opus-4-7` for OpenCode; etc.) | — |
| Per-harness frontmatter transform | n/a (single format used everywhere) | ✓ Markdown→TOML for Codex; CamelCase→lowercase tool names for OpenCode; `tools:` → `permission:` deny-blocks for OpenCode | — |
| Per-harness validation gate | partial (`scripts/eval-skill.py` per-skill) | ✓ `make validate` per-harness syntax checks + frontmatter required fields + size caps + tool-name case | partial (sync scripts validate manifest entries) |
| Drift detection across harnesses | — | ✓ `make garden` finds dead refs, orphans, oversize, marketplace mismatches | — |
| CI integration | partial (project CI may run `eval-skill.py`) | ✓ `.github/workflows/validate.yml` runs validate + garden + tests on every PR | — |
| Marketplace registry | — (no marketplace; symlinks only) | ✓ `.claude-plugin/marketplace.json` + per-harness equivalents | partial (per-domain `plugin.json` files) |

## Strategic insight

Contest-refactor's symlink approach is the SIMPLEST cross-harness strategy. Works for skills whose body needs ZERO per-harness transformation. Pros: no build step, no toolchain, edits propagate instantly. Cons: limited to skills whose `SKILL.md` + `references/*.md` + `scripts/*` work verbatim under every harness's expectations.

wshobson's adapter approach is the MOST POWERFUL but requires Python build toolchain + per-harness adapter code. Pros: per-harness optimization (Codex 8KB body cap auto-shunt; OpenCode permission-block generation; Cursor `.mdc` format). Cons: maintenance burden; gitignored generated artifacts can drift; requires CI.

alirezarezvani's sync-script approach is INTERMEDIATE. Symlinks + index generation but no body transformation. Pros: simpler than adapters, more discoverable than raw symlinks (manifest indexes). Cons: doesn't solve body-incompatibility issues (Codex 8KB cap, OpenCode permission shape).

## When does contest-refactor NEED an adapter?

contest-refactor's `SKILL.md` is currently ~7KB (under Codex 8KB cap, per agent-skills/CLAUDE.md skill-description-sizing memory) but its bundled `references/*.md` files are larger. The shipping `references/` mechanism may NOT work identically across harnesses:

| Harness | references/*.md support |
|---|---|
| Claude Code | ✓ progressive disclosure (skill loads SKILL.md, references loaded on demand via Read) |
| Codex CLI | ✓ `references/` directory loaded similarly per agent-skills CLAUDE.md |
| opencode | partial (per-skill structure varies; needs verification) |
| Gemini CLI / Antigravity | partial (per-skill structure varies; needs verification) |
| Cursor (hypothetical future) | ✗ `.cursor/rules/*.mdc` doesn't natively support references/ subdir |

**Current evidence**: project CLAUDE.md asserts symlinks work across all 5 harnesses today, validating contest-refactor's symlink strategy AS LONG AS each harness honors SKILL.md + references/. If that assumption breaks for any future harness, an adapter becomes mandatory.

## P2 GAPS — what to potentially import (per user authorization 2026-05-25)

### Gap A: Adapter framework when adding a 6th+ harness

**Decision rule**: contest-refactor stays symlink-only AS LONG AS every supported harness honors:
1. `SKILL.md` YAML frontmatter (name, description, allowed-tools)
2. `references/*.md` progressive disclosure (loaded on demand, not bundled)
3. `scripts/*` directly executable (bash on POSIX; portable per `bash-macos` skill discipline)

If a future 6th harness violates any of these (e.g., body-size hard cap < SKILL.md current size, or no `references/` mechanism), introduce wshobson-style adapter framework:

```
contest-refactor/
├── SKILL.md                          # canonical source
├── references/                       # canonical source
├── scripts/                          # canonical source
├── adapters/                         # NEW: per-harness transforms
│   ├── base.py                       # ABC + shared parser
│   ├── claude_code.py                # passthrough (current behavior)
│   ├── codex.py                      # markdown→TOML if Codex ever requires
│   ├── cursor.py                     # SKILL.md → .mdc if Cursor support added
│   └── opencode.py                   # tools[] → permission{} if needed
└── .generated/                       # gitignored; per-harness outputs
    ├── codex/
    ├── cursor/
    └── opencode/
```

**Cost**: Python build toolchain dependency. Marginal — agent-skills already requires Python 3.11+ for `scripts/eval-skill.py` + `scripts/sync_common.py`.

### Gap B: Drift-detection script (`make garden` equivalent)

**Adopt** even WITHOUT adapter framework. Scan all 5 symlinked install locations + verify:
- Symlinks point to repo, not stale paths
- SKILL.md body size under each harness's cap (8KB Codex; unknown others)
- `references/*.md` refs in SKILL.md actually exist
- `scripts/*` files actually exist and are executable

**Implementation**: extend `scripts/eval-skill.py` with a `--cross-harness-check` mode that does the above. ~50 LoC addition.

### Gap C: Per-harness validation in CI

**Adopt** as cheap addition. Add to project CI:

```yaml
# .github/workflows/validate-skills.yml
- name: Validate contest-refactor across harnesses
  run: python3 scripts/eval-skill.py contest-refactor --cross-harness-check
```

Catches symlink rot, body-size drift, dead reference links.

## What NOT to import

| Tempting | Why skip |
|---|---|
| wshobson's full adapter framework | Premature optimization for contest-refactor today. Symlinks work for all 5 currently-supported harnesses; adapter framework adds toolchain + CI burden with no current payoff. |
| alirezarezvani's sync-script-per-harness approach | Same as wshobson — over-engineering. Symlinks achieve equivalent at lower cost. |
| Marketplace registry pattern | contest-refactor is NOT a marketplace (single skill, not collection). `.claude-plugin/marketplace.json` is N/A. |
| Model-alias mapping in build artifacts | Runtime `provider-adapters.md` already handles per-provider model defaults. Build-time mapping would duplicate. |
| Per-harness frontmatter transform | Current SKILL.md frontmatter works across all 5 harnesses verbatim. No transform needed. |

## Recommendation

**Keep symlink-only strategy until a 6th harness forces an adapter.** Adopt drift-detection (Gap B) as cheap insurance. Defer full adapter framework (Gap A) indefinitely.

The adapter framework adds value when SKILL.md body grows past Codex's 8KB cap OR when adding Cursor support (`.mdc` format incompatible with raw SKILL.md). Track contest-refactor SKILL.md size; if it grows past 7KB plan Gap A; if it stays under, keep symlinks.

## Pairing with other gap docs

- **No direct overlap** with other gap docs. This is a NEW orthogonal axis (distribution mechanism, not loop mechanics).
- Loosely related to GOVERNANCE-GAP (both touch project-config + manifest discipline) but different problem.

## Cost summary

| Gap | Lift | Adoption time | Maintenance |
|---|---|---|---|
| Gap A (adapter framework) | Large — new Python toolchain | 1-2 weeks | Per-harness adapter updates per harness release |
| Gap B (drift-detection script) | Small — ~50 LoC | 1-2 days | None ongoing |
| Gap C (per-harness CI gate) | Trivial — 5 LoC of YAML | 1 hour | None ongoing |

Recommended adoption: **Gap C immediately + Gap B when convenient + Gap A only when forced**.

## Risk flags

1. **Harness fragmentation risk**: as more harnesses emerge, single-source-symlink strategy may break. Monitor: claude-code 4.x changes, Codex SKILL.md schema changes, opencode skill API changes, Gemini Antigravity changes, hypothetical Cursor support.
2. **CI-cost asymmetry**: per-harness validation in CI may bloat run-time. Mitigation: parallelize harness checks; skip on docs-only PRs.
3. **Drift opacity**: today no automated check that symlinks remain valid. Gap B addresses; Gap C enforces.
