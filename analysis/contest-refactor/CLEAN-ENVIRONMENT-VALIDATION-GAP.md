# Clean-Environment Validation Gap — contest-refactor vs goose + sweep + superpowers

> **CURRENT-STATE (2026-06-28):** OPEN — Gap A fresh-checkout oracle is absent — G21 full-reverify + dirty-tree abort are SAME-worktree and G32's challenge is v4-only (`validation.md:152`); parked in the plan's W4. Gap B (container) deferred. See [`GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md`](GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md) for the source-verified audit.

Source: `refs/competitors/goose/`, `refs/competitors/sweep/`, `refs/competitors/superpowers/`. Research called this P2: "final validation from fresh checkout, container, or sandbox."

## Research overstatement confirmed

Inspection of cloned competitors finds **goose and sweep do NOT implement clean-environment validation** the way the source landscape research implied:

### goose (`refs/competitors/goose/`)

- **Sandbox** = macOS `sandbox-exec` (Apple seatbelt) for security, NOT workspace isolation for validation. Restricts file access + egress proxy. Documented at `documentation/docs/guides/sandbox.md:1-40`.
- **"Fresh session"** UI option (`crates/goose-cli/src/commands/project.rs`) restarts goose with new session_id in same directory. NOT a fresh checkout.
- **Docker** = distribution/CI vessel only (`BUILDING_DOCKER.md:193`: `docker run --rm -v $(pwd):/workspace`). Mounts live host directory; not validation isolation.
- **No snapshot/rollback** mechanism for state.

**Verdict**: research overstatement. Goose's "sandbox" is security-scoped, not validation-scoped.

### sweep (`refs/competitors/sweep/`)

- Repo is a **shallow stub**: 2 files total; README redirects to JetBrains plugin; `sweepai/` source directory missing.
- Cannot validate research claims; source is elsewhere.

**Verdict**: insufficient material to extract patterns. Skip.

### Only working clean-env pattern in clones: superpowers worktree isolation

`refs/competitors/superpowers/skills/using-git-worktrees/` (already covered in HALT-STATE-GAP Gap A):
- Detect already-in-worktree via `GIT_DIR != GIT_COMMON`
- Prefer native `EnterWorktree` tool; fall back to `git worktree add` to `.worktrees/` (project-local, gitignored) or `~/.config/superpowers/worktrees/$project/`
- Run baseline tests in worktree before proceeding
- Cleanup is user-decided (no auto-cleanup on failure)

This is the ONE pattern from the inspected competitor set that actually delivers clean-environment validation.

## Strategic insight

Clean-environment validation is genuinely valuable for contest-refactor in three scenarios:

1. **HALT_SUCCESS gate (highest stakes)**: before declaring HALT_SUCCESS at 9.5+ scoring, re-validate against a CLEAN checkout. The active branch may have intermediate broken states, untracked files, or worktree-dirty paths the Critic missed. A fresh clone + full test run is the strongest oracle.
2. **Cross-loop drift detection**: between loops, the user may make manual edits the loop doesn't know about. Running the next loop in a fresh worktree forces the loop to re-detect drift via files-on-disk, not in-memory state.
3. **Reproducibility for fixtures** (pairs with SKILL-TDD-FIXTURES-GAP): bad-codebase fixtures must run in a clean environment for `expected/` outputs to be comparable across runs.

But the cost is real: fresh checkout adds minutes per loop; container/VM startup adds more. Not appropriate as default.

## Gap matrix

| Mechanism | contest-refactor | goose | sweep | superpowers |
|---|:--:|:--:|:--:|:--:|
| Worktree isolation | partial (HALT-STATE-GAP Gap A proposes `--worktree` opt-in) | — (security sandbox only) | — (no source) | ✓ `git worktree add` |
| Fresh-checkout validation before HALT_SUCCESS | — | — | — | — |
| Container / VM validation | — | partial (Docker for distribution) | — | — |
| Snapshot + rollback | ✓ `LOOP_STATE.pre_step3_blob_shas` (file-level) | — (event history only) | — | partial (worktree = implicit snapshot) |
| Verification in clean env as explicit phase | — | — | — | — |
| Per-loop branch isolation | — | — | — | partial (worktree per task) |

## P1/P2 GAPS — what to import

### Gap A (P1, opt-in): `--clean-validate-before-halt` flag

Default off. When enabled, contest-refactor adds a Phase 1.3 between Step 1 (Critic) and Step 2 (Architect) ONLY when state transitions to candidate `HALT_SUCCESS`:

1. Critic emits CURRENT_REVIEW.json with provisional `state: HALT_SUCCESS`
2. **NEW Phase 1.3 (Clean re-validation)**:
   - Identify CWD's repo + HEAD SHA
   - Create temp worktree: `git worktree add .contest-refactor/revalidate-worktrees/<short_sha> HEAD`
   - cd into temp worktree
   - Run the discovery's `test_command` end-to-end (full suite, no `--test-filter` override)
   - Re-run validation gates G21 + G24 + G25 against the clean checkout
   - If any gate fails OR test_command fails: revert `state: HALT_SUCCESS` → `state: HALT_STAGNATION` subtype `clean_revalidation_failed` (NEW subtype)
   - Cleanup: `git worktree remove .contest-refactor/revalidate-worktrees/<short_sha>`
3. Step 2 only runs if Phase 1.3 confirmed clean state

