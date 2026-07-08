# Project Config — `.contest-refactor.toml`

Durable per-project configuration for the contest-refactor loop. Lives at the repo root. Optional — the loop runs with sensible defaults when the file is absent.

The example file at the skill root is [`.contest-refactor.example.toml`](../.contest-refactor.example.toml). Copy it to `.contest-refactor.toml` in your target repo and edit values to taste.

This config NEVER overrides The Evidence Chain (see [method.md](method.md)), validation gates (see [validation.md](validation.md)), or safety checks (see [SKILL.md § Guardrails](../SKILL.md)).

## Contents

- [Schema](#schema)
- [Resolution order](#resolution-order)
- [Accepted residuals — semantics + expiry rule](#accepted-residuals--semantics--expiry-rule)
- [Validator coverage](#validator-coverage)

## Schema

```toml
version = 1

# Top-level keys (must precede any [table]) for TOML scope reasons.
ignore = [
    "<glob>",              # primary_file globs excluded from finding emission
]

[defaults]
lens = "apple"             # apple | generic — default lens for Step 0; CLI --force-lens overrides
loop_cap = 10              # default loop count; CLI --cap overrides
test_command = "<shell>"   # discovery hint when Step 0 cannot detect a test runner

[[accepted_residuals]]
id = "<unique-string>"     # human-readable stable id
pattern = "<glob>"         # file pattern the residual applies to
reason = "<non-empty>"     # rationale text
accepted_by = "<name>"     # who approved the residual (person or council)
accepted_on = "YYYY-MM-DD" # ISO-8601 date the residual was accepted
expires = "YYYY-MM-DD"     # MANDATORY ISO-8601 expiry date
```

Note: in TOML, anything after a `[table]` header belongs to that table until the next header. Place top-level scalars and arrays (`version`, `ignore`) before any `[defaults]` or `[[accepted_residuals]]` block.

Top-level keys:

- `version` — schema version. Currently `1`.
- `defaults` — defaults for CLI-overridable flags. The full set of recognized keys is `lens`, `loop_cap`, `test_command`. Unknown keys are a validator error.
- `ignore` — array of globs. Findings whose `primary_file` matches any glob are downgraded to scope-limited and excluded from oscillation/retirement counting. Useful for generated code (`*.pb.go`, codegen output) and vendored dependencies.
- `accepted_residuals` — array of long-lived residual entries (TOML `[[accepted_residuals]]` array-of-tables). Each entry is a structured exception to the 9.5+ rule. See § Accepted residuals below.

## Resolution order

When the loop reads CLI flags + config:

1. Hard-coded skill defaults (`loop_cap: 10`, lens detection per `lenses.md`).
2. `.contest-refactor.toml` at the repo root (when present).
3. CLI flags (`--force-lens`, `--cap`, `--test-filter`, etc.) override config.
4. Per-invocation flags (`--dry-run`) are invocation-scoped and not persisted.

The config never raises a residual to `HALT_SUCCESS` unless the residual's `expires` date is in the future at loop start.

## Accepted residuals — semantics + expiry rule

An accepted residual is a documented, scope-limited exception to the 9.5+ scoring threshold for a specific file or pattern. The rubric in [architecture-rubric-scoring.md § 9.5+ Threshold](architecture-rubric-scoring.md#95-threshold-the-contest-target) gives the structural rules; this config gives the durability.

Mandatory fields per entry:

- `id` — unique kebab-case identifier (e.g., `"audio-session-lease-deinit-carve-out"`).
- `pattern` — glob matching the file(s) the residual applies to.
- `reason` — non-empty rationale string.
- `accepted_by` — non-empty approver string (person name or council/team).
- `accepted_on` — ISO-8601 date the residual was accepted.
- `expires` — **MANDATORY** ISO-8601 expiry date. Residuals without `expires` are a validator error.

The expiry rule:

- A residual whose `expires` date is in the **future at loop start** can satisfy `HALT_SUCCESS`.
- A residual whose `expires` date is in the **past at loop start** cannot satisfy `HALT_SUCCESS`. The Critic must reconsider the residual as active unless current evidence shows it no longer applies (in which case the entry should be removed from the config).

The expiry rule is enforced by `scripts/validate-artifact.py`: a `HALT_SUCCESS` artifact citing an expired residual fails the validator.

## Validator coverage

`scripts/validate-repo.py` checks `.contest-refactor.example.toml` (and `.contest-refactor.toml` when present) for:

- TOML parses without error.
- Every top-level key is recognized.
- Every `accepted_residuals[]` entry carries all six required fields (`id`, `pattern`, `reason`, `accepted_by`, `accepted_on`, `expires`).
- `ignore` is an array (not a scalar).
- No obvious secrets: no entries that look like API keys (`AKIA`, `sk-`, `xoxb-`, etc.) or user-specific absolute paths.

`scripts/validate-artifact.py` checks the live-run artifact for expired residuals cited at `HALT_SUCCESS`.

See the skill root's [`.contest-refactor.example.toml`](../.contest-refactor.example.toml) for a realistic example.
