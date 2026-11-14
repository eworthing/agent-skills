/**
 * Shell deny patterns shared by the installed permission policy and the
 * runnable diff command renderer. Keeping one list means a path, branch name,
 * or repository root that the policy would reject is also omitted from the
 * command the review prompt advertises.
 */

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

/**
 * Control characters `renderPath` rewrites; a path with one is unsafe even
 * though it is not a literal substring in the glob list.
 */
const CONTROL_CHARS = /[\n\r\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u2028\u2029]/

/** The literal text behind each `*text*` glob above. */
const DENY_SUBSTRINGS = SHELL_DENY_RESOURCES.map((resource) => resource.slice(1, -1))

/** True when a path, range, or root cannot be placed in a runnable command. */
export function isShellDenied(value: string): boolean {
  if (CONTROL_CHARS.test(value)) return true
  return DENY_SUBSTRINGS.some((text) => value.includes(text))
}
