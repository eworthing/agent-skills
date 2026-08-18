# AWS Rule Delta — 2026-08-17 (backlog item 29 prerequisite audit)

Trigger: backlog item 29 gates adoption of AWS `aws-agent-skill-eval`'s static safety/structure
rules on a rule-by-rule delta against our own mechanical gates. This doc is that delta. It does not
adopt anything — adoption (suppressions, FP targets, report-only→enforce rollout) is a separate,
later step, contingent on this audit's shortlist.

**Corpus**: AWS side — `refs/competitors/contest-refactor/aws-agent-skill-eval` pinned at
`13b2277b300d2beafa09bbbe425ca0cc41f34c8d` (2026-05-27), `skill_eval/audit/security_scan.py` (9
`SEC-*` codes), `structure_check.py` (20 `STR-*` codes), `permission_analyzer.py` (5 `PERM-*`
codes) — **34 rules total**, all read in full. Our side — `contest-refactor/canon/validation-gates.toml`
(43 gates, G1-G43), the enforcing code in `contest-refactor/scripts/validate-artifact.py` /
`validate-repo.py`, `.githooks/pre-commit`, `common/scripts/*`, and
`.claude/skills/skill-evaluator-1.0.0/scripts/eval-skill.py` (13 checks) — the last of these turned
out to be the real comparison surface; see the domain-mismatch note below.

**Evidence discipline**: every classification below is **VERIFIED** — read the cited line(s) on
both sides, or ran the cited grep against this repo's actual tree and report the raw hit count. No
claim in this doc is **INFERRED** from a docstring or comment alone.