**Schema additions** (additive, `schema_version: 4` — default-fill row per [SCHEMA-GAP § Schema-version sequencing](SCHEMA-GAP-CONTEST-REFACTOR.md#schema-version-sequencing-v4v5)):

```jsonc
{
  "clean_revalidation": {
    "performed": true,
    "worktree_path": ".contest-refactor/revalidate-worktrees/abc1234",
    "head_sha_at_revalidation": "abc1234",
    "test_command_run": "swift test",
    "test_command_passed": true,
    "gates_rerun": ["G21", "G24", "G25"],
    "gates_passed": true,
    "duration_seconds": 87
  }
}
```

**New halt subtype**: `clean_revalidation_failed` — single-source-of-truth canon entry lives in [STATE-MACHINE-COMPOSITION-APPENDIX § canon/halt-subtypes.toml consolidated enum](STATE-MACHINE-COMPOSITION-APPENDIX.md). Per Codex round 1 N3 single-ownership rule, this doc does NOT include a standalone `halt_subtypes = [...]` block.

### Gap B (P2): `--container-validate` flag (defer)

For projects with hostile environments (cross-compile targets, package-manager pinning that varies by host, OS-specific build steps), validate in a Docker container before HALT_SUCCESS.

Defer because:
- Adds Docker dependency
- Adds 60-300s per validation
- Most contest-refactor use cases (Swift/Apple, single-language projects) don't need it

Document as opt-in extension for Phase 1.3 when user has Docker available and a `Dockerfile.contest-refactor-validate` in the repo.

### Gap C (defer): VM/cloud validation

Per landscape research, Jules (Google) uses cloud VM validation. Out of scope for contest-refactor (local-first skill, no cloud dependency). Document as path not taken.

## What NOT to import

| Tempting | Why skip |
|---|---|
| Always-on clean validation per loop | Cost prohibitive (minutes per loop, 10-loop cap = 10+ minutes overhead). Gate to HALT_SUCCESS only — when stakes are highest. |
| goose's macOS-only sandbox-exec security model | Single-platform. contest-refactor must run on macOS + Linux + Windows. Worktree pattern (superpowers) is portable. |
| sweep's missing source | Nothing to import. |
| Docker as default | Not all users have Docker. Worktree (`git`) is universally available. |
| Cloud VM validation (Jules pattern) | Contest-refactor is local-first. Cloud is opt-in, not core. |
| Re-validation that runs ALL 31 gates | Only G21 (HALT_SUCCESS criteria) + G24 (Authority Map test-surface) + G25 (Continuation-bridge audit) depend on test/build execution. Other gates already validated in normal Step 1 emit. Don't re-run them. |
| Auto-cleanup of failed-validation worktrees | If clean validation fails, KEEP the worktree for user to inspect what failed. Manual cleanup. |

## Pairing with other gap docs

- **HALT-STATE-GAP Gap A (`--worktree` opt-in mode)**: clean re-validation is a NARROWER use of worktree isolation. Both can ship; `--worktree` is for the whole loop, `--clean-validate-before-halt` is just for the HALT_SUCCESS gate. Either or both can be enabled.
- **HALT-STATE-GAP Gap B (`critic_unfounded` subtype)**: `clean_revalidation_failed` is a sibling subtype with similar semantics (Critic emitted a verdict that didn't survive independent verification).
- **SKILL-TDD-FIXTURES-GAP**: fixture-replay harness should run each fixture in a fresh worktree to ensure baseline traces are reproducible.
- **GATES-GAP Stop hook**: doesn't conflict; Stop hook checks G20 continuation, clean re-validation checks G21 honesty. Different intercept points.

## Adoption order

1. **Phase 1**: Add `clean_revalidation_failed` to `canon/halt-subtypes.toml`. Schema bump for `clean_revalidation` field in CURRENT_REVIEW.json. NO behavior yet; just schema.
2. **Phase 2**: Implement Phase 1.3 worktree creation + test re-run + gate re-run + cleanup. Wire `--clean-validate-before-halt` flag.
3. **Phase 3**: Document failure modes (worktree creation fails, test_command in clean env behaves differently due to missing local-tooling, etc.). Add halt_handoff template for `clean_revalidation_failed`.
4. **Phase 4 (defer)**: Container-based re-validation behind `--container-validate` flag.

## Risk flags

1. **Test command non-reproducibility in clean env**: project-local scripts may reference files not in git (gitignored configs, hooks, secrets). Mitigation: `clean_revalidation_failed` carries detailed diff between active-branch test pass and clean-checkout test fail; user diagnoses environment drift.
2. **Worktree creation collision**: parallel contest-refactor runs in same repo could collide on `.contest-refactor/revalidate-worktrees/<short_sha>` paths. Mitigation: use `<short_sha>-<pid>-<random>` suffix.
3. **Path choice rationale (per Gemini Pro round 3 N1)**: project-local `.contest-refactor/revalidate-worktrees/<sha>` over `/tmp/...` because monorepo toolchains (Bazel, Nx, Cargo workspaces, Lerna) traverse upward to find workspace roots; `/tmp` is outside the project tree and breaks resolution. macOS `/tmp` is also commonly a symlink to `/private/tmp`, which trips symlink-boundary checks in many tools. Matches superpowers' `.worktrees/` pattern. Ensure `.contest-refactor/` is in repo `.gitignore` (already required for `.contest-refactor/hotspots-cache.json` per ROI-PRIORITIZATION-GAP).
3. **Disk space**: large repos with large `git worktree` create disk pressure. Mitigation: validate disk has > 2x repo size free before creating; warn user if low.
4. **Network-dependent test command in clean env**: tests that call external services may behave differently in a worktree (different working tree paths, different env vars). Mitigation: worktree inherits parent env; differences are caused by `cd /tmp/...`-relative paths only.
5. **Symlinked dependencies**: monorepo packages with relative symlinks may break in worktree at `/tmp/...`. Mitigation: detect and warn; user can disable Phase 1.3 for repos with this structure.
