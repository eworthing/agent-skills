/**
 * Phase 0: deterministic diff discovery.
 *
 * The reference's Phase 0 is prose handed to the main agent; the hidden
 * workflows used a Scope agent. This module reproduces the observable rules
 * those instructions encode (upstream range, main/HEAD~1 fallbacks, working
 * tree inclusion, PR/branch/path targets) without a model in the loop.
 *
 * Backported from `fyeeme/pi-review` (MIT): nearest-git-root/submodule path
 * resolution, the fresh-repo ladder, git invocation hardening, the abort/
 * timeout shape, and the changed-file context package. The primary diff range
 * and the reference's `Zs` numstat invocation stay unchanged.
 */
import { execFile } from "node:child_process"
import { closeSync, existsSync, openSync, readFileSync, readSync, realpathSync, statSync } from "node:fs"
import { homedir } from "node:os"
import { basename, dirname, isAbsolute, join, relative, resolve, sep } from "node:path"
import { TextDecoder } from "node:util"
import { StringDecoder } from "node:string_decoder"
import { envInt, pluralize, positiveLine, renderPath, truncateText } from "./finding.ts"
import { normalizeRef, sameRefName } from "./refs.ts"

export type ExecOptions = { signal?: AbortSignal; timeoutMs?: number }

export type ExecResult = {
  stdout: string
  stderr: string
  code: number
  /** The child was killed by the per-call timeout. */
  timedOut?: boolean
  /** The child was killed by the caller's abort signal. */
  aborted?: boolean
}

export type Exec = (argv: string[], cwd: string, opts?: ExecOptions) => Promise<ExecResult>

export const defaultExec: Exec = (argv, cwd, opts = {}) =>
  new Promise((resolvePromise) => {
    execFile(
      argv[0],
      argv.slice(1),
      {
        cwd,
        maxBuffer: 64 * 1024 * 1024,
        ...(opts.signal ? { signal: opts.signal } : {}),
        ...(opts.timeoutMs !== undefined ? { timeout: opts.timeoutMs } : {}),
      },
      (err, stdout, stderr) => {
        const e = err as (NodeJS.ErrnoException & { killed?: boolean }) | null
        const aborted = opts.signal?.aborted === true || e?.name === "AbortError"
        const errorCode = (e as unknown as { code?: unknown } | null)?.code
        // execFile sets `killed` for both the timeout and a maxBuffer abort.
        // A maxBuffer kill is not a timeout: reporting it as one tells the user
        // to raise a timeout that was never reached.
        const maxBuffer =
          errorCode === "ERR_CHILD_PROCESS_STDIO_MAXBUFFER" ||
          /maxBuffer/i.test(e?.message ?? "")
        const timedOut = e?.killed === true && !aborted && !maxBuffer
        // Exit code 1 is a semantic git answer (diff --quiet: changes exist).
        // A killed or failed exec with no numeric exit status must not look
        // like that answer, or a timeout is read as a non-empty diff.
        const raw =
          typeof errorCode === "number" ? errorCode : e ? (timedOut ? 124 : aborted ? 130 : 2) : 0
        resolvePromise({
          stdout: stdout ?? "",
          stderr: stderr ?? "",
          code: raw ?? 0,
          ...(timedOut ? { timedOut } : {}),
          ...(aborted ? { aborted } : {}),
        })
      },
    )
  })

export type Scope = {
  /** All diff commands joined for display; `diffCommands` is the structured form. */
  diffCommand: string
  /** Captured diff commands; prompts render these instead of re-parsing. */
  diffCommands?: string[]
  files: string[]
  claudeMdFiles: string[]
  summary: string
  conventions: string
  target?: string
  root: string
  pr?: number
  /** PR head captured with the patch, so comments pin the reviewed commit. */
  prHeadOid?: string
  /** PR URL captured with the patch; authoritative for the base repository. */
  prUrl?: string
  branch?: string
  /** Added + deleted lines in the primary diff (Qs finder-budget input). */
  diffLines: number
  /** Captured unified diff text, passed to child agents and the synthesizer. */
  diffText?: string
  /** Repo root + scope label + per-file churn, injected into every prompt. */
  context?: string
  /** upstream | worktree | range | branch | path | pr | fresh */
  scopeKind?: string
  /** Branch/ref the reviewed range is based on, when it is known. */
  diffBase?: string
  /** Non-fatal discovery failures; the review must not present itself as complete. */
  warnings?: string[]
}

/**
 * The subset of Scope that prompt rendering needs. Deriving it from Scope
 * keeps the two in sync when a field is added.
 */
export type ScopeBlock = Pick<
  Scope,
  | "diffCommand"
  | "diffCommands"
  | "files"
  | "claudeMdFiles"
  | "summary"
  | "conventions"
  | "target"
  | "root"
  | "context"
  | "scopeKind"
  | "diffText"
>

/** Scope is already a superset of ScopeBlock; no field-by-field copy needed. */
export function scopeBlock(scope: Scope): ScopeBlock {
  return scope
}

export type ScopeOptions = {
  cwd: string
  target?: string
  exec?: Exec
  conventionsBudget?: number
  /** Propagated to every git/gh call; a hung hook must not stall the command. */
  signal?: AbortSignal
  /** Per-call git/gh timeout. Unset by default: a large PR diff must be
   *  allowed to finish; CODE_REVIEW_SCOPE_TIMEOUT_MS can bound it. */
  scopeTimeoutMs?: number
  /** The reference's `Zs` numstat timeout. Default 30s. */
  numstatTimeoutMs?: number
  /** Skip the numstat/PR line-count pass when the cell has no finder budget. */
  includeDiffLines?: boolean
  /** Skip the CLAUDE.md/AGENTS.md reads when no finder renders conventions. */
  includeConventions?: boolean
  /** A target classification already computed for host detection. */
  classification?: TargetClassification
  /** Verify the PR head after capturing the patch. Only --comment needs it. */
  verifyPrHead?: boolean
}

/** The PR metadata fields the scope needs, parsed once per discovery. */
type PrMeta = {
  files?: Array<{ path?: string }>
  additions?: number
  deletions?: number
  headRefOid?: string
  url?: string
}

/**
 * Hooks, fsmonitor, and askpass can execute user code or block on a prompt
 * during a read-only review. `quotePath=false` keeps ordinary paths readable;
 * the parsers still handle the quoted form for tabs/newlines and non-ASCII.
 */
export const GIT_HARDENING = [
  "-c",
  "core.hooksPath=/dev/null",
  "-c",
  "core.fsmonitor=",
  "-c",
  "core.askPass=",
  "-c",
  "core.quotePath=false",
]

/** Prefix a `git` argv with the read-only config hardening. */
export function hardenedGit(argv: string[]): string[] {
  return ["git", ...GIT_HARDENING, ...argv.slice(1)]
}

function quote(argv: string[]): string {
  return argv
    // `{}` and `~` expand in a shell even without whitespace; a changed file
    // named `{a,b}.ts` or `~/x` must stay one literal argument. Control
    // characters are escaped first: this text is rendered on one prompt line,
    // and a newline in a repo path must not start a forged instruction.
    .map((a) => {
      // `renderPath` escapes the full control-character class, not only CR/LF;
      // a filename with a tab or C1 control must not forge a prompt line.
      const safe = renderPath(a)
      return /^[\w@./:^=-]+$/.test(safe) ? safe : `'${safe.replaceAll("'", "'\\''")}'`
    })
    .join(" ")
}

function looksLikeRange(s: string): boolean {
  // Refs routinely contain dots (`v1.2.3`, `release/1.4`). Only the leading
  // character must not be a dot, so `../path` stays a path target; the right
  // side must start with a ref character, not `/`, so `a/../b` stays a path.
  return /^[^.\s][^\s]*\.\.\.?[^\s./][^\s]*$/.test(s)
}

async function git(exec: Exec, cwd: string, args: string[], opts?: ExecOptions): Promise<ExecResult> {
  return exec(["git", ...GIT_HARDENING, ...args], cwd, opts)
}

/** One failure policy for every scope-discovery command. */
function assertExec(
  r: ExecResult,
  label: string,
  timeoutSuffix: string,
  cancelled = "Diff discovery was cancelled.",
): void {
  if (r.aborted) throw new Error(cancelled)
  if (r.timedOut) throw new Error(`${label} timed out${timeoutSuffix}.`)
}

async function revParse(exec: Exec, cwd: string, ref: string, opts?: ExecOptions): Promise<boolean> {
  const r = await git(exec, cwd, ["rev-parse", "--verify", "--quiet", "--end-of-options", ref], opts)
  // A timed-out or aborted probe says nothing about the ref. Treating it as
  // "not a revision" sent the caller down the fresh-repository branch and
  // silently ignored committed changes.
  assertExec(r, "git rev-parse", " while resolving the diff base")
  return r.code === 0 && r.stdout.trim().length > 0
}