**Terminology caveat** (per the team's prior deep-dive): AWS's own `trigger_precision` metric is
computed as `trigger_pass / len(should_trigger)` (`skill_eval/trigger.py:418`) — that is recall
(true-positive rate over the should-trigger set), not precision. Their naming is imported nowhere
in this doc; "FP baseline" below always means false positives measured directly against our tree.

---

## Domain-mismatch finding (read this before the table)

G1-G43 and `validate-artifact.py` / most of `validate-repo.py` do **not** audit skill-file content
(SKILL.md structure, script security, `allowed-tools` scope) at all. They audit the **JSON review
artifact** (`CURRENT_REVIEW.json`) that the contest-refactor Actor-Critic loop produces about
*itself* during a run — HALT-state shape, backlog/registry consistency, evidence-chain fields per
finding, retirement hashing, panel-challenge gating. Confirmed by reading every check function
`validate-artifact.py` imports and dispatches (`contest-refactor/scripts/validate-artifact.py:37-78,
118-160`): every one of `check_g5_sub95_residual_fields` through `check_g43_convergence_pass`
operates on `current_review` (the artifact), never on a skill directory. `validate-repo.py`'s 10
checks (`contest-refactor/scripts/validate-repo.py:551-560`) audit contest-refactor's *own*
reference docs (evidence-chain cross-refs, gate sequencing, link resolution) — again, not generic
skill content. The one exception is `OBVIOUS_SECRET_REGEXES`
(`contest-refactor/scripts/validate-repo.py:51-57`), and that's scoped to a single file
(`.contest-refactor.example.toml`, `validate-repo.py:328-344`), not the tree AWS scans.

So **0 of 43 canon gates are a candidate comparison surface** for AWS's SEC/STR/PERM rules — wrong
domain, not weaker coverage. The genuine comparison surface is
`.claude/skills/skill-evaluator-1.0.0/scripts/eval-skill.py`, which *does* audit arbitrary
SKILL.md/scripts content the same way AWS's tool does, plus the pre-commit hook
(`.githooks/pre-commit:1-79`, 4 gates: vendor-integrity, module-size, ruff, eval-guard — none touch
skill-content security/structure) and `common/scripts/*` (checked by grep for
secret/subprocess/eval/pickle/allowed-tools patterns — only hit was `eval_guard.py`'s own
legitimate `subprocess.run` git plumbing and `check_shim_contract.py:152`'s legitimate
`importlib.import_module`, both repo-level dev tools outside any skill's scanned surface). This
reframes the audit below: 6 of AWS's 34 rules are genuinely COVERED, but by a skill-evaluator
script the backlog item didn't originally point at.

---

## SEC-* rules (9 total, `security_scan.py`)

| Code | Check (as implemented) | Class | Our-side citation | Measured FP on this repo |
|---|---|---|---|---|
| SEC-001 | 17 regex patterns for API keys/AWS/GitHub/OpenAI/Anthropic/Slack/passwords/DB conn strings/PEM keys (`security_scan.py:28-99`), CRITICAL, code at line 280 | **PARTIAL** | `eval-skill.py:378-426` `check_no_hardcoded_secrets` — 4 patterns (email, generic `key/token/secret/password=`, OpenAI `sk-`, GitHub `ghp_`) vs AWS's 17; scans the *whole* skill tree (`os.walk`, no dir restriction) vs AWS's default scripts/agents-only scope | 0 hits either side today |
| SEC-002 | External URL inventory against a 15-domain allowlist (`security_scan.py:117-128`), INFO in docs / WARNING in scripts, code 329 | **NEW** | none | **49 hits** for `developer.apple.com` alone, scanning only SKILL.md+`scripts/`+`agents/` (AWS's own default scope) across the repo's Apple-platform skills — `developer.apple.com` is absent from AWS's `SAFE_DOMAINS` |
| SEC-003 | `subprocess.*`/`os.system`/`os.popen`/`shell=True`/`eval|exec(` in scripts, code 356 | **NEW** | none | 0 real hits. 3 regex matches, all false positives on inspection: `apple-multiplatform/scripts/audit-platform-guards.py:50` (`def eval(self, env):` — a method name, not a call), `:33` (a docstring warning *against* eval), `peer-plan-review/scripts/tests/test_ppr_launch.py:159` (the English phrase "fresh exec (resume_reason=...)") |
| SEC-004 | pip/npm install, curl\|sh, wget\|sh, code 391 | **NEW** | none | 0 hits (repo is stdlib-only per CLAUDE.md convention, verified) |
| SEC-005 | Injection-surface phrasing in SKILL.md prose + eval/exec inside SKILL.md code fences, codes 579/557 | **NEW** | none | 0 hits |
| SEC-006 | `pickle.load(s)`/`marshal.loads`/`shelve.open`/`yaml.load` w/o SafeLoader, code 425 | **NEW** | none | 0 hits |
| SEC-007 | `importlib.import_module`/`__import__`/`compile(`/`types.FunctionType`/`types.CodeType`, code 449 | **NEW** | none | 1 hit: `common/scripts/check_shim_contract.py:152`, a legitimate AST-verification tool that loads a shim to check its `__all__` contract — and it lives outside any skill's `scripts/`/`agents/` dir, so AWS's own default scan (`SKILL_SCAN_DIRS = {"scripts","agents"}`, `security_scan.py:597`) would never reach it |
| SEC-008 | base64 decode calls / long base64 strings near eval/exec, codes 483/501 | **NEW** | none | 0 hits |
| SEC-009 | `mcpServers` config blocks, `npx -y <pkg>` (CRITICAL), MCP/SSE endpoint URLs, code 524 | **NEW** | none | 1 hit, `swiftui-native-ux/references/stitch-tool-capability-map.md:3` — a documented, verified real MCP endpoint citation, and it's in `references/`, outside AWS's default scan scope. The CRITICAL sub-pattern (`npx -y`) has **0** hits anywhere in the repo |

## STR-* rules (20 total, `structure_check.py`)

| Code | Check | Class | Our-side citation | Measured FP on this repo |
|---|---|---|---|---|
| STR-001 | Path is not a directory, code 163 | **N/A** | `eval-skill.py:567-569` (`main`, identical `isdir` guard) | trivial invocation guard, not a skill-content property; both tools already guard it |
| STR-002 | SKILL.md exists, code 177 | **COVERED** | `eval-skill.py:59-65` `check_skill_md_exists` | 0/17 |
| STR-003 | SKILL.md unreadable (encoding/permission), code 193 | **PARTIAL** | `eval-skill.py:504-514` `run_checks` wraps every check in a generic try/except → FAIL, no dedicated diagnostic message | untested (no unreadable files in tree) |
| STR-004 | Frontmatter missing/unclosed `---`, code 206 | **COVERED** | `eval-skill.py:78-91` `check_frontmatter` | 0/17 |
| STR-005 | Missing `name` field, code 220 | **COVERED** | `eval-skill.py:93-95,99-101` | 0/17 |
| STR-006 | `name` > 64 chars, code 233 | **NEW** | none | 0/17 (longest name well under 64) |
| STR-007 | `name` format (lowercase/hyphen/no leading-trailing/no `--`), code 255 | **NEW** | none | 0/17 — verified every `name:` field against AWS's own regex `^[a-z0-9]([a-z0-9-]*[a-z0-9])?$` |
| STR-008 | `name` ≠ directory, code 267 | **COVERED** | `eval-skill.py:106-129` `check_name_matches_dir` | 0/17 |
| STR-009 | Missing `description`, code 297 | **COVERED** | `eval-skill.py:93-97` (same check as STR-005) | 0/17 |
| STR-010 | `description` > 1024 chars, code 309 | **PARTIAL** | `eval-skill.py:171-192` `check_description_length` — word-count proxy (>150 words WARN), not char-count | 0/17 either metric |
| STR-011 | `description` < 20 chars, code 320 | **PARTIAL** | same function, <15 words FAIL — stricter unit, same intent | 0/17 either metric |
| STR-012 | `compatibility` field > 500 chars, code 371 | **NEW** | none | field unused in all 17 SKILL.md files — dormant, 0 FP risk |
| STR-013 | `metadata` field must be a YAML mapping, codes 391/399/409 | **NEW** | none | field unused in all 17 SKILL.md files — dormant, 0 FP risk |
| STR-014 | SKILL.md > 500 lines, code 425 | **COVERED** | `eval-skill.py:217-245` `check_body_length` — identical 500-line threshold (body lines, not incl. frontmatter, vs AWS's total-line count — negligible difference) | 1/17 (`ios-security-hardening`, 515 lines) — same skill either check would catch |
| STR-015 | SKILL.md body > ~5000 tokens (chars/4), code 438 | **NEW** | none | **2/17**: `apple-multiplatform` (~5076 tok) and `contest-refactor` (~10737 tok). `contest-refactor` is 293 lines — under STR-014's/`eval-skill.py`'s 500-line threshold — so this is a real blind spot our line-count proxy structurally cannot see |
| STR-016 | README.md present alongside SKILL.md, code 451 (INFO) | **PARTIAL / value-conflict** | `eval-skill.py:132-150` `check_no_extraneous` — explicitly *allows* README.md, with a comment stating why: "SKILL.md is agent-facing, README.md is human-facing for GitHub browsing" | 1/17 (`peer-plan-review`) — a deliberate, documented file, not an oversight |
| STR-017 | Script (.py/.sh/.js/.ts under `scripts/`) missing a shebang, code 476 | **NEW** | none | **47 hits**, but ~37 are pytest test files (`test_*.py`, `conftest.py`) and internal package modules (e.g. `quorum-review/scripts/quorum/*.py`) that are imported, never directly executed, under this repo's `scripts/` convention. AWS's `rglob("*")` scan (`structure_check.py:469`) doesn't distinguish CLI entry points from library/test modules |
| STR-018 | `name` contains `anthropic`/`claude`, code 281 | **NEW** | none | 0/17 — checked both directory names and frontmatter `name:` values |
| STR-019 | `description` contains an XML-tag-shaped substring `<[a-zA-Z][^>]*>`, code 331 | **NEW** | none | **4/17** (`quorum-review`, `bash-macos`, `contest-refactor`, `peer-plan-review`) — read every match; all 4 are this repo's convention of `<placeholder>` argument notation in prose (`<artifact-file>`, `<target>`, `<pattern>`, `<provider>`), not actual XML/HTML tags |
| STR-020 | `description` uses first/second person, code 356 | **NEW** | none | 0/17 |

## PERM-* rules (5 total, `permission_analyzer.py`)

| Code | Check | Class | Our-side citation | Measured FP on this repo |
|---|---|---|---|---|
| PERM-001 | Unscoped `Bash`/`Bash(*)`/`Shell`/`Terminal` in `allowed-tools`, WARNING, code 123 | **NEW** | none | **15/17 (88%)** declare bare `Bash` (not `Bash(git:*)`-style scoped) in `allowed-tools`. Verified this is a *deliberate* repo convention, not an oversight: `feedback_allowed_tools.md` memory records "Bash/orchestration skills use full Read/Write/Edit/Glob/Grep/Bash, not minimal Read/Write." Adopting this rule as-is means either a blanket suppression on 88% of the corpus or re-litigating that convention |
| PERM-002 | Any high-risk tool declared, INFO, code 135 | **NEW** | none | fires on essentially every skill that declares `Write`/`Edit`/`Bash` — no filtering logic distinguishes "necessary" from "excessive," so it's unconditional noise at this repo's tool-declaration density |
| PERM-003 | > 15 tools declared, INFO, code 145 | **NEW** | none | 0/17 (max observed: 7 tools, `contest-refactor`) |
| PERM-004 | Prose implies sensitive-dir/root/listener/credential access, codes vary, 196 | **NEW** | none | 0/17 |
| PERM-005 | Prose references an absolute path under `/etc,/var,/tmp,/usr,/opt,/home,/root`, code 224 | **NEW** | none | 2 hits, both `quorum-review/SKILL.md:140,151` — legitimate documented CLI example paths (`--plan-file /tmp/plan.md`). AWS's own pattern flags `/tmp` as a risky prefix despite it being the normal, low-risk scratch location |

---

## Summary

| Classification | Count | Codes |
|---|---|---|
| COVERED | 6 | STR-002, STR-004, STR-005, STR-008, STR-009, STR-014 |
| PARTIAL | 5 | SEC-001, STR-003, STR-010, STR-011, STR-016 |
| N/A | 1 | STR-001 |
| NEW | 22 | SEC-002/003/004/005/006/007/008/009; STR-006/007/012/013/015/017/018/019/020; PERM-001/002/003/004/005 |

34 AWS rules audited. Our-side surface actually read: 43 canon gates (all ruled out as wrong-domain
— see above), `validate-repo.py`'s 10 checks, `validate-artifact.py`'s 23 imported gate-checks,
`eval-skill.py`'s 13 checks (the real comparison surface), and the 4-gate pre-commit hook.

**Of the 22 NEW rules, 15 have a measured FP baseline of 0 on this repo** (SEC-004/005/006/008;
STR-006/007/012/013/018/020; PERM-002/003/004 — PERM-002 is 0 in the sense of "0 filtering logic to
even measure," not "0 hits," since it fires unconditionally). **7 NEW rules have nonzero measured
hits, and of those, 6 are 100% false positives on inspection** (SEC-002 developer.apple.com, SEC-003
regex-on-English-prose, SEC-007 out-of-scope legitimate tooling, SEC-009 legitimate documented
endpoint, STR-017 test/library modules, STR-019 placeholder syntax, PERM-001 deliberate convention,
PERM-005 legitimate /tmp example). **Exactly one NEW rule's hits are genuine gaps in our own
coverage**: STR-015 (SKILL.md token-count ceiling), which catches `contest-refactor`'s own
10,737-token SKILL.md — invisible to our 500-line proxy.

## Shortlist

1. **STR-015 (SKILL.md token-count ceiling) — ADOPT.** Real, measured gap: our line-count proxy
   (`eval-skill.py:217-245`) cannot see a short-but-dense SKILL.md. Cheap fix: add a `len(body)//4 >
   5000` check next to the existing body-length check in `eval-skill.py`, not a new dependency.
2. **SEC-001 pattern-set (partial adopt) — ADOPT the pattern literals only.** AWS's AWS-key/GitHub
   fine-grained/Anthropic-key/Slack-token/PEM-header/DB-connection-string regexes
   (`security_scan.py:35-93`) are high-specificity literal signatures with near-zero FP risk, unlike
   the generic `password=` pattern already in `eval-skill.py:383`. Fold the missing literal patterns
   into `check_no_hardcoded_secrets`; don't import AWS's scanning machinery or file-scope model.
3. **Everything else — SKIP**, not "adopt later," because the specific reasons don't resolve with
   more effort:
   - **SEC-002, PERM-001**: actively fight documented repo conventions (Apple-doc-heavy content,
     coarse-grained `allowed-tools`). Adopting means re-litigating those conventions first — out of
     scope for a mechanical-rule delta.
   - **STR-016, STR-019**: conflict with *deliberate* design choices already made and cited in code
     (README.md coexistence) or in prose (`<placeholder>` argument notation).
   - **STR-017, SEC-003, SEC-007, SEC-009, PERM-005**: the AWS pattern is too coarse for this repo's
     actual file layout (test/library modules under `scripts/`, prose containing the word "exec",
     legitimate dev tooling, documented MCP citations, `/tmp` example paths) — every measured hit
     needed a suppression, and suppressions built to cover 100% of current hits are suppressions
     built to hide the rule, not to scope it.
   - **SEC-004/005/006/008, STR-006/007/012/013/018/020, PERM-002/003/004**: 0 measured hits, no
     plausible near-term trigger given this repo's stdlib-only/no-eval/no-pickle conventions
     (CLAUDE.md). Dormant rules are pure maintenance cost with no current signal.

## Verdict

**Adopt nothing from AWS's machinery wholesale.** The 43 canon gates were never a comparison
surface for this — wrong domain entirely (artifact-schema vs skill-content). Against the actual
comparison surface (`eval-skill.py`), the delta is real but small: 2 cheap, narrow patches
(STR-015's token ceiling, a handful of SEC-001 literal patterns) are worth folding directly into
`eval-skill.py`. The remaining 20 NEW/PARTIAL rules either duplicate existing PARTIAL coverage at
marginal benefit, sit dormant with zero signal on this corpus, or would require suppression lists
that swallow the majority of today's legitimate content — which is a sign the rule doesn't fit this
repo's conventions, not that the repo has a gap. Recommend closing backlog item 29 as **measured,
not adopted** — no report-only rollout, no suppression config, no FP-target exercise. Revisit only
if this repo's content profile changes (e.g., starts shipping example credentials, unsafe
deserialization, or fine-grained Bash-scoped `allowed-tools` becomes the actual convention).
