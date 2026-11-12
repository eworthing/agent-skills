# code-review-opencode — Self-review scope rotation

The reference `max` recipe is sized for a normal PR. The full working-tree diff
is about 11.8k lines / 51 files, and the review scope combines it with the
branch range (~16.2k combined lines), so running the full 10-finder fleet over
tests, docs, and plugin code on every iteration is the slowest possible case.
Scope each pass to one surface and fix that surface before moving on.

## Rotation

1. **Plugin pass (primary):** target `.opencode` — the 12 plugin TypeScript
   files plus the 4 agent definitions (~11.4k combined lines).
2. **Test pass:** target `test` — the test suite and fixtures (~4.5k combined
   lines).
3. **Docs pass (occasional):** target one documentation file at a time
   (`README.md`, then the `CODE_REVIEW_*.md` files). The docs diff is small.
4. **Full-repo pass:** final gate only, after the plugin and test passes are
   clean.

Do not launch the next pass until the current pass is fixed and the suite is
green:

- validate every reported finding against the current code;
- fix validated findings in main;
- add a regression test for each behavior change;
- run `node --test test/*.test.ts`.

## Measured scope sizes

In `cr-self4` before the run 14 fixes, `resolveScope` reports the combined
branch range (`main...HEAD`) plus the working tree:

| Scope | Files | Combined diff lines | Diff chars |
|---|---:|---:|---:|
| Full repo | 51 | 16,171 | 770 KB |
| `.opencode` | 35 | 11,390 | 548 KB |
| `.opencode/plugins/code-review-opencode` | 31 | 10,834 | 528 KB |
| `test` | 15 | 4,542 | 207 KB |
| Docs (`git diff HEAD` only) | — | 163 | 8.7 KB |

The plugin code is most of the change set, so a path filter alone does not make
the plugin pass small. It does remove tests and docs, which is the point of the
rotation.

## Incremental fix passes

`resolveScope` reviews both the branch range and the working tree, so a path
filter still includes the committed reconstruction. For a fast fix-only pass,
create a baseline commit of the pre-fix tree in the review copy, apply the
fixes, and target the range `baseline...HEAD` (or point `main` at the baseline).
Use this for small fix batches between full scoped passes; keep the full scoped
pass as the periodic completeness check.

## Commands

Plugin pass:

```
/code-review-opencode max --max-findings all --concurrency 6 .opencode
```

Test pass:

```
/code-review-opencode max --max-findings all --concurrency 6 test
```

Docs pass:

```
/code-review-opencode max --max-findings all --concurrency 6 README.md
```

Full-repo gate:

```
/code-review-opencode max --max-findings all --concurrency 4
```

## Concurrency

- Use `--concurrency 6` for scoped passes while the 6-way gate is being
  validated.
- Revert to 4 if a child stalls or the run is partial.
- Keep the full-repo pass at 4 until a full-repo 6-way run completes cleanly.
- `cr-conc6` is only a copy of main. Resync it after the current run's fixes
  land; do not review a pre-fix tree.
