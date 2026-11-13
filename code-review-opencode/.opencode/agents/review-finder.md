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
  # The plugin setup installs the full read-only policy from
  # agent-policy.ts. This fallback keeps the agent read-only even if
  # the transform is unavailable.
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
  - action: code_review_candidates
    resource: "*"
    effect: allow
  # The fallback still allows the one read-only command the review prompt
  # displays when a diff is truncated; the full policy installed by the plugin
  # adds the history commands. The deny list keeps this read-only.
  - action: shell
    resource: "git -c core.hooksPath=/dev/null -c core.fsmonitor= -c core.askPass= -c core.quotePath=false diff*"
    effect: allow
  - action: shell
    resource: "git -C * -c core.hooksPath=/dev/null -c core.fsmonitor= -c core.askPass= -c core.quotePath=false diff*"
    effect: allow
  - action: shell
    resource: "gh pr diff*"
    effect: allow
  - action: shell
    resource: "*--output*"
    effect: deny
  - action: shell
    resource: "*>*"
    effect: deny
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
  - action: shell
    resource: "*--open-files-in-pager*"
    effect: deny
  - action: shell
    resource: "*difftool*"
    effect: deny
  - action: shell
    resource: "* --textconv*"
    effect: deny
  - action: shell
    resource: "* --ext-diff*"
    effect: deny

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
