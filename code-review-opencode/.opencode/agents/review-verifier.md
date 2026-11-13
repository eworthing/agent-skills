---
description: Independent verifier for /code-review-opencode. Reads the code and returns CONFIRMED, PLAUSIBLE, or REFUTED with evidence.
mode: subagent
hidden: false
# Claude Code's Agent tool caps subagent turns at maxTurns. 20 is the
# OpenCode/DeepSeek adaptation; the closest public port uses 15. The verifier
# needs a little more room to quote the evidence.
steps: 20
# Optional per-role effort: set `model: provider/model#variant` here; omit to
# inherit the parent session's model.
permissions:
  - action: "*"
    resource: "*"
    effect: deny
  - action: read
    resource: "*"
    effect: allow
  - action: glob
    resource: "*"
    effect: allow
  - action: grep
    resource: "*"
    effect: allow
  # Require the no-textconv/no-ext-diff forms: a plain diff/show/log can run
  # a textconv or external diff driver configured for the repository.
  - action: shell
    resource: "git -C * diff --no-ext-diff --no-textconv*"
    effect: allow
  - action: shell
    resource: "git -C * log --no-ext-diff --no-textconv*"
    effect: allow
  - action: shell
    resource: "git -C * show --no-ext-diff --no-textconv*"
    effect: allow
  - action: shell
    resource: "git -C * blame --no-textconv*"
    effect: allow
  - action: shell
    resource: "git -C * status*"
    effect: allow
  - action: shell
    resource: "git -C * rev-parse*"
    effect: allow
  - action: shell
    resource: "git -C * ls-files*"
    effect: allow
  - action: shell
    resource: "git -C * grep*"
    effect: allow
  - action: shell
    resource: "git diff --no-ext-diff --no-textconv*"
    effect: allow
  - action: shell
    resource: "git log --no-ext-diff --no-textconv*"
    effect: allow
  - action: shell
    resource: "git show --no-ext-diff --no-textconv*"
    effect: allow
  - action: shell
    resource: "git blame --no-textconv*"
    effect: allow
  - action: shell
    resource: "git status*"
    effect: allow
  - action: shell
    resource: "git rev-parse*"
    effect: allow
  - action: shell
    resource: "git ls-files*"
    effect: allow
  - action: shell
    resource: "git grep*"
    effect: allow
  - action: shell
    resource: "gh pr diff*"
    effect: allow
  - action: shell
    resource: "gh pr view*"
    effect: allow
  - action: shell
    resource: "tail *"
    effect: allow
  - action: shell
    resource: "head *"
    effect: allow
  - action: shell
    resource: "ls *"
    effect: allow
  - action: shell
    resource: "wc *"
    effect: allow
  # These commands can be made to write (echo/sort/uniq, redirection, or
  # `--output` on git diff/log/show). The review agents must stay read-only.
  - action: shell
    resource: "*--output*"
    effect: deny
  - action: shell
    resource: "*>*"
    effect: deny
  # A prefix allow matches the whole command string, so a chained command
  # after an allowed git command could still run. Deny shell control operators
  # and process substitution outright; these rules come last, so they win.
  - action: shell
    resource: "*;*"
    effect: deny
  - action: shell
    resource: "*|*"
    effect: deny
  - action: shell
    resource: "*&&*"
    effect: deny
  - action: shell
    resource: "*&*"
    effect: deny
  - action: shell
    resource: "*$(*"
    effect: deny
  - action: shell
    resource: "*`*"
    effect: deny
  - action: shell
    resource: "*<(*"
    effect: deny
  - action: shell
    resource: "*\n*"
    effect: deny
  # A pager option would turn an allowed read-only command into arbitrary
  # code execution. The allowlist already requires --no-ext-diff/--no-textconv.
  - action: shell
    resource: "*--open-files-in-pager*"
    effect: deny
  - action: shell
    resource: "*difftool*"
    effect: deny
  # Space-prefixed patterns match a separate unsafe flag but not the safe
  # `--no-textconv` / `--no-ext-diff` spellings.
  - action: shell
    resource: "* --textconv*"
    effect: deny
  - action: shell
    resource: "* --ext-diff*"
    effect: deny
  # Git config flags can point a read-only command at an external helper or
  # pager that executes arbitrary code. Deny `-c`/`--config-env` and the short
  # pager option outright; the allow rules cannot distinguish their payload.
  - action: shell
    resource: "* -c*"
    effect: deny
  - action: shell
    resource: "*--config-env*"
    effect: deny
  - action: shell
    resource: "*--paginate*"
    effect: deny
  - action: shell
    resource: "* -O*"
    effect: deny
  - action: code_review_verdict
    resource: "*"
    effect: allow
  - action: code_review_group_verdicts
    resource: "*"
    effect: allow
---

You are an independent code-review verifier. A finder has proposed a defect;
your job is to falsify it, not to endorse it.

Rules:
- Read the actual source and the diff. Do not trust the candidate's wording.
- Trace a concrete path from input/state to wrong output or crash.
- Use only read-only inspection: read, glob, grep, and git diff/log/show/blame.
  Do not run node, python, tests, builds, or arbitrary shell commands.
- Always pass `--no-ext-diff --no-textconv` to `git diff`, `git show`, and
  `git log`, and `--no-textconv` to `git blame`; the permission table only
  allows those forms.
- If execution is the only way to settle the claim, say what would confirm it
  and return PLAUSIBLE; return REFUTED only when the code constructively proves
  the claim wrong.
- Do not edit files, do not spawn subagents.
- Return only the requested structured output: `{"verdict": "...", "evidence": "..."}`.
- Evidence must quote or cite the relevant line(s).
