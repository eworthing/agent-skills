# doc-standardization Evaluation

**Date:** 2026-07-04
**Evaluator:** Codex GPT-5
**Skill version:** Flag-driven local-contract discovery (agent passes discovered exceptions/vocab to the validator)
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
    PASS Python scripts parse without errors   # vacuous: this skill ships zero Python (Bash-only)
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
  SKILL.md                          166 lines
  EVAL.md                           this file
  references/
    conventions.md                   90 lines
    error-taxonomy.md                22 lines
    regex-recipes.md                114 lines
  scripts/
    check-doc-naming.sh             357 lines, executable (Bash 3.2 / BSD-compatible)
    run-tests.sh                     77 lines, executable
  tests/
    fixtures/                        15 fixture docs trees
```

The skill is **Bash-only** — there are no Python scripts, so the automated
"Python scripts parse" check above passes vacuously.

## Current Behavior

- Discovers project-local docs taxonomy from `docs/README.md` or the nearest
  index instead of imposing a universal directory tree.
- Keeps default grammar for curated docs: `<topic>-<type>-<status>.md`.
- Recognizes dated records: `<topic>-<type>-YYYY-MM-DD.md`.
- Recognizes ADR numbering: `adr/NNNN-topic.md`.
- Treats generic `vendor`/`archive`/`_archive` bundle paths as declared-style
  filename exceptions while still validating their links.
- Honors project-local contracts the agent discovers in the README via flags:
  `--bundle-glob` (extra declared bundles), `--allow` (extra basenames),
  `--types` / `--states` (extend the grammar vocab). Unknown flags and missing
  flag values exit `2`.
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
- undeclared custom bundle: blocked bare, clean with `--bundle-glob`
- custom type vocab: blocked bare, clean with `--types`
- multi-word H1 drift caught (full topic phrase, not just first token)
- clean multi-word H1 (no false positive)

## Verification

```
bash -n doc-standardization/scripts/check-doc-naming.sh
bash -n doc-standardization/scripts/run-tests.sh
bash doc-standardization/scripts/run-tests.sh
python3 .claude/skills/skill-evaluator-1.0.0/scripts/eval-skill.py doc-standardization
```

All commands passed on 2026-07-04 (suite also re-run under `/bin/bash`
3.2.57 for BSD-userland portability).

## Revision History

| Date | Score | Notes |
|---|---:|---|
| 2026-05-12 | 91 | Imported from Tiercade and genericized. |
| 2026-05-12 | 89 | Fresh re-eval surfaced link-validator fragility. |
| 2026-05-12 | 99 | Split references, added audit script, hardened link validation. |
| 2026-06-03 | 99 | Added H1 drift check and self-consistency fixes. |
| 2026-06-28 | 100 | Replaced universal filename doctrine with project-local contract discovery, added ADR/dated-record/declared-bundle handling, and added fixture-backed validator tests. |
| 2026-07-04 | 100 | Closed the agent↔script contract gap: `--bundle-glob`/`--allow`/`--types`/`--states` flags let the agent pass discovered exceptions/vocab to the validator; removed the leaked `code-flow` hardcode; H1-drift now matches the full topic phrase; 6 new fixture assertions; corrected the vacuous "Python scripts parse" claim (skill is Bash-only); removed stray `.DS_Store`. Peer-reviewed (Codex gpt-5.4-mini, APPROVED round 3). |
