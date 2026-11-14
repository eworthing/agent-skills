/**
 * Branch/ref comparison shared by scope discovery and comment posting.
 *
 * Scope uses it to decide whether a remote-only target names the checked-out
 * branch; posting uses it to decide whether the reviewed diff base is the PR's
 * base. Both must agree on when a remote prefix is meaningful: `origin/main`
 * is `main` on origin, but a local branch named `release/main` is not `main`.
 */

/** Drop a qualified `refs/heads/` or `refs/remotes/` prefix. */
export function normalizeRef(ref: string): string {
  return ref.replace(/^refs\/heads\//, "").replace(/^refs\/remotes\//, "")
}

/**
 * True when two ref names denote the same branch. A `<remote>/<branch>` form
 * matches `<branch>` only when `<remote>` is a real remote name; a local
 * branch such as `release/main` must not be mistaken for `main`.
 */
export function sameRefName(
  left: string,
  right: string,
  remotes: readonly string[] = [],
): boolean {
  const a = normalizeRef(left)
  const b = normalizeRef(right)
  if (a === b) return true
  return remotes.some(
    (remote) =>
      remote.length > 0 && a.startsWith(`${remote}/`) && a.slice(remote.length + 1) === b,
  )
}

/**
 * A PR baseRefName is a short branch name. `release/main` is a different
 * branch even though it ends in `/main`; only a known remote-tracking prefix
 * for the same branch counts. A stale local base at another commit is caught
 * separately by the local-HEAD check in postComments.
 */
export function samePrBase(
  diffBase: string,
  prBase: string,
  remotes: readonly string[] = [],
): boolean {
  return sameRefName(diffBase, prBase, remotes)
}
