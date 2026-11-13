/**
 * Optional --comment posting.
 *
 * GitHub PR -> one inline review comment per finding (gh api). GitLab MR
 * support is out of scope for this port; the prompt corpus still documents the
 * reference's GitLab path, but the host path reports that --comment was
 * ignored on a non-GitHub remote.
 */
import type { EngineResult } from "./engine.ts"
import type { Scope } from "./scope.ts"
import { defaultExec, diffSideMap, type Exec, type ExecOptions, type ExecResult } from "./scope.ts"
import { mapLimit } from "./concurrency.ts"
import { envInt, lineOf, pluralWord } from "./finding.ts"

export type Host = "github" | "gitlab" | "other"

export type CommentDeps = {
  cwd: string
  scope: Scope
  result: EngineResult
  log?: (message: string) => void
  /** Injected for tests; defaults to the real git/gh runner. */
  exec?: Exec
  /** Skip the remote lookup when the caller already resolved the host. */
  host?: Host
  /** GitHub Enterprise hostname, when the caller already resolved it. */
  githubHostname?: string
  /** Cancellation for the remote lookup and posting calls. */
  signal?: AbortSignal
  /** Inline comments in flight at once. */
  concurrency?: number
  /** Per-call timeout; unset by default so a slow GitHub enterprise responds. */
  timeoutMs?: number
}

export function buildGitHubCommentArgs(opts: {
  owner: string
  repo: string
  pr: number
  commit: string
  path: string
  line: number
  body: string
  /** LEFT anchors a comment to a line deleted by the PR; RIGHT to the head file. */
  side?: "RIGHT" | "LEFT"
  /** GitHub Enterprise hostname; omitted for github.com. */
  hostname?: string
}): string[] {
  return [
    "gh",
    "api",
    ...(opts.hostname && opts.hostname.toLowerCase() !== "github.com"
      ? ["--hostname", opts.hostname]
      : []),
    `repos/${opts.owner}/${opts.repo}/pulls/${opts.pr}/comments`,
    "-f",
    `body=${opts.body}`,
    "-f",
    `commit_id=${opts.commit}`,
    "-f",
    `path=${opts.path}`,
    "-F",
    `line=${opts.line}`,
    "-f",
    `side=${opts.side ?? "RIGHT"}`,
  ]
}

export function commentBody(finding: { summary: string; failure_scenario: string }): string {
  return `${finding.summary}\n\nFailure scenario: ${finding.failure_scenario}`
}

/** Hostname from a PR URL, including GitHub Enterprise instances. */
function hostFromPrUrl(value: string): string | undefined {
  try {
    return new URL(value.trim()).hostname || undefined
  } catch {
    return undefined
  }
}

/** `owner/repo` from a PR URL; the PR URL always names the base repository. */
function repoFromPrUrl(value: string): string | undefined {
  try {
    const url = new URL(value.trim())
    const parts = url.pathname.split("/").filter(Boolean)
    // The PR marker is normally at index 2, but a GitHub Enterprise instance
    // can serve repositories under a path prefix. Locate the marker instead of
    // assuming a fixed depth.
    const pull = parts.lastIndexOf("pull")
    if (pull >= 2 && parts[pull - 2] && parts[pull - 1]) {
      return `${parts[pull - 2]}/${parts[pull - 1]}`
    }
  } catch {
    /* not a URL */
  }
  return undefined
}

/**
 * Match the host, not any substring of the repository path: a GitHub repo
 * named "gitlab-migration-tool" is still a GitHub repo.
 */
export function isGitHubRemote(url: string): boolean {
  return /(^|@|\/\/)github\.com[:/]/i.test(url)
}

export function isGitLabRemote(url: string): boolean {
  // Match `gitlab` as a host label, not a prefix of an arbitrary hostname:
  // `gitlab-migration-tool.corp.example` is not GitLab.
  return /(^|@|\/\/)gitlab(\.[^/]*)?[:/]/i.test(url)
}

export function hostFromRemote(url: string): Host {
  if (isGitHubRemote(url)) return "github"
  if (isGitLabRemote(url)) return "gitlab"
  return "other"
}

