# Error Taxonomy

Structured map of every error class this skill detects, plus the recipe
that finds it and the canonical fix. Detector references point at
[`regex-recipes.md`](regex-recipes.md). The bundled
[`scripts/check-doc-naming.sh`](../scripts/check-doc-naming.sh) runs all
of these in one pass.

| Error class | Detector recipe | Symptom (output line) | Canonical fix |
|---|---|---|---|
| **Broken link** | Recipe 4 (Validate links exist) | `BROKEN: <src> -> <target>` | Either restore the missing target or update the reference to its renamed path. Re-run the validator after every batch of renames. |
| **Orphan file** | Recipe 5 (Find orphan markdown files) | `ORPHAN: <path>` | Add the file to the nearest `README.md` index; or move it to `docs/archive/` with a note in `docs/archive/README.md`; or, if the file is referenced from code only, accept the report. |
| **Index drift** | Recipe 6 (Find index drift) | `INDEX-DRIFT: <index> references missing <target>` | Remove the dead entry from the index, or restore the target if the deletion was accidental. |
| **Case violation** | Recipe 7 (Find case violations) | `CASE: <path>` | `git mv` to lowercase-hyphenated form, then re-run Recipe 4 to catch references to the old casing. |
| **Naming-convention miss** | Recipe 2 (Detect naming-convention violations) | `NAMING: <path>` | Rename to `[domain]-[feature]-[type]-[status].md` via `git mv`. See SKILL.md Step 3. |
| **Missing status suffix** | Recipe 2 (subset) | `NAMING: …-spec.md` | Append correct status: `-draft` / `-proposed` / `-active` / `-implemented` / `-deprecated`. |
| **H1 / filename mismatch** | Recipe 8 (Find H1 / filename mismatch) | `H1-DRIFT: <file> -> H1 "<h1>" missing slug token "<token>"` | Either edit the H1 to mention the primary slug token, or rename the file. Advisory — legitimate rewordings will trigger it. |

## Severity guidance

| Severity | Error classes | Action |
|---|---|---|
| **Block merge** | Broken link, Index drift | Always fix before merge. These are unambiguous. |
| **Block release** | Case violation, Missing status suffix | Fix in the same PR as the introducing change. |
| **Advisory** | Orphan file, Naming-convention miss (allowlisted bases), H1 / filename mismatch | Triage. Many false positives expected for orphans and H1 drift. |
