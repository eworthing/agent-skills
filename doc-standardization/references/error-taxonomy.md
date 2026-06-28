# Error Taxonomy

Structured map of every output class emitted by
[`scripts/check-doc-naming.sh`](../scripts/check-doc-naming.sh). Detector
details live in [`regex-recipes.md`](regex-recipes.md).

| Class | Severity | Symptom | Canonical fix |
|---|---|---|---|
| `BROKEN` | Blocking | `BROKEN: <src>:<line> -> <target>` | Restore the missing target or update the link to the renamed path. |
| `INDEX-DRIFT` | Blocking | `INDEX-DRIFT: <index> references missing <target>` | Remove the stale index entry or restore the target if deletion was accidental. |
| `CASE` | Blocking | `CASE: <path>` | Rename to lowercase kebab-case, or document the file under a declared bundle exception. |
| `NAMING` | Blocking or advisory | `NAMING: <path> (<reason>)` | Blocking reasons require a rename or documented exception. Advisory reasons indicate lower-kebab project-local names that do not opt into the default grammar; triage them against the local contract. |
| `ORPHAN` | Advisory | `ORPHAN: <path>` | Add the file to the nearest index, archive it with a rationale, or accept it if referenced from outside Markdown. |
| `H1-DRIFT` | Advisory | `H1-DRIFT: <file> -> H1 "<h1>" missing slug token "<token>"` | Edit the H1 to include the topic, rename the file, or accept a legitimate wording difference. |

## Severity guidance

| Severity | Classes | Action |
|---|---|---|
| **Block merge** | `BROKEN`, `INDEX-DRIFT`, `CASE`, blocking `NAMING` | Fix in the same change. These are objective contract or link failures. |
| **Triage before handoff** | `ORPHAN`, `H1-DRIFT`, advisory `NAMING` | Decide whether to index, rename, document an exception, or accept. |
| **Declared exempt** | Allowlisted top-level files, ADR numbering, dated records, common vendor/archive/tool bundle paths | Preserve names, but still validate links. |