/** Hostname from an scp-like (`git@host:org/repo`) or URL remote. */
function remoteHostname(url: string): string | undefined {
  const scp = url.match(/^[^@/\s]+@([^:/\s]+):/)
  if (scp) return scp[1]
  try {
    return new URL(url).hostname || undefined
  } catch {
    return undefined
  }
}

export type HostDetails = {
  host: Host
  /** The origin hostname, including github.com, so callers do not re-read the
   *  remote to learn it. */
  hostname?: string
}

export async function detectHostDetails(
  cwd: string,
  exec: Exec = defaultExec,
  opts?: ExecOptions,
): Promise<HostDetails> {
  const remote = await exec(["git", "remote", "get-url", "origin"], cwd, opts)
  if (remote.code !== 0) return { host: "other" }
  const url = remote.stdout.trim()
  const host = hostFromRemote(url)
  const hostname = remoteHostname(url)
  if (host !== "other") {
    return { host, ...(hostname ? { hostname } : {}) }
  }
  // GitHub Enterprise uses an arbitrary hostname, so the URL alone cannot
  // identify it. Ask gh whether it is authenticated to that host; a plain
  // non-GitHub remote fails this probe and stays "other".
  if (!hostname) return { host: "other" }
  const auth = await exec(["gh", "auth", "status", "--hostname", hostname], cwd, opts)
  return auth.code === 0 ? { host: "github", ...(hostname ? { hostname } : {}) } : { host: "other" }
}

export async function detectHost(
  cwd: string,
  exec: Exec = defaultExec,
  opts?: ExecOptions,
): Promise<Host> {
  return (await detectHostDetails(cwd, exec, opts)).host
}

/**
 * A numeric target sets `scope.pr`; a checked-out PR branch does not. Resolve
 * the branch's PR once so `--comment` works in both cases instead of silently
 * doing nothing.
 */
export type PrInfo = {
  number: number
  headRefOid?: string
  baseRefName?: string
  baseRefOid?: string
}

/** Parse `gh pr view --json number,headRefOid,baseRefName,baseRefOid`; tolerate a bare number. */
function parsePrInfo(result: ExecResult): PrInfo | undefined {
  if (result.code !== 0) return undefined
  try {
    const parsed = JSON.parse(result.stdout) as unknown
    const data =
      parsed && typeof parsed === "object" ? (parsed as Record<string, unknown>) : undefined
    const number = typeof parsed === "number" ? parsed : Number(data?.number)
    if (!Number.isSafeInteger(number) || number <= 0) return undefined
    return {
      number,
      ...(typeof data?.headRefOid === "string" && data.headRefOid
        ? { headRefOid: data.headRefOid }
        : {}),
      ...(typeof data?.baseRefName === "string" && data.baseRefName
        ? { baseRefName: data.baseRefName }
        : {}),
      ...(typeof data?.baseRefOid === "string" && data.baseRefOid
        ? { baseRefOid: data.baseRefOid }
        : {}),
    }
  } catch {
    // Older tests/hosts returned the `--jq .number` scalar; accept it.
    const number = Number(result.stdout.trim())
    return Number.isSafeInteger(number) && number > 0 ? { number } : undefined
  }
}

/**
 * Resolve the PR for a branch-shaped review. One `gh pr view` returns the
 * number, head, and base; the caller must not re-read the same PR twice.
 */
export async function resolvePrInfo(
  cwd: string,
  scope: Scope,
  exec: Exec = defaultExec,
  opts?: ExecOptions,
): Promise<PrInfo | undefined> {
  if (scope.pr !== undefined) return { number: scope.pr }
  // An explicit branch target makes `scope.branch` the diff base, not the
  // checked-out head. Ask git for the current branch instead of looking up the
  // base's PR (which is usually a different PR, or none at all). A clean
  // default review already recorded the current branch in `scope.branch`.
  let branch = scope.branch
  if (scope.scopeKind === "branch") {
    const current = await exec(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd, opts)
    branch = current.code === 0 ? current.stdout.trim() : undefined
  }
  // A dirty worktree is deliberately excluded: its findings may anchor to
  // uncommitted lines that do not exist at the PR head, so posting them would
  // misplace or reject every comment. An explicit range/path/fresh-repo review
  // must not post to an unrelated PR.
  if (!branch || branch === "HEAD") return undefined
  const found = await exec(
    ["gh", "pr", "view", branch, "--json", "number,headRefOid,baseRefName,baseRefOid"],
    cwd,
    opts,
  )
  return parsePrInfo(found)
}

