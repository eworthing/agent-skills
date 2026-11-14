/**
 * Shell deny patterns shared by the installed permission policy and the
 * runnable diff command renderer. Keeping one list means a path, branch name,
 * or repository root that the policy would reject is also omitted from the
 * command the review prompt advertises.
 */
import { renderPath } from "./finding.ts"

/** Glob resources installed in each review agent's permission table. */
export const SHELL_DENY_RESOURCES = [
  "*--output*",
  "*>*",
  "*;*",
  "*|*",
  "*&&*",
  "*&*",
  "*$(*",
  "*`*",
  "*<(*",
  "*\n*",
  "*--open-files-in-pager*",
  "*difftool*",
  "* --textconv*",
  "* --ext-diff*",
  "*--config-env*",
  "*--paginate*",
  "* -O*",
] as const

/** The literal text behind each `*text*` glob above. */
const DENY_SUBSTRINGS = SHELL_DENY_RESOURCES.map((resource) => resource.slice(1, -1))

/** True when a path, range, or root cannot be placed in a runnable command. */
export function isShellDenied(value: string): boolean {
  // `renderPath` is the shared escaper for every prompt/report surface. If it
  // changes a value, that value is unsafe in a displayed command too.
  if (renderPath(value) !== value) return true
  return DENY_SUBSTRINGS.some((text) => value.includes(text))
}