/**
 * A branch can exist only as a remote-tracking ref (`origin/release/1.4`).
 * `rev-parse release/1.4` checks `refs/heads/`, so without this probe the
 * requested branch is silently ignored and the current worktree is reviewed.
 */
async function resolveRemoteBranch(
  exec: Exec,
  cwd: string,
  target: string,
  opts?: ExecOptions,
): Promise<string | undefined> {
  const remotes = await git(exec, cwd, ["remote"], opts)
  assertExec(remotes, "git remote", " while resolving the diff base")
  if (remotes.code !== 0) return undefined
  const names = remotes.stdout.trim().split(/\s+/).filter(Boolean)
  const ordered = [...names.filter((name) => name === "origin"), ...names.filter((name) => name !== "origin")]
  for (const remote of ordered) {
    const ref = `${remote}/${target}`
    if (await revParse(exec, cwd, ref, opts)) return ref
  }
  return undefined
}

/** Walk up from `from` to the nearest directory containing `.git` (dir or file). */
export function findGitRoot(from: string): string | null {
  // Resolve symlinks before walking: a link into a repository subdirectory has
  // no `.git` of its own, and the unresolved path would walk to `/tmp` instead
  // of the repository that actually contains the target.
  let dir: string
  try {
    dir = realpathSync(resolve(from))
  } catch {
    dir = resolve(from)
  }
  for (;;) {
    if (existsSync(join(dir, ".git"))) return dir
    const parent = dirname(dir)
    if (parent === dir) return null
    dir = parent
  }
}

/** The absolute path of an existing target, trying the literal @-form first. */
export function resolveTargetPath(cwd: string, target: string | undefined): string | null {
  const raw = (target ?? "").trim()
  if (!raw) return null
  for (const candidate of raw.startsWith("@") ? [raw, raw.slice(1)] : [raw]) {
    const resolved = resolve(cwd, candidate)
    if (existsSync(resolved)) return resolved
  }
  return null
}

export type DiffScope = {
  root: string
  /** Path inside `root`, or null when the target is the whole root. */
  relPath: string | null
  /** The target resolved to an existing path (not a branch/PR/range). */
  isPath: boolean
}

/**
 * Resolve a path target to the nearest git root, including submodules.
 * `@`-prefixed paths are tried literally first (a real directory may start
 * with `@`), then with the prefix stripped. A non-path target keeps the
 * whole-diff scope of cwd's git root.
 */
export function resolveDiffScope(cwd: string, target: string | undefined): DiffScope | null {
  const abs = resolveTargetPath(cwd, target)
  if (abs === null) {
    const root = findGitRoot(cwd)
    return root ? { root, relPath: null, isPath: false } : null
  }
  const root = findGitRoot(abs)
  if (!root) return null
  // findGitRoot returns the physical root, so compare against the physical
  // target as well; otherwise a symlinked path becomes `../../link`.
  let physical = abs
  try {
    physical = realpathSync(abs)
  } catch {
    /* keep the resolved path */
  }
  const rel = relative(root, physical)
  return {
    root,
    // Only the platform separator is a path separator. On POSIX a backslash
    // is a literal filename character and must not be rewritten.
    relPath: rel === "" || rel === "." ? null : rel.replaceAll(sep, "/"),
    isPath: true,
  }
}

/**
 * A target the user explicitly wrote as a path. `@` is not included: it is
 * also a valid branch prefix, so an `@name` target is resolved as a branch
 * when one exists and as a path otherwise.
 */
export function explicitPathTarget(target: string): boolean {
  return target.startsWith("./") || target.startsWith("../") || target.startsWith("/") || target.endsWith("/")
}

/**
 * The target was written as a path but does not exist. Shared by the inline
 * path (which never calls resolveScope) and scope discovery so the two cannot
 * drift on which typos are rejected.
 */
export function missingExplicitPathTarget(cwd: string, target?: string): string | undefined {
  if (!target || prTargetNumber(target) !== undefined || !explicitPathTarget(target)) return undefined
  return resolveTargetPath(cwd, target) === null ? target : undefined
}