export async function resolvePrNumber(
  cwd: string,
  scope: Scope,
  exec: Exec = defaultExec,
  opts?: ExecOptions,
): Promise<number | undefined> {
  return (await resolvePrInfo(cwd, scope, exec, opts))?.number
}

/**
 * A PR baseRefName is a short branch name. `release/main` is a different
 * branch even though it ends in `/main`; only a known remote-tracking prefix
 * for the same branch counts. A stale local base at another commit is caught
 * separately by the local-HEAD check in postComments.
 */
export function samePrBase(diffBase: string, prBase: string, remotes: readonly string[] = []): boolean {
  const normalize = (ref: string): string =>
    ref.replace(/^refs\/heads\//, "").replace(/^refs\/remotes\//, "")
  const base = normalize(diffBase)
  if (base === prBase) return true
  // A remote-tracking ref is `<remote>/<branch>`. Strip a prefix only when it
  // is a real remote name: a local branch such as `release/main` is not the PR
  // base `main`, and treating it as one posts comments at the wrong anchors.
  return remotes.some(
    (remote) => remote.length > 0 && base.startsWith(`${remote}/`) && base.slice(remote.length + 1) === prBase,
  )
}

export async function postComments(deps: CommentDeps): Promise<string> {
  const { scope, result } = deps
  if (result.findings.length === 0) return ""
  const exec = deps.exec ?? defaultExec
  // A 10s hard cap killed an otherwise successful post on slow GHE links. No
  // timeout by default; an explicit dependency or env value can bound it.
  const timeoutMs = deps.timeoutMs ?? envInt("CODE_REVIEW_COMMENT_TIMEOUT_MS")
  const execOpts: ExecOptions = {
    ...(deps.signal ? { signal: deps.signal } : {}),
    ...(timeoutMs !== undefined && timeoutMs > 0 ? { timeoutMs } : {}),
  }
  const call = (argv: string[]) => exec(argv, deps.cwd, execOpts)
  // Resolve the host and its hostname together. Calling detectHost() and then
  // re-reading the remote to recover the hostname doubles the probe and can
  // disagree if the remote changes between calls.
  const hostDetails =
    deps.host === undefined ? await detectHostDetails(deps.cwd, exec, execOpts) : undefined
  const host = deps.host ?? hostDetails?.host ?? "other"
  if (host === "gitlab") {
    return "`--comment` was ignored: GitLab merge requests are out of scope for this port."
  }
  if (host !== "github") {
    return "`--comment` was ignored: the origin remote is not GitHub (GitLab MRs are out of scope)."
  }

  const prInfo = await resolvePrInfo(deps.cwd, scope, exec, execOpts)
  if (!prInfo) {
    return "`--comment` was ignored: no pull request found for this branch; pass the PR number as the target."
  }
  // A branch-shaped diff without a recorded base (the HEAD~1/HEAD ladder in a
  // clone with no upstream/main) cannot prove its line numbers describe the
  // PR's diff. Refuse rather than submitting anchors to an unrelated tree.
  if (scope.pr === undefined && scope.branch && !scope.diffBase) {
    return "`--comment` was ignored: the reviewed diff has no verified base; pass the PR number as the target."
  }
  const pr = prInfo.number

  // detectHost identifies GitHub Enterprise by probing gh auth, but the host
  // name itself is needed for the comment request. Discarding it sends every
  // GHE comment to github.com (or fails auth there). The caller can pass the
  // hostname it already resolved; otherwise resolve it once here. If the
  // lookup fails, refuse rather than silently targeting github.com.
  const resolvedHostname = deps.githubHostname ?? hostDetails?.hostname
  let githubHostname =
    resolvedHostname && resolvedHostname.toLowerCase() !== "github.com"
      ? resolvedHostname
      : undefined
  if (resolvedHostname === undefined) {
    const remote = await call(["git", "remote", "get-url", "origin"])
    if (remote.code !== 0 || !remote.stdout.trim()) {
      return "`--comment` was ignored: could not resolve the origin remote."
    }
    const remoteHost = remoteHostname(remote.stdout.trim())
    githubHostname = remoteHost && remoteHost.toLowerCase() !== "github.com" ? remoteHost : undefined
  }

  // Resolve the repository from the PR itself, not the local checkout:
  // reviewing an upstream PR from a fork clone must comment on the base
  // repository the PR belongs to. `gh repo view` would name the fork, and
  // GitHub then rejects the comment (or attaches it to the fork's own PR with
  // the same number).
  const [repo, head] = await Promise.all([
    call(["gh", "pr", "view", String(pr), "--json", "url", "--jq", ".url"]),
    // A branch-shaped review already fetched the head with the number/base in
    // one call; only fall back when the host/tests did not supply it.
    prInfo.headRefOid
      ? Promise.resolve({ stdout: prInfo.headRefOid, stderr: "", code: 0 })
      : call(["gh", "pr", "view", String(pr), "--json", "headRefOid", "--jq", ".headRefOid"]),
  ])
  let repoName = repoFromPrUrl(repo.stdout) ?? ""
  let repoError = repo.stderr.trim()
  // The PR URL is authoritative for the host as well as the repository. A
  // fork clone can have an origin on a different GitHub Enterprise instance
  // than the upstream PR it is reviewing.
  const prHost = hostFromPrUrl(repo.stdout)
  // The PR URL is authoritative for the host in both directions. A fork clone
  // can have an origin on GHE while the PR itself is on github.com; keeping the
  // origin hostname would send the comment request to the wrong instance.
  if (prHost) githubHostname = prHost.toLowerCase() === "github.com" ? undefined : prHost
  if (!repoName) {
    // Older gh versions/tests may not return a URL. Keep the local lookup as a
    // fallback, but only after the PR-scoped answer failed.
    const fallback = await call(["gh", "repo", "view", "--json", "owner,name", "--jq", '.owner.login + "/" + .name'])
    repoName = fallback.stdout.trim()
    repoError = fallback.stderr.trim() || repoError
  }
  const [owner, name] = repoName.split("/")
  const commit = head.stdout.trim()
  if (!owner || !name || !commit) {
    return `Posting GitHub comments failed: could not resolve repository or PR head (${repoError || head.stderr.trim() || "unknown error"}).`
  }

  // A branch-shaped review resolves that branch's PR, but its diff is
  // `branch...HEAD` from the local checkout. Posting local line numbers to the
  // PR head is only safe when the local HEAD is that head revision and the
  // reviewed diff base is the PR's base; otherwise the anchors describe a
  // different tree (often the inverse diff).
  if (scope.pr === undefined && scope.branch) {
    // A branch-shaped review includes uncommitted worktree changes. Those
    // lines do not exist at the PR head, so an inline anchor is either
    // rejected or attached to a different line. Refuse instead of posting a
    // review that describes a tree the PR does not contain.
    const dirty = await call(["git", "status", "--porcelain"])
    if (dirty.code !== 0) {
      return "`--comment` was ignored: could not verify the working tree is clean."
    }
    if (dirty.stdout.trim()) {
      return "`--comment` was ignored: the working tree has uncommitted changes; commit them or pass the PR number as the target."
    }
    const local = await call(["git", "rev-parse", "HEAD"])
    const localHead = local.stdout.trim()
    if (local.code !== 0 || localHead !== commit) {
      return `\`--comment\` was ignored: local HEAD ${localHead || "(unknown)"} is not the PR head ${commit}; check out the PR branch or pass the PR number as the target.`
    }
    // A default branch review falls back to main/upstream when the branch has
    // no upstream. That base can differ from the PR's target branch even when
    // local HEAD is the PR head, so the line anchors belong to another diff.
    if (scope.diffBase) {
      let prBase = prInfo.baseRefName
      if (!prBase) {
        const base = await call([
          "gh",
          "pr",
          "view",
          String(pr),
          "--json",
          "baseRefName",
          "--jq",
          ".baseRefName",
        ])
        if (base.code !== 0 || !base.stdout.trim()) {
          return "`--comment` was ignored: could not verify the pull request's base branch."
        }
        prBase = base.stdout.trim()
      }
      // Only a real remote-tracking prefix identifies the same base. A local
      // `release/main` branch must not be mistaken for the PR base `main`.
      const remoteList = await call(["git", "remote"])
      const remotes =
        remoteList.code === 0 ? remoteList.stdout.split(/\s+/).filter(Boolean) : []
      if (!samePrBase(scope.diffBase, prBase, remotes)) {
        return `\`--comment\` was ignored: the reviewed diff is based on ${scope.diffBase}, but PR #${pr} targets ${prBase}; pass the PR number as the target to review that PR's diff.`
      }
      // Matching the base *name* is not enough: the local ref can be stale.
      // Compare the merge-base the review actually captured with the one
      // GitHub computes from the PR's base commit. If they differ, the line
      // numbers describe a different diff even though both refs say "main".
      const prBaseOid =
        prInfo.baseRefOid ??
        (
          await call([
            "gh",
            "pr",
            "view",
            String(pr),
            "--json",
            "baseRefOid",
            "--jq",
            ".baseRefOid",
          ])
        ).stdout.trim()
      if (!prBaseOid) {
        return "`--comment` was ignored: could not verify the pull request's base commit."
      }
      const reviewedMergeBase = await call(["git", "merge-base", scope.diffBase, "HEAD"])
      const prMergeBase = await call(["git", "merge-base", prBaseOid, "HEAD"])
      if (
        reviewedMergeBase.code !== 0 ||
        prMergeBase.code !== 0 ||
        reviewedMergeBase.stdout.trim() !== prMergeBase.stdout.trim()
      ) {
        return `\`--comment\` was ignored: the reviewed diff base ${scope.diffBase} does not share the pull request's merge base; fetch the PR base or pass the PR number as the target.`
      }
    }
  }

  // Resolve every line side in one pass instead of re-parsing the whole patch
  // for each finding.
  const sides = diffSideMap(
    scope.diffText,
    result.findings.flatMap((f) => {
      const line = lineOf(f)
      return line === undefined ? [] : [{ file: f.file, line }]
    }),
  )
  const outcomes = await mapLimit(result.findings, deps.concurrency ?? 4, async (f) => {
    const line = lineOf(f)
    if (line === undefined) return { ok: false, message: `${f.file}: no line to anchor an inline comment` }
    if (!sides.hasLine(f.file, line)) {
      return {
        ok: false,
        message: `${f.file}:${line}: line is not part of the reviewed diff; no inline anchor`,
      }
    }
    const r = await call(
      buildGitHubCommentArgs({
        owner,
        repo: name,
        pr,
        commit,
        // GitHub anchors even a LEFT comment on the head path of a renamed
        // file; the old path from the finding would be rejected (422).
        path: sides.pathFor(f.file, line),
        line,
        body: commentBody(f),
        side: sides.sideFor(f.file, line),
        ...(githubHostname ? { hostname: githubHostname } : {}),
      }),
    )
    return r.code === 0
      ? { ok: true, message: "" }
      : { ok: false, message: `${f.file}:${line}: ${r.stderr.trim() || "gh api failed"}` }
  })
  const posted = outcomes.filter((o) => o.ok).length
  const failures = outcomes.filter((o) => !o.ok).map((o) => o.message)
  const suffix = failures.length > 0 ? `\n${failures.map((x) => `  - ${x}`).join("\n")}` : ""
  return `Posted ${posted}/${result.findings.length} ${pluralWord(result.findings.length, "inline GitHub PR comment")}.${suffix}`
}
