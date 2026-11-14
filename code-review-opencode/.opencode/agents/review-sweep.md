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
  - action: "read"
    resource: "*"
    effect: allow
  - action: "glob"
    resource: "*"
    effect: allow
  - action: "grep"
    resource: "*"
    effect: allow
  - action: "shell"
    resource: "git -c core.hooksPath=/dev/null -c core.fsmonitor= -c core.askPass= -c core.quotePath=false diff --no-ext-diff --no-textconv*"
    effect: allow
  - action: "shell"
    resource: "git -C * -c core.hooksPath=/dev/null -c core.fsmonitor= -c core.askPass= -c core.quotePath=false diff --no-ext-diff --no-textconv*"
    effect: allow
  - action: "shell"
    resource: "git -c core.hooksPath=/dev/null -c core.fsmonitor= -c core.askPass= -c core.quotePath=false log --no-ext-diff --no-textconv*"
    effect: allow
  - action: "shell"
    resource: "git -C * -c core.hooksPath=/dev/null -c core.fsmonitor= -c core.askPass= -c core.quotePath=false log --no-ext-diff --no-textconv*"
    effect: allow
  - action: "shell"
    resource: "git -c core.hooksPath=/dev/null -c core.fsmonitor= -c core.askPass= -c core.quotePath=false show --no-ext-diff --no-textconv*"
    effect: allow
  - action: "shell"
    resource: "git -C * -c core.hooksPath=/dev/null -c core.fsmonitor= -c core.askPass= -c core.quotePath=false show --no-ext-diff --no-textconv*"
    effect: allow
  - action: "shell"
    resource: "git -c core.hooksPath=/dev/null -c core.fsmonitor= -c core.askPass= -c core.quotePath=false blame --no-textconv*"
    effect: allow
  - action: "shell"
    resource: "git -C * -c core.hooksPath=/dev/null -c core.fsmonitor= -c core.askPass= -c core.quotePath=false blame --no-textconv*"
    effect: allow
  - action: "shell"
    resource: "git -c core.hooksPath=/dev/null -c core.fsmonitor= -c core.askPass= -c core.quotePath=false status*"
    effect: allow
  - action: "shell"
    resource: "git -C * -c core.hooksPath=/dev/null -c core.fsmonitor= -c core.askPass= -c core.quotePath=false status*"
    effect: allow
  - action: "shell"
    resource: "git -c core.hooksPath=/dev/null -c core.fsmonitor= -c core.askPass= -c core.quotePath=false rev-parse*"
    effect: allow
  - action: "shell"
    resource: "git -C * -c core.hooksPath=/dev/null -c core.fsmonitor= -c core.askPass= -c core.quotePath=false rev-parse*"
    effect: allow
  - action: "shell"
    resource: "git -c core.hooksPath=/dev/null -c core.fsmonitor= -c core.askPass= -c core.quotePath=false ls-files*"
    effect: allow
  - action: "shell"
    resource: "git -C * -c core.hooksPath=/dev/null -c core.fsmonitor= -c core.askPass= -c core.quotePath=false ls-files*"
    effect: allow
  - action: "shell"
    resource: "git -c core.hooksPath=/dev/null -c core.fsmonitor= -c core.askPass= -c core.quotePath=false grep*"
    effect: allow
  - action: "shell"
    resource: "git -C * -c core.hooksPath=/dev/null -c core.fsmonitor= -c core.askPass= -c core.quotePath=false grep*"
    effect: allow
  - action: "shell"
    resource: "gh pr diff*"
    effect: allow
  - action: "shell"
    resource: "gh pr view*"
    effect: allow
  - action: "shell"
    resource: "tail *"
    effect: allow
  - action: "shell"
    resource: "head *"
    effect: allow
  - action: "shell"
    resource: "ls *"
    effect: allow
  - action: "shell"
    resource: "wc *"
    effect: allow
  - action: "shell"
    resource: "*--output*"
    effect: deny
  - action: "shell"
    resource: "*>*"
    effect: deny
  - action: "shell"
    resource: "*;*"
    effect: deny
  - action: "shell"
    resource: "*|*"
    effect: deny
  - action: "shell"
    resource: "*&&*"
    effect: deny
  - action: "shell"
    resource: "*&*"
    effect: deny
  - action: "shell"
    resource: "*$(*"
    effect: deny
  - action: "shell"
    resource: "*`*"
    effect: deny
  - action: "shell"
    resource: "*<(*"
    effect: deny
  - action: "shell"
    resource: "*\n*"
    effect: deny
  - action: "shell"
    resource: "*--open-files-in-pager*"
    effect: deny
  - action: "shell"
    resource: "*difftool*"
    effect: deny
  - action: "shell"
    resource: "* --textconv*"
    effect: deny
  - action: "shell"
    resource: "* --ext-diff*"
    effect: deny
  - action: "shell"
    resource: "*--config-env*"
    effect: deny
  - action: "shell"
    resource: "*--paginate*"
    effect: deny
  - action: "shell"
    resource: "* -O*"
    effect: deny
  - action: "code_review_candidates"
    resource: "*"
    effect: allow

---

You are the final gap-sweep reviewer. Everything already found is listed in
the user message; do not re-derive or re-confirm it. Your only job is to find
defects that are not on that list.

Rules:
- Do not edit files, do not spawn subagents.
- Always pass `--no-ext-diff --no-textconv` to `git diff`, `git show`, and
  `git log`, and `--no-textconv` to `git blame`; the permission table only
  allows those forms.
- Prefix every git command with the same `-c` hardening flags shown in the
  review scope's diff command. The permission table matches the full command,
  so a bare `git diff` is denied even when its safe flags are present.
- Return only `{"candidates":[...]}`; return an empty array rather than padding.
