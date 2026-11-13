---
description: Gap-sweep finder for /code-review-opencode. Hunts only for defects the first pass missed.
mode: subagent
hidden: false
# Claude Code's Agent tool caps subagent turns at maxTurns. 60 is the
# OpenCode/DeepSeek adaptation; the reference maxTurns is 20. The gap hunt reads
# the diff and the first-pass candidates, so it needs the same headroom as the
# finder before OpenCode's final-step summary.
steps: 60
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
  # `diff` and `diff *` are separate patterns: `git diff*` also matched
  # `git difftool`, which executes an external program.
  - action: shell
    resource: "git -C * diff"
    effect: allow
  - action: shell
    resource: "git -C * diff *"
    effect: allow
  - action: shell
    resource: "git -C * log*"
    effect: allow
  - action: shell
    resource: "git -C * show*"
    effect: allow
  - action: shell
    resource: "git -C * blame*"
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
    resource: "git diff"
    effect: allow
  - action: shell
    resource: "git diff *"
    effect: allow
  - action: shell
    resource: "git log*"
    effect: allow
  - action: shell
    resource: "git show*"
    effect: allow
  - action: shell
    resource: "git blame*"
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
  # Git options that execute a pager, external diff, or textconv filter would
  # turn an allowed read-only command into arbitrary code execution.
  - action: shell
    resource: "*--open-files-in-pager*"
    effect: deny
  - action: shell
    resource: "*difftool*"
    effect: deny
  - action: shell
    resource: "*--ext-diff*"
    effect: deny
  - action: shell
    resource: "*--textconv*"
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
  - action: code_review_candidates
    resource: "*"
    effect: allow
---

You are the final gap-sweep reviewer. Everything already found is listed in
the user message; do not re-derive or re-confirm it. Your only job is to find
defects that are not on that list.

Rules:
- Do not edit files, do not spawn subagents.
- Return only `{"candidates":[...]}`; return an empty array rather than padding.
