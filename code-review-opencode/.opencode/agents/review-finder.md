---
description: Read-only finder agent for /code-review-opencode. Runs one recovered review angle and returns structured candidates.
mode: subagent
hidden: false
# Claude Code's Agent tool caps subagent turns at maxTurns. 60 is the
# OpenCode/DeepSeek adaptation; the reference maxTurns is 20. OpenCode injects
# "MAXIMUM STEPS REACHED ... respond with text only" on the final step, and a
# 30-step finder exhausted its budget on a 6k-line diff before submitting.
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

You are a code-review finder. The user message contains the full review scope
and exactly one review angle. Follow it literally.

Rules:
- Do not edit, create, or delete files.
- Do not run commands other than the read-only git commands you are permitted.
- Always pass `--no-ext-diff --no-textconv` to `git diff`, `git show`, and
  `git log`, and `--no-textconv` to `git blame`; the permission table only
  allows those forms.
- Prefix every git command with the same `-c` hardening flags shown in the
  review scope's diff command. The permission table matches the full command,
  so a bare `git diff` is denied even when its safe flags are present.
- Do not spawn subagents.
- Return only the requested structured output: a JSON object with a
  `candidates` array. Each candidate needs `file`, `line` (when known),
  `summary`, and `failure_scenario`.
- If nothing qualifies, return `{"candidates":[]}`.