/** Extract a path-looking token from free-form instructions. */
export function extractPathHint(target: string, cwd: string): string | undefined {
  const tokens = target.split(/\s+/).map((t) =>
    t
      .replace(/^[`'"(<[{*]+/, "")
      .replace(/[`'",.:;!?)\]}>*]+$/, ""),
  )
  for (const token of tokens) {
    if (!token.includes("/") && !/\.[a-z0-9]{1,8}$/i.test(token)) continue
    const abs = isAbsolute(token) ? token : resolve(cwd, token)
    if (existsSync(abs)) return token
  }
  return undefined
}

type DiffSpec = {
  /** A revision/range. `--staged` is a flag, not a range. */
  range?: string
  staged?: boolean
  pathspec?: string
}

type DiffMode = "diff" | "name-status" | "numstat" | "quiet"

/** One argv builder for every read-only diff shape. */
function gitDiffArgs(spec: DiffSpec, mode: DiffMode): string[] {
  return [
    "diff",
    // Safe flags first, so the displayed command matches the agent
    // permission pattern even for `--staged` or a mode flag.
    "--no-ext-diff",
    "--no-textconv",
    ...(spec.staged ? ["--staged"] : []),
    ...(mode === "quiet"
      ? ["--quiet"]
      : mode === "name-status"
        ? ["--name-status"]
        : mode === "numstat"
          ? ["--numstat"]
          : []),
    "--end-of-options",
    ...(spec.range ? [spec.range] : []),
    ...(spec.pathspec ? ["--", spec.pathspec] : []),
  ]
}

const diffArgv = (spec: DiffSpec): string[] => ["git", ...GIT_HARDENING, ...gitDiffArgs(spec, "diff")]

const nameArgv = (spec: DiffSpec): string[] => ["git", ...GIT_HARDENING, ...gitDiffArgs(spec, "name-status")]

/** `git()` prepends the binary and hardening flags, so this omits both. */
const quietArgs = (spec: DiffSpec): string[] => gitDiffArgs(spec, "quiet")

function sameDir(a: string, b: string): boolean {
  try {
    return realpathSync(a) === realpathSync(b)
  } catch {
    return resolve(a) === resolve(b)
  }
}

/**
 * Characters the child permission table denies anywhere in a command string
 * (`;`, `|`, `&`, `$`, `<`, `>`, backtick, and a newline), plus control
 * characters `renderPath` rewrites. A path containing one cannot be placed in
 * a runnable command: the host matches the raw string, not shell quoting, so
 * the deny rule wins even when the path is single-quoted. The command then
 * omits the pathspec; the embedded diff is still scoped, and the review target
 * tells the agent to stay inside it. A tab is safe: it is neither denied nor
 * rewritten, so it stays in the command.
 */
const SHELL_DENIED = /[;&|$<>`\n\r\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u2028\u2029]/

/**
 * A shell-ready command the model can re-run visibly. Derive it from the same
 * argv builder the engine executes; it carries both the safe
 * `--no-ext-diff`/`--no-textconv` flags and the `-c` config hardening. The
 * hardening matters in the child too: a repository's `core.fsmonitor` or
 * hooks can execute code during what is advertised as a read-only review.
 */
function labelFor(spec: DiffSpec, root: string, cwd: string): string {
  const omitPathspec = spec.pathspec !== undefined && SHELL_DENIED.test(spec.pathspec)
  const display = omitPathspec ? { ...spec, pathspec: undefined } : spec
  const argv = gitDiffArgs(display, "diff").map((a) => quote([a]))
  const inRoot = sameDir(root, cwd)
  // The session cwd is inside the repository root, so a relative `-C` is a
  // run of `..` segments and cannot contain the ancestor's metacharacter.
  // Resolve both sides first: macOS `/var` and `/private/var` spellings would
  // otherwise make `relative` walk back through the metacharacter.
  const relativeRoot = inRoot
    ? undefined
    : SHELL_DENIED.test(root)
      ? (() => {
          try {
            return relative(realpathSync(cwd), realpathSync(root)) || "."
          } catch {
            return undefined
          }
        })()
      : root
  const unsafeRoot = !inRoot && (relativeRoot === undefined || SHELL_DENIED.test(relativeRoot))
  const command = unsafeRoot
    ? ""
    : relativeRoot === undefined
      ? ["git", ...GIT_HARDENING, ...argv].join(" ")
      : ["git", "-C", quote([relativeRoot]), ...GIT_HARDENING, ...argv].join(" ")
  const notes = [
    omitPathspec ? "pathspec omitted: shell metacharacter in the review target" : "",
    unsafeRoot ? "command omitted: repository root contains a shell metacharacter" : "",
  ].filter(Boolean)
  if (command === "") return notes.join("; ")
  return notes.length > 0 ? `${command}  # ${notes.join("; ")}` : command
}

/** Unquote git's C-style path quoting (`"a/foo\\tbar"`). */
export function unquoteGitPath(raw: string): string {
  // Git only quotes a path that needs it. Whitespace in an unquoted path is
  // part of the filename, so do not trim the raw field before deciding.
  const s = raw.endsWith("\r") ? raw.slice(0, -1) : raw
  if (s.length < 2 || !s.startsWith('"') || !s.endsWith('"')) return s
  const body = s.slice(1, -1)
  const decoder = new TextDecoder()
  let out = ""
  // Git quotes every byte of a non-ASCII path separately (`caf\303\251.ts`),
  // so contiguous octal escapes must be decoded together as UTF-8 rather than
  // appended one code unit at a time.
  let pending: number[] = []
  const flush = () => {
    if (pending.length === 0) return
    out += decoder.decode(Uint8Array.from(pending))
    pending = []
  }
  for (let i = 0; i < body.length; i++) {
    const ch = body[i]
    if (ch !== "\\") {
      flush()
      out += ch
      continue
    }
    const next = body[++i]
    if (next === undefined) {
      flush()
      out += "\\"
      break
    }
    switch (next) {
      case "n":
        flush()
        out += "\n"
        break
      case "t":
        flush()
        out += "\t"
        break
      case "r":
        flush()
        out += "\r"
        break
      case "b":
        flush()
        out += "\b"
        break
      case "f":
        flush()
        out += "\f"
        break
      case "v":
        flush()
        out += "\v"
        break
      case "a":
        // Git's C-style quoting uses \a for BEL (0x07).
        flush()
        out += "\x07"
        break
      case "\\":
        flush()
        out += "\\"
        break
      case '"':
        flush()
        out += '"'
        break
      default:
        if (/[0-7]/.test(next)) {
          let oct = next
          while (oct.length < 3 && /[0-7]/.test(body[i + 1] ?? "")) oct += body[++i]
          pending.push(parseInt(oct, 8))
        } else {
          flush()
          out += next
        }
    }
  }
  flush()
  return out
}

function pathFromHeader(raw: string, prefix: "a/" | "b/"): string {
  const unquoted = unquoteGitPath(raw)
  return unquoted.startsWith(prefix) ? unquoted.slice(prefix.length) : unquoted
}

function parseDiffGitHeader(line: string): { a: string; b: string } | null {
  if (!line.startsWith("diff --git ")) return null
  const body = line.slice("diff --git ".length)
  const starts = new Set<number>()
  // The right field is either ` b/...` or, for a quoted path, ` "b/...`.
  for (const needle of [" b/", ' "b/']) {
    for (let i = body.indexOf(needle); i !== -1; i = body.indexOf(needle, i + 1)) {
      starts.add(i + 1)
    }
  }
  const candidates: Array<{ a: string; b: string }> = []
  for (const start of [...starts].sort((x, y) => x - y)) {
    const left = body.slice(0, start - 1)
    const right = body.slice(start)
    if (!(left.startsWith("a/") || left.startsWith('"a/'))) continue
    if (!(right.startsWith("b/") || right.startsWith('"b/'))) continue
    candidates.push({ a: pathFromHeader(left, "a/"), b: pathFromHeader(right, "b/") })
  }
  if (candidates.length === 0) return null
  // A modified file has the same path on both sides. Splitting there is
  // unambiguous even when the path itself contains ` b/`; the greedy
  // last-separator heuristic would invent two nonexistent paths.
  const identical = candidates.find((c) => c.a === c.b)
  if (identical) return identical
  // A rename has different paths. The real separator is the split whose two
  // path fields are closest in length. On a tie prefer the earlier split: a
  // new path may itself contain ` b/`, and the later split would then cut the
  // path in half and invent two nonexistent filenames.
  let best = candidates[0]
  let bestScore = Math.abs(best.a.length - best.b.length)
  for (const candidate of candidates.slice(1)) {
    const score = Math.abs(candidate.a.length - candidate.b.length)
    if (score < bestScore) {
      best = candidate
      bestScore = score
    }
  }
  return best
}

type FileList = { files: string[]; ok: boolean }

/** Run a name-status command and distinguish "no changes" from a failure. */
async function listFiles(exec: Exec, cwd: string, argv: string[], opts?: ExecOptions): Promise<FileList> {
  const r = await exec(argv, cwd, opts)
  if (r.code !== 0) return { files: [], ok: false }
  const out: string[] = []
  for (const line of r.stdout.split("\n")) {
    if (!line.trim()) continue
    const parts = line.split("\t")
    const status = parts[0] ?? ""
    if (status.startsWith("R") || status.startsWith("C")) {
      if (parts[1]) out.push(unquoteGitPath(parts[1]))
      if (parts[2]) out.push(unquoteGitPath(parts[2]))
    } else if (parts[1]) {
      out.push(unquoteGitPath(parts[1]))
    }
  }
  return { files: out, ok: true }
}

function uniq(xs: string[]): string[] {
  return [...new Set(xs.filter(Boolean))]
}

/**
 * One unified-diff state machine for every consumer. Emits file headers,
 * hunk starts, and content lines with their old/new positions. Consumers
 * derive the file list, churn counts, and comment sides from the same parse,
 * so a quoting or hunk-boundary fix cannot drift between them.
 */
type PatchHandlers = {
  onFile?: (a: string | undefined, b: string | undefined) => void
  onBinary?: (file: string | undefined) => void
  onHunk?: (oldStart: number, newStart: number) => void
  onLine?: (op: "+" | "-" | " ", oldLine: number | undefined, newLine: number | undefined) => void
  /** Authoritative rename pair from the patch body, when git emits one. */
  onRename?: (from: string, to: string) => void
}

export function walkPatch(patch: string, handlers: PatchHandlers): void {
  let currentA: string | undefined
  let currentB: string | undefined
  let pendingA: string | undefined
  let renameFrom: string | undefined
  let inHunk = false
  let oldLine = 0
  let newLine = 0
  let oldRemaining = 0
  let newRemaining = 0

  for (const raw of patch.split("\n")) {
    // A `diff --git` line always begins a new file, even when a malformed hunk
    // count left the previous hunk open. Content lines always carry a
    // +/-/space prefix, so this cannot match a real hunk body.
    const header = parseDiffGitHeader(raw)
    if (header) {
      currentA = header.a
      currentB = header.b
      pendingA = undefined
      renameFrom = undefined
      inHunk = false
      handlers.onFile?.(header.a, header.b)
      continue
    }
    for (;;) {
      if (!inHunk) {
        // `diff --git` cannot represent a rename unambiguously when either
        // path contains ` b/`; the rename lines can. Prefer them over the
        // header split for both the file list and the churn map.
        if (raw.startsWith("rename from ")) {
          renameFrom = unquoteGitPath(raw.slice("rename from ".length))
          break
        }
        if (raw.startsWith("rename to ")) {
          const to = unquoteGitPath(raw.slice("rename to ".length))
          if (renameFrom !== undefined) handlers.onRename?.(renameFrom, to)
          renameFrom = undefined
          break
        }
        if (raw.startsWith("--- ")) {
          pendingA = pathFromFileHeader(raw, "a/")
          break
        }
        if (raw.startsWith("+++ ")) {
          const b = pathFromFileHeader(raw, "b/")
          currentA = pendingA ?? currentA
          currentB = b
          pendingA = undefined
          handlers.onFile?.(currentA, currentB)
          break
        }
        const m = raw.match(HUNK_HEADER)
        if (m) {
          inHunk = true
          oldLine = Number(m[1])
          oldRemaining = m[2] === undefined ? 1 : Number(m[2])
          newLine = Number(m[3])
          newRemaining = m[4] === undefined ? 1 : Number(m[4])
          handlers.onHunk?.(oldLine, newLine)
          break
        }
        if (raw.startsWith("Binary files")) handlers.onBinary?.(currentB ?? currentA)
        break
      }
      // A hunk ended on the previous line. Re-process this line as metadata.
      if (oldRemaining <= 0 && newRemaining <= 0) {
        inHunk = false
        continue
      }
      if (raw.startsWith("\\")) break
      if (raw.startsWith("+")) {
        handlers.onLine?.("+", undefined, newLine)
        newLine++
        newRemaining--
      } else if (raw.startsWith("-")) {
        handlers.onLine?.("-", oldLine, undefined)
        oldLine++
        oldRemaining--
      } else {
        handlers.onLine?.(" ", oldLine, newLine)
        oldLine++
        newLine++
        oldRemaining--
        newRemaining--
      }
      break
    }
  }
}

const HUNK_HEADER = /^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@/

type FileChurn = { added: number; removed: number; binary: boolean }

/**
 * Walk a unified patch once and collect per-file churn plus the changed-line
 * total. Hunk headers delimit content lines: outside a hunk `---`/`+++` are
 * file headers; inside one they can be real removed/added content
 * (`-- comment`, `++ i`). `\ No newline at end of file` annotates the previous
 * line and consumes neither side.
 */
export function scanPatchChurn(patch: string): {
  files: Map<string, FileChurn>
  paths: Set<string>
  total: number
} {
  const files = new Map<string, FileChurn>()
  const paths = new Set<string>()
  let current: string | undefined
  let lastFile: { a?: string; b?: string } | undefined
  let total = 0
  walkPatch(patch, {
    onFile: (a, b) => {
      if (a) paths.add(a)
      if (b) paths.add(b)
      lastFile = { a, b }
      current = b ?? a
      if (current && !files.has(current)) files.set(current, { added: 0, removed: 0, binary: false })
    },
    onRename: (from, to) => {
      // Move the churn accumulated under the header's guessed key onto the
      // authoritative rename target, and drop the guessed paths.
      if (lastFile?.a) paths.delete(lastFile.a)
      if (lastFile?.b) paths.delete(lastFile.b)
      const churn = current === undefined ? undefined : files.get(current)
      if (current !== undefined) files.delete(current)
      if (from) paths.add(from)
      paths.add(to)
      if (churn) files.set(to, churn)
      else if (!files.has(to)) files.set(to, { added: 0, removed: 0, binary: false })
      current = to
      lastFile = { a: from, b: to }
    },
    onBinary: () => {
      const churn = current === undefined ? undefined : files.get(current)
      if (churn) churn.binary = true
    },
    onLine: (op) => {
      if (op === " ") return
      total++
      const churn = current === undefined ? undefined : files.get(current)
      if (!churn) return
      if (op === "+") churn.added++
      else churn.removed++
    },
  })
  return { files, paths, total }
}

/** Sum added/removed lines from `git diff --numstat`; binary entries are "-". */
function numstatTotal(stdout: string): number {
  let total = 0
  for (const line of stdout.split("\n")) {
    const [added, removed] = line.split("\t")
    if (/^\d+$/.test(added ?? "")) total += Number(added)
    if (/^\d+$/.test(removed ?? "")) total += Number(removed)
  }
  return total
}

/** Strip the trailing tab Git appends to `---`/`+++` fields with spaces. */
function pathFromFileHeader(line: string, prefix: "a/" | "b/"): string | undefined {
  const raw = line.slice(4).replace(/\r$/, "").replace(/\t$/, "")
  if (raw === "/dev/null") return undefined
  return pathFromHeader(raw, prefix)
}

export type DiffSideMap = {
  sideFor(file: string, line: number): "RIGHT" | "LEFT"
  /** The head-side path for a finding, including when it names a renamed-from file. */
  pathFor(file: string, line: number): string
  /**
   * Whether the line appears in the reviewed patch. With no patch available
   * the answer is optimistic: posting can still proceed, but a known-missing
   * anchor is rejected before GitHub returns a 422.
   */
  hasLine(file: string, line: number): boolean
}

type SideRequest = {
  key: string
  file: string
  line: number
  oldOnly: boolean
  left: boolean
  right: boolean
  /** The `b/` path when this finding names the old side of a rename. */
  headFile?: string
}

/**
 * Resolve LEFT/RIGHT for every requested line in one pass over the patch.
 * GitHub anchors a comment on a deleted line with side=LEFT and the old-file
 * line number; the same number on the head side would point at unrelated code.
 *
 * A replacement hunk can contain the same number on both sides. Prefer the
 * head side (RIGHT) when the line exists there, and the old side (LEFT) for a
 * finding anchored to a renamed-from path. Scanning once also avoids
 * re-parsing the whole patch for every posted comment.
 */
export function diffSideMap(
  patch: string | undefined,
  requests: Array<{ file: string; line: number }>,
): DiffSideMap {
  const unique = new Map<string, SideRequest>()
  for (const request of requests) {
    if (!Number.isFinite(request.line)) continue
    const key = `${request.file}\0${request.line}`
    if (unique.has(key)) continue
    unique.set(key, {
      key,
      file: request.file,
      line: request.line,
      oldOnly: false,
      left: false,
      right: false,
    })
  }
  const states = [...unique.values()]
  const byFile = new Map<string, SideRequest[]>()
  for (const state of states) {
    const list = byFile.get(state.file) ?? []
    list.push(state)
    byFile.set(state.file, list)
  }
  const resolved = new Map<string, "RIGHT" | "LEFT">()
  const headPaths = new Map<string, string>()
  const matched = new Set<string>()

  if (patch && states.length > 0) {
    let active: SideRequest[] = []
    const activate = (a: string | undefined, b: string | undefined) => {
      active = [
        ...(a ? byFile.get(a) ?? [] : []),
        ...(b && b !== a ? byFile.get(b) ?? [] : []),
      ]
      for (const state of active) {
        if (a === state.file && a !== b) {
          state.oldOnly = true
          if (b) state.headFile = b
        }
      }
    }
    const consider = (
      op: "+" | "-" | " ",
      oldLine: number | undefined,
      newLine: number | undefined,
    ) => {
      for (const state of active) {
        if (state.oldOnly) {
          // A finding that named the old side of a rename stays on that side.
          // An added line in the new file that happens to reuse the number is
          // not evidence that the old line moved.
          if (op !== "+" && oldLine === state.line) {
            state.left = true
            matched.add(state.key)
          }
        } else {
          if (op === "-" && oldLine === state.line) {
            state.left = true
            matched.add(state.key)
          }
          if (op !== "-" && newLine === state.line) {
            state.right = true
            matched.add(state.key)
          }
        }
      }
    }
    walkPatch(patch, {
      onFile: (a, b) => activate(a, b),
      onRename: (from, to) => activate(from, to),
      onLine: (op, oldLine, newLine) => consider(op, oldLine, newLine),
    })
  }

  for (const state of states) {
    const side = state.oldOnly
      ? state.left
        ? "LEFT"
        : "RIGHT"
      : state.right
        ? "RIGHT"
        : state.left
          ? "LEFT"
          : "RIGHT"
    resolved.set(state.key, side)
    if (state.headFile) headPaths.set(state.key, state.headFile)
  }
  return {
    sideFor(file: string, line: number): "RIGHT" | "LEFT" {
      return resolved.get(`${file}\0${line}`) ?? "RIGHT"
    },
    pathFor(file: string, line: number): string {
      return headPaths.get(`${file}\0${line}`) ?? file
    },
    hasLine(file: string, line: number): boolean {
      if (!patch) return true
      return matched.has(`${file}\0${line}`)
    },
  }
}

function readCapped(path: string, budget: number, knownSize?: number): string {
  try {
    if (budget <= 0) return ""
    const size = knownSize ?? statSync(path).size
    // Small files are cheap to read whole. A large CLAUDE.md must not be
    // loaded into memory just to keep a 10-20 KB slice.
    if (size <= budget) return readFileSync(path, "utf8")
    // `budget` counts UTF-16 code units, not bytes. A UTF-8 code unit can need
    // up to three bytes (a BMP character; an astral pair is four bytes for two
    // units), so read enough bytes to fill the character budget instead of
    // truncating a Chinese/Japanese conventions file at a third of its text.
    const byteBudget = Math.min(size, budget * 3)
    const fd = openSync(path, "r")
    try {
      const buffer = Buffer.alloc(byteBudget)
      const read = readSync(fd, buffer, 0, byteBudget, 0)
      // A byte budget can land inside a multi-byte character. StringDecoder
      // withholds an incomplete trailing sequence instead of emitting U+FFFD,
      // so the conventions block never ends with a corrupted character.
      const text = new StringDecoder("utf8").write(buffer.subarray(0, read))
      // A short read, or a byte budget that covers the whole file, proves the
      // file ended. A full read only proves the buffer filled: multi-byte text
      // can decode to fewer characters than the budget while the tail was
      // never read, so those bytes must still carry the truncation marker.
      const complete = read < byteBudget || byteBudget >= size
      const marker = "\n…(truncated)"
      if (complete) {
        // A file that fits the byte budget can still exceed the character
        // budget (the byte budget allows up to three bytes per code unit).
        // Mark the cut instead of presenting a truncated file as complete.
        if (text.length <= budget) return text
        return budget <= marker.length
          ? truncateText(text, budget)
          : `${truncateText(text, budget - marker.length)}${marker}`
      }
      // Keep the returned value inside the cap: callers sum lengths to enforce
      // the conventions budget, and appending a marker past the cap made a later
      // source look unaffordable.
      return budget <= marker.length
        ? truncateText(text, budget)
        : `${truncateText(text, budget - marker.length)}${marker}`
    } finally {
      closeSync(fd)
    }
  } catch {
    return ""
  }
}

/** Soft cap on the context package's changed-file index. */
export const CONTEXT_PACKAGE_MAX_FILES = 200

/**
 * Zero-token context package injected into every prompt: repo root, resolved
 * scope, and a changed-file index with add/remove counts parsed straight out
 * of the diff. No extra git calls, so the index cannot drift from the diff.
 */
export function buildContextPackage(
  diff: string,
  root: string,
  scopeLabel: string,
  fallbackFiles: string[] = [],
  /** Reuse the caller's single patch scan instead of parsing the diff again. */
  parsedChurn?: Map<string, FileChurn>,
): string {
  const churn = parsedChurn ?? scanPatchChurn(diff).files

  // A rename records only the new path in the churn map, and a partially
  // failed capture can leave a scoped file with no patch entry. Keep the
  // fallback list even when the map is populated.
  const files = uniq([...churn.keys(), ...fallbackFiles])
  const lines: string[] = [`Repo root: ${renderPath(root)}`, `Diff scope: ${renderPath(scopeLabel)}`]
  if (files.length > 0) {
    lines.push("Changed files (added/removed lines):")
    for (const f of files.slice(0, CONTEXT_PACKAGE_MAX_FILES)) {
      const c = churn.get(f)
      lines.push(`  ${renderPath(f)}${c ? (c.binary ? " (binary)" : ` +${c.added} -${c.removed}`) : ""}`)
    }
    if (files.length > CONTEXT_PACKAGE_MAX_FILES) {
      lines.push(`  … and ${files.length - CONTEXT_PACKAGE_MAX_FILES} more (see the diff below)`)
    }
  }
  return lines.join("\n")
}

/**
 * Discover CLAUDE.md / AGENTS.md files that govern the changed code.
 *
 * Repo-level and ancestor files come first; the user-level file is last so it
 * cannot consume the budget before the project's own rules. Root files get a
 * reserved share, and every non-root source takes only what it needs from the
 * remaining budget.
 */
export function discoverConventions(
  root: string,
  files: string[],
  budget = 20_000,
  home = homedir(),
  options: { pathsOnly?: boolean } = {},
): { paths: string[]; text: string } {
  const dirs = new Set<string>()
  for (const f of files) {
    let d = dirname(join(root, f))
    for (;;) {
      dirs.add(d)
      if (d === root) break
      const parent = dirname(d)
      if (parent === d || !d.startsWith(root)) break
      d = parent
    }
  }
  const candidates: string[] = []
  let rootReal: string
  try {
    rootReal = realpathSync(root)
  } catch {
    rootReal = root
  }
  // A repository-provided symlink must not pull an arbitrary local file into
  // the prompts. Only follow a conventions file whose real path stays inside
  // the repository; the user-level file is allowed outside by design.
  const insideRoot = (p: string): boolean => {
    try {
      const real = realpathSync(p)
      return real === rootReal || real.startsWith(`${rootReal}${sep}`)
    } catch {
      return false
    }
  }
  const ordered = [root, ...[...dirs].filter((d) => d !== root).sort((a, b) => a.length - b.length)]
  for (const dir of ordered) {
    for (const name of ["CLAUDE.md", "CLAUDE.local.md", "AGENTS.md"]) {
      const p = join(dir, name)
      if (existsSync(p) && insideRoot(p)) candidates.push(p)
    }
  }
  const userClaude = join(home, ".claude", "CLAUDE.md")
  if (existsSync(userClaude)) candidates.push(userClaude)
  const paths = uniq(candidates)
  // A cell without a conventions finder still needs the path list: the prompt
  // tells finders to read those files when their lens needs them. Skip only
  // the text reads, not discovery.
  if (options.pathsOnly) return { paths, text: "" }
  const chunks: string[] = []
  const displayName = (p: string): string => {
    const rel = relative(root, p)
    return rel === "" || rel.startsWith("..") || isAbsolute(rel) ? p : rel
  }
  const headerFor = (p: string): string => `### ${displayName(p)}\n`
  // Read sizes first so unused per-source budget can be redistributed. A
  // hand-tuned share truncated a large root file while one-line nested files
  // left most of their share unused.
  const rootPaths = paths.filter((p) => dirname(p) === root)
  const userPath = paths.find((p) => p === userClaude)
  const otherPaths = paths.filter((p) => dirname(p) !== root && p !== userPath)
  // Size each source without reading it in full. The bytes are an upper bound
  // on the character count (UTF-8 never uses fewer bytes than UTF-16 units),
  // so water-filling may allocate a little extra to non-ASCII files; the read
  // below is capped to the final allocation and the total is still enforced.
  const sizes = new Map<string, number>()
  for (const p of paths) {
    try {
      sizes.set(p, statSync(p).size)
    } catch {
      sizes.set(p, 0)
    }
  }
  const sizeOf = (p: string): number => sizes.get(p) ?? 0
  // Headers are part of the budget. Reserve them up front so content caps
  // cannot overrun the total and truncate the last source's text. If many
  // per-directory headers would consume the whole budget, fall back to
  // basenames and keep at least a small content share so project rules are
  // never silently reduced to zero.
  const fullHeaders = paths.map(headerFor)
  let headers = fullHeaders
  let headerBudget = fullHeaders.reduce((sum, header) => sum + header.length, 0)
  if (headerBudget > Math.floor(budget / 2)) {
    headers = paths.map((p) => `### ${basename(p)}\n`)
    headerBudget = headers.reduce((sum, header) => sum + header.length, 0)
  }
  const contentBudget = Math.max(
    Math.min(1024, Math.floor(budget / 2)),
    budget - headerBudget,
  )
  const rootNeeded = rootPaths.reduce((sum, p) => sum + sizeOf(p), 0)
  const otherNeeded = otherPaths.reduce((sum, p) => sum + sizeOf(p), 0)
  const userNeeded = userPath ? sizeOf(userPath) : 0
  // The user-level file is last and must not compete with the project's own
  // rules for the root share. Reserve only a small slice for it; the rest of
  // the budget stays available to the root and nested project files.
  const userReserve = Math.min(userNeeded, 512)
  // Reserve at least half for the root rules, but let the root take as much as
  // it actually needs when the nested files are small. Only project files
  // count here: a large ~/.claude/CLAUDE.md must not cut the root rules in
  // half while the nested files leave the rest of the budget unused.
  const rootShare =
    rootPaths.length === 0
      ? 0
      : otherPaths.length === 0 && userNeeded === 0
        ? contentBudget
        : Math.min(
            rootNeeded,
            Math.max(
              Math.floor(contentBudget * 0.5),
              contentBudget - otherNeeded - userReserve,
            ),
          )
  // Water-fill a budget across sources: small files get their full text and
  // the remaining budget is split evenly among the rest. Precomputing equal
  // caps stranded the unused share of a one-line file, hiding rules from a
  // large root file (or a later package) behind a cap it never needed.
  const waterFill = (sizes: number[], total: number): number[] => {
    if (sizes.length === 0) return []
    if (sizes.reduce((sum, size) => sum + size, 0) <= total) return sizes.slice()
    let lo = 0
    let hi = Math.max(...sizes)
    while (lo < hi) {
      const mid = Math.ceil((lo + hi) / 2)
      const used = sizes.reduce((sum, size) => sum + Math.min(size, mid), 0)
      if (used <= total) lo = mid
      else hi = mid - 1
    }
    const caps = sizes.map((size) => Math.min(size, lo))
    let remaining = total - caps.reduce((sum, cap) => sum + cap, 0)
    for (let i = 0; i < caps.length && remaining > 0; i++) {
      if (caps[i] < sizes[i]) {
        caps[i]++
        remaining--
      }
    }
    return caps
  }
  const rootCaps = waterFill(rootPaths.map(sizeOf), Math.min(rootShare, rootNeeded))
  const rootAlloc = rootCaps.reduce((sum, cap) => sum + cap, 0)
  const otherShare = Math.max(0, contentBudget - rootAlloc)
  const otherPathsForBudget = otherPaths
  const userCap = userPath ? Math.min(userNeeded, userReserve, otherShare) : 0
  const nestedShare = Math.max(0, otherShare - userCap)
  const otherCaps = waterFill(otherPathsForBudget.map(sizeOf), nestedShare)
  const caps = new Map<string, number>()
  rootPaths.forEach((p, i) => caps.set(p, rootCaps[i] ?? 0))
  otherPathsForBudget.forEach((p, i) => caps.set(p, otherCaps[i] ?? 0))
  if (userPath) caps.set(userPath, userCap)
  let used = 0
  let contentUsed = 0
  for (const [i, p] of paths.entries()) {
    if (used >= budget) break
    const header = headers[i] ?? headerFor(p)
    const cap = caps.get(p) ?? 0
    const limit = Math.max(0, Math.min(cap, contentBudget - contentUsed))
    if (limit <= 0) continue
    const text = readCapped(p, limit, sizeOf(p))
    if (!text) continue
    chunks.push(header + text)
    used += header.length + text.length
    contentUsed += text.length
  }
  return { paths, text: chunks.join("\n\n") }
}

function describeScope(
  kind: string,
  ctx: { pr?: number; branch?: string; range?: string; pathspec?: string },
): string {
  switch (kind) {
    case "pr":
      return `pull request #${ctx.pr}`
    case "branch":
      return `branch ${ctx.branch}...HEAD`
    case "path":
      return `path ${ctx.pathspec ?? "."}`
    case "fresh":
      return "fresh repository (no commits yet)"
    case "range":
      return `range ${ctx.range}`
    default:
      return "working tree"
  }
}

type Plan = {
  argv: string[]
  label: string
  range?: string
  staged?: boolean
  pathspec?: string
}

/** A bare number is a PR target. Keep the spelling in one place. */
export function prTargetNumber(target: string | undefined): number | undefined {
  if (target === undefined) return undefined
  // Accept a PR number followed by free-form instructions ("123 focus on
  // auth"), but not a path or identifier that merely starts with digits.
  const match = target.match(/^#?(\d+)(?:\s|$)/)
  return match ? positiveLine(match[1]) : undefined
}

export type TargetClassification = {
  pr?: number
  branchCandidate: boolean
  branchRef?: string
  pathScope?: DiffScope
}

/**
 * Classify a review target exactly once. A bare branch name wins over a
 * same-named directory, while an explicit path (`./name`, `/abs`, `name/`)
 * always stays a path. Scope discovery and host detection both use this, so
 * they cannot send the review and the comment host to different repositories.
 */
export async function classifyTarget(
  exec: Exec,
  cwd: string,
  target: string | undefined,
  opts?: ExecOptions,
): Promise<TargetClassification> {
  const pr = prTargetNumber(target)
  let pathScope = target && pr === undefined ? resolveDiffScope(cwd, target) : undefined
  // HEAD is the current checkout, not a branch to diff against itself. Treat
  // it as the default range so uncommitted changes are reviewed.
  if (target && target.toUpperCase() === "HEAD") {
    return {
      ...(pr !== undefined ? { pr } : {}),
      branchCandidate: false,
      ...(pathScope ? { pathScope } : {}),
    }
  }
  if (target && !explicitPathTarget(target) && pr === undefined && !looksLikeRange(target)) {
    const branchRoot = findGitRoot(cwd) ?? cwd
    if (await revParse(exec, branchRoot, target, opts)) {
      return { ...(pr !== undefined ? { pr } : {}), branchCandidate: true, branchRef: target }
    }
    // A remote-only branch is still a valid target; resolve the
    // remote-tracking ref before falling through to the default ladder.
    const remoteRef = await resolveRemoteBranch(exec, branchRoot, target, opts)
    if (remoteRef) {
      return { ...(pr !== undefined ? { pr } : {}), branchCandidate: true, branchRef: remoteRef }
    }
  }
  return {
    ...(pr !== undefined ? { pr } : {}),
    branchCandidate: false,
    ...(pathScope ? { pathScope } : {}),
  }
}

/**
 * The repository a review target belongs to, without downloading a diff. Used
 * to choose the comment host before the engine resolves the full scope.
 */
export async function resolveReviewRoot(
  cwd: string,
  target: string | undefined,
  exec: Exec = defaultExec,
  opts?: ExecOptions,
  classifiedTarget?: TargetClassification,
): Promise<string | null> {
  const trimmed = target?.trim() || undefined
  if (!trimmed) return findGitRoot(cwd)
  const classified = classifiedTarget ?? (await classifyTarget(exec, cwd, trimmed, opts))
  if (classified.pr !== undefined || classified.branchCandidate) return findGitRoot(cwd)
  if (classified.pathScope) return classified.pathScope.root
  const hint = extractPathHint(trimmed, cwd)
  if (hint) {
    const hinted = resolveDiffScope(cwd, hint)
    if (hinted) return hinted.root
  }
  return findGitRoot(cwd)
}

/** `gh pr diff --name-only` emits one path per line; only a CR can be noise. */
function nameOnlyPaths(stdout: string): string[] {
  return stdout
    .split("\n")
    .map((line) => (line.endsWith("\r") ? line.slice(0, -1) : line))
    .filter((line) => line.length > 0)
}

export async function resolveScope(opts: ScopeOptions): Promise<Scope> {
  const exec = opts.exec ?? defaultExec
  const cwd = opts.cwd
  const target = opts.target?.trim() || undefined
  // No wall-clock cap by default: a large PR diff on a slow connection must be
  // allowed to finish. Set CODE_REVIEW_SCOPE_TIMEOUT_MS to bound discovery.
  const scopeTimeout = opts.scopeTimeoutMs ?? envInt("CODE_REVIEW_SCOPE_TIMEOUT_MS")
  const timeoutSuffix = scopeTimeout !== undefined ? ` after ${scopeTimeout}ms` : ""
  const callOpts = (timeoutMs = scopeTimeout): ExecOptions => ({
    ...(opts.signal ? { signal: opts.signal } : {}),
    ...(timeoutMs !== undefined && timeoutMs > 0 ? { timeoutMs } : {}),
  })

  // An explicit path that does not exist must not silently fall back to the
  // whole working-tree diff. A typo is a target error, not a review of every
  // changed file.
  const missingExplicit = missingExplicitPathTarget(cwd, target)
  if (missingExplicit !== undefined) {
    throw new Error(`Review target path not found: ${missingExplicit}`)
  }

  // A bare number is a PR target. Resolve it as a path only when the user
  // forced path form (`./42`, `42/`); otherwise a same-named directory or
  // submodule would redirect the `gh pr` calls into another repository.
  const classified = opts.classification ?? (await classifyTarget(exec, cwd, target, callOpts()))
  const targetPr = classified.pr
  let pathScope = classified.pathScope
  const branchCandidate = classified.branchCandidate
  const branchRef = classified.branchRef
  // A repo-relative path typo (src/authn.ts) is as much a target error as
  // ./src/authn.ts. Do not silently review the whole default diff. A free-form
  // instruction contains spaces and keeps its fallback behavior.
  if (
    target &&
    targetPr === undefined &&
    !branchCandidate &&
    !looksLikeRange(target) &&
    !target.includes(" ") &&
    (target.includes("/") || /\.[a-z0-9]{1,8}$/i.test(target)) &&
    resolveTargetPath(cwd, target) === null
  ) {
    throw new Error(`Review target path not found: ${target}`)
  }
  if (
    target &&
    targetPr === undefined &&
    !branchCandidate &&
    resolveTargetPath(cwd, target) !== null &&
    pathScope === undefined
  ) {
    throw new Error("Review target is not inside a git repository.")
  }

  let root: string
  if (pathScope) {
    root = pathScope.root
  } else {
    const top = await git(exec, cwd, ["rev-parse", "--show-toplevel"], callOpts())
    assertExec(top, "git rev-parse", timeoutSuffix)
    if (top.code !== 0 || !top.stdout.trim()) {
      throw new Error("Not a git repository — /code-review-opencode needs one to discover a diff.")
    }
    // Strip only the line terminator git adds. A repository path may legally
    // end (or begin) with a space, and trimming would run later commands in a
    // different directory.
    // Strip exactly the one line terminator git appends. A legal directory
    // name may itself end in a newline; deleting the whole trailing run would
    // silently run every later command in a different directory.
    root = top.stdout.replace(/\r?\n$/, "")
  }
  let gitCwd = root
  let isPathTarget = pathScope?.isPath === true
  let pathspec = isPathTarget ? pathScope?.relPath ?? undefined : undefined

  // `@name` is tried as a branch above, then falls back to its path. A user
  // can force a path with `./name` or a trailing slash.
  //
  // A free-form instruction can name a path without being one itself.
  if (target && !branchCandidate && !isPathTarget && targetPr === undefined && !looksLikeRange(target)) {
    const hint = extractPathHint(target, cwd)
    if (hint) {
      const hinted = resolveDiffScope(cwd, hint)
      if (hinted?.isPath) {
        pathScope = hinted
        root = hinted.root
        gitCwd = root
        isPathTarget = true
        pathspec = hinted.relPath ?? undefined
      }
    }
  }

  const plan: Plan[] = []
  let pr: number | undefined
  let branch: string | undefined
  let range: string | undefined
  let diffBase: string | undefined
  let scopeKind = "worktree"
  let patch: string | undefined
  /** The final metadata payload, parsed once. */
  let prMetaJson: PrMeta | undefined
  /** The patch was captured between two matching PR-head reads. */
  let prHeadVerified = false
  let firstFiles: string[] | undefined
  let firstFilesFailed = false
  const warnings: string[] = []

  const add = (spec: DiffSpec) => {
    plan.push({ argv: diffArgv(spec), label: labelFor(spec, root, cwd), ...spec })
  }

  if (targetPr !== undefined) {
    pr = targetPr
    // The patch and metadata are separate live reads. When --comment will pin
    // the head, bracket the patch between two cheap head-only reads and run
    // the two big downloads concurrently: a matching pair proves the patch
    // belongs to the head that --comment will use. A review that will not post
    // comments skips the head reads entirely.
    const readMeta = () =>
      exec(
        ["gh", "pr", "view", String(pr), "--json", "files,additions,deletions,headRefOid,url"],
        gitCwd,
        callOpts(),
      )
    const readPatch = () => exec(["gh", "pr", "diff", String(pr)], gitCwd, callOpts())
    const parseMeta = (result: ExecResult | undefined): PrMeta | undefined => {
      if (!result || result.code !== 0) return undefined
      try {
        return JSON.parse(result.stdout) as PrMeta
      } catch {
        return undefined
      }
    }
    /** One head-only read, retried once on a transient failure. */
    const readHead = async (): Promise<string | undefined> => {
      for (let attempt = 0; attempt < 2; attempt++) {
        const result = await exec(
          ["gh", "pr", "view", String(pr), "--json", "headRefOid"],
          gitCwd,
          callOpts(),
        )
        if (result.aborted) return undefined
        const value = parseMeta(result)
        if (typeof value?.headRefOid === "string" && value.headRefOid) return value.headRefOid
      }
      return undefined
    }
    const verifyHead = opts.verifyPrHead !== false
    let headBefore = verifyHead ? await readHead() : undefined
    let [meta, gh] = await Promise.all([readMeta(), readPatch()])
    let metaJson = parseMeta(meta)
    let headAfter = verifyHead ? await readHead() : undefined
    const headMoved =
      headBefore !== undefined && headAfter !== undefined && headBefore !== headAfter
    const metaDisagrees =
      headAfter !== undefined &&
      typeof metaJson?.headRefOid === "string" &&
      metaJson.headRefOid !== headAfter
    if (verifyHead && (headMoved || metaDisagrees)) {
      // The head moved while the pair was being fetched; take one fresh pair.
      headBefore = await readHead()
      ;[meta, gh] = await Promise.all([readMeta(), readPatch()])
      metaJson = parseMeta(meta)
      headAfter = await readHead()
    }
    prMetaJson = metaJson
    const reviewedHead =
      headAfter ?? (typeof metaJson?.headRefOid === "string" ? metaJson.headRefOid : undefined)
    // An unavailable head read is not proof that the patch matches. Only a
    // bracketed pair that agrees with the metadata authorizes pinning; a
    // failed check leaves prHeadOid unset so posting refuses to use stale
    // anchors. The one retry above keeps a transient gh failure from
    // disabling inline comments in the common case.
    prHeadVerified =
      reviewedHead !== undefined &&
      (!verifyHead ||
        (headBefore !== undefined &&
          headAfter !== undefined &&
          headBefore === headAfter &&
          (typeof metaJson?.headRefOid !== "string" || metaJson.headRefOid === headAfter)))
    assertExec(gh, "gh pr diff", timeoutSuffix, "PR diff discovery was cancelled.")
    if (gh.code !== 0) {
      throw new Error(`Could not fetch PR #${pr} with gh: ${gh.stderr.trim() || "gh is unavailable"}`)
    }
    // A metadata timeout or malformed response is not a review failure: the
    // patch scan can recover the file list, and --comment refuses because the
    // head was not verified. Cancellation still stops the whole review.
    if (meta.aborted) throw new Error("PR metadata discovery was cancelled.")
    // One patch download: this stdout is also the diff text below.
    patch = gh.stdout
    plan.push({ argv: ["gh", "pr", "diff", String(pr)], label: `gh pr diff ${pr}` })
    scopeKind = "pr"
  } else if (target && !isPathTarget && looksLikeRange(target)) {
    range = target
    add({ range, pathspec })
    // The reference's Phase 0 reviews committed range changes and the
    // uncommitted working tree together. An explicit range is no exception.
    const dirtyProbe = await git(exec, gitCwd, quietArgs({ range: "HEAD", pathspec }), callOpts())
    assertExec(dirtyProbe, "git diff", timeoutSuffix)
    if (dirtyProbe.code > 1) {
      // A failed probe is not a clean worktree. Treating exit 128 as clean
      // silently omits uncommitted changes from an explicit-range review.
      throw new Error(
        `git diff --quiet failed while checking the working tree (${dirtyProbe.stderr.trim() || `exit ${dirtyProbe.code}`}).`,
      )
    }
    if (dirtyProbe.code === 1) add({ range: "HEAD", pathspec })
    scopeKind = "range"
  } else if (target && branchCandidate) {
    // `scope.branch` stays the user's name (the PR head branch), while the
    // diff base uses the resolved ref, which may carry a remote prefix.
    branch = target
    const baseRef = branchRef ?? target
    range = `${baseRef}...HEAD`
    diffBase = baseRef
    add({ range, pathspec })
    // The reference's branch review also includes uncommitted changes when
    // that branch is the checked-out one. A remote-only target must not pull
    // in edits from whichever local branch happens to be current.
    const [current, fullRef] = await Promise.all([
      git(exec, gitCwd, ["rev-parse", "--abbrev-ref", "HEAD"], callOpts()),
      git(exec, gitCwd, ["rev-parse", "--symbolic-full-name", branchRef ?? target], callOpts()),
    ])
    assertExec(current, "git rev-parse", timeoutSuffix)
    assertExec(fullRef, "git rev-parse", timeoutSuffix)
    const currentName = current.stdout.trim()
    // A remote-tracking or qualified target can name the checked-out branch
    // without being byte-identical to its abbreviated name. The same helper
    // posting uses keeps the remote-prefix rule in one place.
    const full = fullRef.code === 0 ? fullRef.stdout.trim() : ""
    // A remote-tracking target (`origin/main`) names the checked-out branch
    // without being byte-identical to its abbreviated name. The
    // `refs/remotes/` guard keeps a local branch named `origin/main` from
    // being treated as a remote-tracking ref and pulling in unrelated
    // worktree edits.
    const fullIsRemote = full.startsWith("refs/remotes/")
    let sameBranch =
      currentName === normalizeRef(target) ||
      currentName === normalizeRef(branchRef ?? target)
    if (!sameBranch && fullIsRemote) {
      const remotes = await git(exec, gitCwd, ["remote"], callOpts())
      assertExec(remotes, "git remote", timeoutSuffix)
      const remoteNames =
        remotes.code === 0 ? remotes.stdout.trim().split(/\s+/).filter(Boolean) : []
      sameBranch = sameRefName(full, currentName, remoteNames)
    }
    if (current.code === 0 && sameBranch) {
      const [worktree, listed] = await Promise.all([
        git(exec, gitCwd, quietArgs({ range: "HEAD", pathspec }), callOpts()),
        listFiles(exec, gitCwd, nameArgv({ range, pathspec }), callOpts()),
      ])
      assertExec(worktree, "git diff", timeoutSuffix)
      if (worktree.code > 1) {
        throw new Error(
          `git diff --quiet failed while checking the working tree (${worktree.stderr.trim() || `exit ${worktree.code}`}).`,
        )
      }
      // The range is the first plan entry; reuse this listing instead of
      // running the same name-status command again below.
      firstFiles = listed.files
      firstFilesFailed = !listed.ok
      if (worktree.code === 1 || listed.files.length === 0) add({ range: "HEAD", pathspec })
    }
    scopeKind = "branch"
  } else {
    const hasHead = await revParse(exec, gitCwd, "HEAD", callOpts())
    if (!hasHead) {
      // Fresh repository: `git diff HEAD` cannot resolve. The index and the
      // worktree are the only real scopes; include both.
      add({ staged: true, pathspec })
      add({ pathspec })
      scopeKind = "fresh"
    } else {
      // Prefer the upstream range, then main, then HEAD~1. `diff --quiet`
      // exits 1 when the range is non-empty, 0 when it is empty, >1 when the
      // revision is unknown.
      let probe: string | undefined
      for (const candidate of ["@{upstream}...HEAD", "main...HEAD", "HEAD~1"]) {
        const r = await git(exec, gitCwd, quietArgs({ range: candidate, pathspec }), callOpts())
        assertExec(r, "git diff", timeoutSuffix)
        // The ladder is by preference, not by non-emptiness. Once a candidate
        // resolves, it wins even when its range is clean; continuing lets a
        // non-empty HEAD~1 replace an empty upstream range and review the last
        // already-merged commit as if it were the current change.
        if (r.code === 0 || r.code === 1) {
          probe = candidate
          break
        }
      }
      // A one-commit repository has no HEAD~1 and no upstream/main. HEAD is
      // still a valid revision and is the only available diff base; using the
      // rejected literal would turn a clean checkout into a failed review.
      range = probe ?? "HEAD"
      const probeBase = probe?.includes("...") ? probe.split("...")[0] : undefined
      // The upstream name does not depend on the worktree probe; run it in the
      // same batch instead of paying a serial git round-trip first.
      const upstreamPromise =
        probeBase === "@{upstream}"
          ? git(exec, gitCwd, ["rev-parse", "--abbrev-ref", "@{upstream}"], callOpts())
          : undefined
      const [upstream, worktree, listed] = await Promise.all([
        upstreamPromise ?? Promise.resolve(undefined),
        git(exec, gitCwd, quietArgs({ range: "HEAD", pathspec }), callOpts()),
        listFiles(exec, gitCwd, nameArgv({ range, pathspec }), callOpts()),
      ])
      if (upstream && upstream.code === 0) diffBase = upstream.stdout.trim()
      else if (probeBase !== undefined && probeBase !== "@{upstream}" && probeBase !== "HEAD~1") {
        diffBase = probeBase
      }
      assertExec(worktree, "git diff", timeoutSuffix)
      // `--quiet` uses 0 for clean and 1 for differences. Any other status is
      // a failure; treating it as clean silently drops uncommitted changes.
      if (worktree.code > 1) {
        throw new Error(
          `git diff --quiet failed while checking the working tree (${worktree.stderr.trim() || `exit ${worktree.code}`}).`,
        )
      }
      const dirty = worktree.code === 1
      firstFiles = listed.files
      firstFilesFailed = !listed.ok
      add({ range, pathspec })
      // A single-revision diff (`HEAD`, `HEAD~1`) already compares that commit
      // with the working tree, so adding `git diff HEAD` would duplicate every
      // uncommitted hunk. Only a multi-commit range (`main...HEAD`) needs the
      // separate worktree entry.
      if (range.includes("..") && (dirty || firstFiles.length === 0)) add({ range: "HEAD", pathspec })
      // A clean checkout with no explicit target — or with a path/free-form
      // instruction — is still the current branch's review. Record that branch
      // so --comment can resolve its PR; keep the scopeKind "path"/"range" so
      // an explicit range target remains non-postable.
      const currentCheckoutTarget =
        target === undefined ||
        (targetPr === undefined && !branchCandidate && !looksLikeRange(target))
      if (currentCheckoutTarget && !dirty) {
        const current = await git(exec, gitCwd, ["rev-parse", "--abbrev-ref", "HEAD"], callOpts())
        const name = current.stdout.trim()
        if (current.code === 0 && name && name !== "HEAD") branch = name
      }
      scopeKind = isPathTarget ? "path" : dirty ? "worktree" : "range"
    }
  }

  // The plan entries are independent of the name-status listings, so start
  // the patch captures now and let them overlap the listing probes. The
  // all-listings-failed path below awaits this promise before throwing so no
  // capture child is left running and buffering.
  const capturesPromise =
    pr === undefined ? Promise.all(plan.map((p) => exec(p.argv, gitCwd, callOpts()))) : undefined

  let files: string[] = []
  let prHeadOid: string | undefined
  let prUrl: string | undefined
  let diffLines = 0
  if (pr !== undefined) {
    // One metadata call covers the file list and the finder-budget line count.
    // The PR branch above parsed it once; do not re-parse the same payload.
    const parsed: PrMeta | undefined = prMetaJson
    if (parsed?.files && parsed.files.length > 0) {
      files = parsed.files.map((f) => f.path ?? "").filter(Boolean)
    }
    if (
      prHeadVerified &&
      typeof parsed?.headRefOid === "string" &&
      parsed.headRefOid
    ) {
      prHeadOid = parsed.headRefOid
    }
    if (typeof parsed?.url === "string" && parsed.url) prUrl = parsed.url
    // A missing or unverified head is a comment-only concern: the patch and
    // file list may still be complete. `postComments` refuses inline anchors
    // when `prHeadOid` is unset, so this must not mark the review partial.
    if (opts.includeDiffLines !== false) {
      if (typeof parsed?.additions === "number" && typeof parsed.deletions === "number") {
        diffLines = parsed.additions + parsed.deletions
      }
      // A failed metadata call falls back to the one patch scan after capture.
    }
  } else {
    // The plan entries are independent git calls; run them together instead
    // of paying one process round-trip per entry.
    const listings = await Promise.all(
      plan.map((p, i) => {
        if (i === 0 && firstFiles !== undefined) {
          return Promise.resolve({ files: firstFiles, ok: !firstFilesFailed })
        }
        return listFiles(
          exec,
          gitCwd,
          nameArgv({ range: p.range, staged: p.staged, pathspec: p.pathspec }),
          callOpts(),
        )
      }),
    )
    let listFailures = 0
    for (const [i, listed] of listings.entries()) {
      if (!listed.ok) {
        listFailures++
        warnings.push(`${plan[i].label}: could not list changed files`)
      }
      files.push(...listed.files)
    }
    if (listFailures === plan.length && plan.length > 0) {
      // Every listing failed. Returning an empty scope would render as the
      // confident "No changes found to review" result for an unreviewed diff.
      // Let the already-started capture children settle first so none is left
      // running and buffering after the throw.
      await capturesPromise
      throw new Error(
        `Could not list changed files with git (${warnings.join("; ")}). The review did not run.`,
      )
    }
  }

  let uniqueFiles = uniq(files).sort()
  const scopeLabel = describeScope(scopeKind, { pr, branch, range, pathspec })
  const diffCommands = plan.map((p) => p.label)

  // Capture each diff command once. For a PR, the cached patch is the diff.
  const chunks: string[] = []
  let captureFailures = 0
  /** Plan entries whose diff capture failed, for the numstat fallback. */
  const failedPlanIndices: number[] = []
  if (pr !== undefined) {
    if (patch && patch.trim()) chunks.push(patch)
  } else {
    const captures = await capturesPromise!
    for (const [i, r] of captures.entries()) {
      if (r.aborted) throw new Error("Diff discovery was cancelled.")
      if (r.code === 0) {
        if (r.stdout.trim()) chunks.push(r.stdout)
      } else {
        captureFailures++
        failedPlanIndices.push(i)
        warnings.push(
          `${plan[i].label}: ${r.timedOut ? "timed out" : r.stderr.trim() || `git exited ${r.code}`}`,
        )
      }
    }
    if (captureFailures === plan.length && plan.length > 0) {
      throw new Error(
        `Could not read the diff with git (${warnings.join("; ")}). The review did not run.`,
      )
    }
  }
  const diffText = chunks.join("\n")

  // One patch scan feeds the recovered file list, the finder budget, and the
  // context package. A successful patch capture with an empty (or partially
  // failed) name-status listing still names every changed file; a large diff is
  // walked once instead of once per consumer.
  const patchScan = /\S/.test(diffText) ? scanPatchChurn(diffText) : undefined
  if (patchScan) uniqueFiles = uniq([...uniqueFiles, ...patchScan.paths]).sort()
  // A PR can have changes that produce no parseable patch blocks (binary-only
  // assets), and its metadata call can fail. When both file sources are empty,
  // ask gh for the names rather than reporting "No changes found" for a PR
  // that really changed files.
  if (pr !== undefined && uniqueFiles.length === 0) {
    const names = await exec(["gh", "pr", "diff", String(pr), "--name-only"], gitCwd, callOpts())
    assertExec(names, "gh pr diff", timeoutSuffix, "PR diff discovery was cancelled.")
    if (names.code === 0) {
      uniqueFiles = uniq(nameOnlyPaths(names.stdout)).sort()
    } else {
      warnings.push(`PR #${pr}: could not list changed files (${names.stderr.trim() || "gh is unavailable"})`)
    }
  }
  if (opts.includeDiffLines !== false && diffLines === 0 && patchScan) diffLines = patchScan.total
  // A partially failed capture would make the patch scan undercount the diff,
  // shrinking the finder budget for exactly the large change set that needs
  // it. Ask numstat for every plan entry and use its independent total.
  if (opts.includeDiffLines !== false && captureFailures > 0) {
    const counts = await Promise.all(
      failedPlanIndices.map((i) => {
        const p = plan[i]
        return git(
          exec,
          gitCwd,
          gitDiffArgs({ range: p.range, staged: p.staged, pathspec: p.pathspec }, "numstat"),
          callOpts(opts.numstatTimeoutMs ?? 30_000),
        )
      }),
    )
    let counted = 0
    let any = false
    for (const r of counts) {
      if (r.code !== 0) continue
      any = true
      counted += numstatTotal(r.stdout)
    }
    if (any) diffLines += counted
  }

  const context = buildContextPackage(diffText, root, scopeLabel, uniqueFiles, patchScan?.files)
  const summary =
    uniqueFiles.length === 0
      ? "No changes found."
      : `${pluralize(uniqueFiles.length, "changed file")} (${scopeLabel}).`

  // Nothing to review means nothing to govern: skip the ancestor walk and the
  // CLAUDE.md/AGENTS.md reads the caller will never render. A cell without a
  // conventions finder still gets the path list; only the text is skipped.
  const conventions =
    uniqueFiles.length === 0
      ? { paths: [] as string[], text: "" }
      : discoverConventions(root, uniqueFiles, opts.conventionsBudget, undefined, {
          pathsOnly: opts.includeConventions === false,
        })

  return {
    diffCommand: diffCommands.join(" ; "),
    diffCommands,
    files: uniqueFiles,
    claudeMdFiles: conventions.paths,
    summary,
    conventions: conventions.text || "(none noted)",
    target,
    root,
    pr,
    ...(prHeadOid ? { prHeadOid } : {}),
    ...(prUrl ? { prUrl } : {}),
    branch,
    diffLines,
    diffText,
    scopeKind,
    ...(diffBase ? { diffBase } : {}),
    context,
    ...(warnings.length > 0 ? { warnings } : {}),
  }
}
