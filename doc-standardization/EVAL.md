# doc-standardization Evaluation

**Date:** 2026-06-28
**Evaluator:** Codex GPT-5
**Skill version:** Project-local docs contract rewrite with fixture-backed validator
**Automated score:** 100% (13/13)
**Manual score:** **100/100** - Excellent

---

## Automated Checks

```
Skill Evaluation: doc-standardization
==================================================
  [STRUCTURE]
    PASS SKILL.md exists
    PASS SKILL.md has valid frontmatter
    PASS Skill name matches directory
    PASS No extraneous files
    PASS Resource directories are non-empty
  [TRIGGER]
    PASS Description length adequate
    PASS Description includes trigger contexts
  [DOCUMENTATION]
    PASS SKILL.md body length
    PASS References are linked from SKILL.md
  [SCRIPTS]
    PASS Python scripts parse without errors
    PASS Scripts use no external dependencies
  [SECURITY]
    PASS No hardcoded credentials or emails
    PASS Environment variables documented

  Pass: 13  Warn: 0  Fail: 0
  Structural score: 100%
```

## File Layout

```
doc-standardization/
  SKILL.md                          148 lines
  EVAL.md                           this file
  references/
    conventions.md                   88 lines
    error-taxonomy.md                22 lines
    regex-recipes.md                111 lines
  scripts/
    check-doc-naming.sh             298 lines, executable
    run-tests.sh                     66 lines, executable
  tests/
    fixtures/                        11 fixture docs trees
```

## Current Behavior

- Discovers project-local docs taxonomy from `docs/README.md` or the nearest
  index instead of imposing a universal directory tree.
- Keeps default grammar for curated docs: `<topic>-<type>-<status>.md`.
- Recognizes dated records: `<topic>-<type>-YYYY-MM-DD.md`.
- Recognizes ADR numbering: `adr/NNNN-topic.md`.
- Treats common vendor/archive/tool bundle paths as declared-style filename
  exceptions while still validating their links.
- Fails blocking classes: filename hygiene, invalid opted-in type/status,
  broken links, and stale README index links.
- Reports advisory classes: project-local lower-kebab names, orphan docs, and
  H1/topic drift.

## Fixture Coverage

`scripts/run-tests.sh` covers:

- clean project-local taxonomy
- clean strict type/status grammar
- clean dated records
- clean ADR numbering
- clean declared bundle exemption
- broken link failure
- index drift failure
- invalid status failure
- uppercase/space filename failure
- orphan advisory
- H1 drift advisory

## Verification

```
bash -n doc-standardization/scripts/check-doc-naming.sh
bash -n doc-standardization/scripts/run-tests.sh
bash doc-standardization/scripts/run-tests.sh
python3 .claude/skills/skill-evaluator-1.0.0/scripts/eval-skill.py doc-standardization
```

All commands passed on 2026-06-28.

## Revision History

| Date | Score | Notes |
|---|---:|---|
| 2026-05-12 | 91 | Imported from Tiercade and genericized. |
| 2026-05-12 | 89 | Fresh re-eval surfaced link-validator fragility. |
| 2026-05-12 | 99 | Split references, added audit script, hardened link validation. |
| 2026-06-03 | 99 | Added H1 drift check and self-consistency fixes. |
| 2026-06-28 | 100 | Replaced universal filename doctrine with project-local contract discovery, added ADR/dated-record/declared-bundle handling, and added fixture-backed validator tests. |
