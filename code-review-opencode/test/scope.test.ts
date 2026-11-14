import { test } from "node:test"
import assert from "node:assert/strict"
import { execFileSync } from "node:child_process"
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, realpathSync, symlinkSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import {
  buildContextPackage,
  defaultExec,
  diffSideMap,
  discoverConventions,
  readCapped,
  scanPatchChurn,
  resolveDiffScope,
  resolveScope,
  unquoteGitPath,
  type Exec,
} from "../.opencode/plugins/code-review-opencode/scope.ts"

/** Test-only convenience wrapper; production uses diffSideMap directly. */
function diffSideForLine(patch: string | undefined, file: string, line: number): "RIGHT" | "LEFT" {
  if (!patch || !Number.isFinite(line)) return "RIGHT"
  return diffSideMap(patch, [{ file, line }]).sideFor(file, line)
}

function scanPatchChurnForTest(patch: string) {
  return new Map(
    [...scanPatchChurn(patch).paths]
      .filter((file) => file.startsWith("src/"))
      .map((file) => [file, { added: 1, removed: 1, binary: false }] as const),
  )
}

test("changed files are recovered from a patch when gh pr view fails", () => {
  const patch = [
    "diff --git a/src/a.ts b/src/a.ts",
    "--- a/src/a.ts",
    "+++ b/src/a.ts",
    "@@ -1 +1 @@",
    "-a",
    "+b",
    "diff --git a/old.ts b/new.ts",
    "--- a/old.ts",
    "+++ b/new.ts",
  ].join("\n")
  assert.deepEqual([...scanPatchChurn(patch).paths], ["src/a.ts", "old.ts", "new.ts"])
})

function git(cwd: string, ...args: string[]) {
  return execFileSync("git", args, { cwd, encoding: "utf8" })
}

function makeRepo(branch = "main"): string {
  const dir = mkdtempSync(join(tmpdir(), "code-review-scope-"))
  git(dir, "init", "-b", branch)
  git(dir, "config", "user.email", "test@example.com")
  git(dir, "config", "user.name", "Test")
  writeFileSync(join(dir, "a.ts"), "export const a = 1\n")
  writeFileSync(join(dir, "b.ts"), "export const b = 2\n")
  git(dir, "add", ".")
  git(dir, "commit", "-m", "base")
  return dir
}

test("not a git repository is a hard error", async () => {
  const dir = mkdtempSync(join(tmpdir(), "code-review-nogit-"))
  await assert.rejects(() => resolveScope({ cwd: dir }), /Not a git repository/)
  rmSync(dir, { recursive: true, force: true })
})

test("uncommitted working-tree changes are in scope", async () => {
  const dir = makeRepo()
  writeFileSync(join(dir, "a.ts"), "export const a = 2\n")
  const scope = await resolveScope({ cwd: dir })
  assert.deepEqual(scope.files, ["a.ts"])
  assert.match(scope.diffCommand, /git .*diff .*--end-of-options HEAD/)
  assert.match(scope.diffText ?? "", /export const a = 2/)
  rmSync(dir, { recursive: true, force: true })
})

test("committed feature branch diffs against main", async () => {
  const dir = makeRepo()
  git(dir, "checkout", "-b", "feature")
  writeFileSync(join(dir, "b.ts"), "export const b = 3\n")
  git(dir, "add", ".")
  git(dir, "commit", "-m", "change b")
  const scope = await resolveScope({ cwd: dir })
  assert.deepEqual(scope.files, ["b.ts"])
  assert.match(scope.diffCommand, /main\.\.\.HEAD/)
  assert.equal(scope.scopeKind, "range")
  assert.equal(scope.branch, "feature")
  assert.equal(scope.diffBase, "main")
  assert.match(scope.diffText ?? "", /export const b = 3/)
  rmSync(dir, { recursive: true, force: true })
})

test("an explicit ref range is used verbatim", async () => {
  const dir = makeRepo()
  writeFileSync(join(dir, "a.ts"), "export const a = 9\n")
  git(dir, "add", ".")
  git(dir, "commit", "-m", "change a")
  const scope = await resolveScope({ cwd: dir, target: "HEAD~1..HEAD" })
  assert.deepEqual(scope.files, ["a.ts"])
  assert.match(scope.diffCommand, /HEAD~1\.\.HEAD/)
  rmSync(dir, { recursive: true, force: true })
})

test("an explicit branch diffs branch...HEAD", async () => {
  const dir = makeRepo()
  git(dir, "checkout", "-b", "feature")
  writeFileSync(join(dir, "a.ts"), "export const a = 7\n")
  git(dir, "add", ".")
  git(dir, "commit", "-m", "change a")
  const scope = await resolveScope({ cwd: dir, target: "main" })
  assert.deepEqual(scope.files, ["a.ts"])
  assert.match(scope.diffCommand, /main\.\.\.HEAD/)
  rmSync(dir, { recursive: true, force: true })
})

test("a failed worktree probe in an explicit range is an error", async () => {
  const dir = makeRepo()
  writeFileSync(join(dir, "a.ts"), "export const a = 9\n")
  const exec: Exec = async (argv, cwd, opts) => {
    if (argv.includes("diff") && argv.includes("--quiet") && argv.includes("HEAD")) {
      return { code: 128, stdout: "", stderr: "fatal: index file corrupt" }
    }
    return defaultExec(argv, cwd, opts)
  }
  await assert.rejects(
    () => resolveScope({ cwd: dir, target: "main...HEAD", exec }),
    /git diff --quiet failed/,
  )
  rmSync(dir, { recursive: true, force: true })
})

test("a remote-prefixed current branch includes uncommitted changes", async () => {
  const dir = makeRepo()
  git(dir, "remote", "add", "origin", "https://example.com/acme/app.git")
  git(dir, "update-ref", "refs/remotes/origin/main", "HEAD")
  writeFileSync(join(dir, "a.ts"), "export const a = 42\n")
  const scope = await resolveScope({ cwd: dir, target: "origin/main" })
  assert.equal(scope.diffBase, "origin/main")
  assert.match(scope.diffText ?? "", /a = 42/)
  assert.ok(scope.diffCommands?.some((command) => command.includes("HEAD")))
  rmSync(dir, { recursive: true, force: true })
})

test("a failed symbolic-full-name probe does not fail a branch review", async () => {
  const dir = makeRepo()
  git(dir, "checkout", "-b", "feature")
  writeFileSync(join(dir, "a.ts"), "export const a = 9\n")
  const exec: Exec = async (argv, cwd, opts) => {
    if (
      argv[0] === "git" &&
      argv.includes("rev-parse") &&
      argv.includes("--symbolic-full-name")
    ) {
      return { code: 128, stdout: "", stderr: "bad revision" }
    }
    return defaultExec(argv, cwd, opts)
  }
  const scope = await resolveScope({ cwd: dir, target: "feature", exec })
  // The refinement probe is optional; the exact abbreviated-name match still
  // identifies the checked-out branch and includes its worktree changes.
  assert.equal(scope.branch, "feature")
  assert.match(scope.diffText ?? "", /a = 9/)
  rmSync(dir, { recursive: true, force: true })
})

test("a timed-out current-branch probe skips worktree inclusion", async () => {
  const dir = makeRepo()
  git(dir, "remote", "add", "origin", "https://example.com/acme/app.git")
  git(dir, "update-ref", "refs/remotes/origin/feature", "HEAD")
  git(dir, "checkout", "-b", "feature")
  writeFileSync(join(dir, "a.ts"), "export const a = 9\n")
  git(dir, "add", "a.ts")
  git(dir, "commit", "-m", "committed change")
  writeFileSync(join(dir, "a.ts"), "export const a = 10\n")
  const exec: Exec = async (argv, cwd, opts) => {
    if (argv[0] === "git" && argv.includes("rev-parse") && argv.includes("--abbrev-ref")) {
      return { code: 1, stdout: "", stderr: "timed out", timedOut: true }
    }
    return defaultExec(argv, cwd, opts)
  }
  const scope = await resolveScope({ cwd: dir, target: "origin/feature", exec })
  // The committed range is still reviewed; only the optional worktree
  // inclusion is skipped.
  assert.match(scope.diffText ?? "", /a = 9/)
  assert.doesNotMatch(scope.diffText ?? "", /a = 10/)
  rmSync(dir, { recursive: true, force: true })
})

test("a path with a shell metacharacter omits the runnable command", async () => {
  const dir = makeRepo()
  writeFileSync(join(dir, "a&b.ts"), "export const amp = 1\n")
  git(dir, "add", "a&b.ts")
  const scope = await resolveScope({ cwd: dir, target: "a&b.ts" })
  assert.deepEqual(scope.files, ["a&b.ts"])
  // The host permission table matches the raw command string, so a quoted
  // `&` would still be denied. Omitting only the pathspec would let the finder
  // review the whole range, so the command is omitted entirely; the captured
  // diff remains scoped to the target.
  assert.doesNotMatch(scope.diffCommand, /&/)
  assert.match(scope.diffCommand, /command omitted/)
  assert.match(scope.diffText ?? "", /amp = 1/)
  rmSync(dir, { recursive: true, force: true })
})

test("a path containing a denied substring omits the runnable command", async () => {
  const dir = makeRepo()
  mkdirSync(join(dir, "tools", "difftool"), { recursive: true })
  writeFileSync(join(dir, "tools/difftool/a.ts"), "export const a = 1\n")
  git(dir, "add", "tools/difftool/a.ts")
  const scope = await resolveScope({ cwd: dir, target: "tools/difftool" })
  // `difftool` is a policy deny substring, not just a control character.
  assert.match(scope.diffCommand, /command omitted/)
  assert.doesNotMatch(scope.diffCommand, /difftool/)
  rmSync(dir, { recursive: true, force: true })
})

test("a tab in a path stays in the runnable command", async () => {
  const dir = makeRepo()
  writeFileSync(join(dir, "a\tb.ts"), "export const tab = 1\n")
  git(dir, "add", "a\tb.ts")
  const scope = await resolveScope({ cwd: dir, target: "a\tb.ts" })
  assert.deepEqual(scope.files, ["a\tb.ts"])
  assert.doesNotMatch(scope.diffCommand, /pathspec omitted/)
  assert.ok(scope.diffCommand.includes("a\tb.ts"))
  rmSync(dir, { recursive: true, force: true })
})

test("a repository root with a shell metacharacter uses a relative -C path", async () => {
  const base = mkdtempSync(join(tmpdir(), "code-review-root-"))
  const dir = join(base, "a&b")
  mkdirSync(dir)
  git(dir, "init", "-b", "main")
  git(dir, "config", "user.email", "test@example.com")
  git(dir, "config", "user.name", "Test")
  writeFileSync(join(dir, "a.ts"), "export const a = 1\n")
  git(dir, "add", "a.ts")
  git(dir, "commit", "-m", "base")
  git(dir, "checkout", "-b", "feature")
  writeFileSync(join(dir, "a.ts"), "export const a = 2\n")
  git(dir, "add", "a.ts")
  git(dir, "commit", "-m", "change")
  const sub = join(dir, "sub")
  mkdirSync(sub)
  const scope = await resolveScope({ cwd: sub })
  // The absolute root contains `&`, which the child deny rules reject. The
  // session cwd is inside the root, so `..` is a safe relative -C path.
  assert.match(scope.diffCommand, /git -C \.\./)
  assert.doesNotMatch(scope.diffCommand, /a&b/)
  rmSync(base, { recursive: true, force: true })
})

test("a branch target with a shell metacharacter omits the runnable command", async () => {
  const dir = makeRepo()
  git(dir, "checkout", "-b", "release/a&b")
  writeFileSync(join(dir, "a.ts"), "export const a = 3\n")
  git(dir, "add", "a.ts")
  git(dir, "commit", "-m", "change")
  const scope = await resolveScope({ cwd: dir, target: "release/a&b" })
  // The range is the user's branch name; the child deny rules would reject
  // `&`, so the displayed command is omitted. The embedded diff is still scoped.
  assert.match(scope.diffCommand, /command omitted: shell metacharacter in the review range/)
  assert.doesNotMatch(scope.diffCommand, /&/)
  rmSync(dir, { recursive: true, force: true })
})

test("a clean path target records the checked-out branch", async () => {
  const dir = makeRepo()
  const scope = await resolveScope({ cwd: dir, target: "a.ts" })
  assert.equal(scope.scopeKind, "path")
  assert.equal(scope.branch, "main")
  rmSync(dir, { recursive: true, force: true })
})

test("a path target restricts the diff", async () => {
  const dir = makeRepo()
  writeFileSync(join(dir, "a.ts"), "export const a = 3\n")
  writeFileSync(join(dir, "b.ts"), "export const b = 4\n")
  const scope = await resolveScope({ cwd: dir, target: "a.ts" })
  assert.deepEqual(scope.files, ["a.ts"])
  assert.match(scope.diffCommand, /-- a\.ts/)
  rmSync(dir, { recursive: true, force: true })
})

test("deleted files stay in scope", async () => {
  const dir = makeRepo()
  git(dir, "checkout", "-b", "feature")
  git(dir, "rm", "b.ts")
  git(dir, "commit", "-m", "delete b")
  const scope = await resolveScope({ cwd: dir })
  assert.ok(scope.files.includes("b.ts"))
  rmSync(dir, { recursive: true, force: true })
})

test("renamed files keep both sides", async () => {
  const dir = makeRepo()
  git(dir, "checkout", "-b", "feature")
  git(dir, "mv", "b.ts", "c.ts")
  git(dir, "commit", "-m", "rename b")
  const scope = await resolveScope({ cwd: dir })
  assert.ok(scope.files.includes("b.ts"))
  assert.ok(scope.files.includes("c.ts"))
  rmSync(dir, { recursive: true, force: true })
})

test("CLAUDE.md discovery is scoped to ancestors of changed files", () => {
  const root = mkdtempSync(join(tmpdir(), "code-review-md-"))
  mkdirSync(join(root, "src"), { recursive: true })
  mkdirSync(join(root, "docs"), { recursive: true })
  writeFileSync(join(root, "CLAUDE.md"), "# root\nUse tabs.\n")
  writeFileSync(join(root, "src", "CLAUDE.md"), "# src\nNo default exports.\n")
  writeFileSync(join(root, "docs", "CLAUDE.md"), "# docs\nDocs only.\n")
  writeFileSync(join(root, "src", "a.ts"), "export default 1\n")

  const { paths, text } = discoverConventions(root, ["src/a.ts"])
  assert.ok(paths.includes(join(root, "CLAUDE.md")))
  assert.ok(paths.includes(join(root, "src", "CLAUDE.md")))
  assert.ok(!paths.includes(join(root, "docs", "CLAUDE.md")))
  assert.match(text, /Use tabs/)
  assert.match(text, /No default exports/)
  assert.doesNotMatch(text, /Docs only/)
  rmSync(root, { recursive: true, force: true })
})

test("a fresh repository reviews staged and unstaged changes", async () => {
  const dir = mkdtempSync(join(tmpdir(), "code-review-fresh-"))
  git(dir, "init", "-b", "main")
  git(dir, "config", "user.email", "test@example.com")
  git(dir, "config", "user.name", "Test")
  writeFileSync(join(dir, "staged.ts"), "export const staged = 1\n")
  writeFileSync(join(dir, "worktree.ts"), "export const worktree = 1\n")
  git(dir, "add", "staged.ts", "worktree.ts")
  writeFileSync(join(dir, "worktree.ts"), "export const worktree = 2\n")
  const scope = await resolveScope({ cwd: dir })
  assert.deepEqual(scope.files, ["staged.ts", "worktree.ts"])
  assert.match(scope.diffText ?? "", /staged = 1/)
  assert.match(scope.diffText ?? "", /worktree = 2/)
  assert.match(scope.diffCommand, /--staged/)
  rmSync(dir, { recursive: true, force: true })
})

test("a path target resolves to the nearest git root", async () => {
  const parent = mkdtempSync(join(tmpdir(), "code-review-parent-"))
  git(parent, "init", "-b", "main")
  git(parent, "config", "user.email", "test@example.com")
  git(parent, "config", "user.name", "Test")
  writeFileSync(join(parent, "parent.ts"), "export const parent = 1\n")
  git(parent, "add", ".")
  git(parent, "commit", "-m", "base")
  const sub = join(parent, "sub")
  mkdirSync(sub)
  git(sub, "init", "-b", "main")
  git(sub, "config", "user.email", "test@example.com")
  git(sub, "config", "user.name", "Test")
  writeFileSync(join(sub, "sub.ts"), "export const sub = 1\n")
  git(sub, "add", ".")
  git(sub, "commit", "-m", "base")
  writeFileSync(join(sub, "sub.ts"), "export const sub = 2\n")
  const scope = await resolveScope({ cwd: parent, target: "sub" })
  assert.equal(realpathSync(scope.root), realpathSync(sub))
  assert.deepEqual(scope.files, ["sub.ts"])
  assert.match(scope.diffText ?? "", /sub = 2/)
  rmSync(parent, { recursive: true, force: true })
})

test("@-prefixed path targets try the literal path, then the stripped path", () => {
  const dir = mkdtempSync(join(tmpdir(), "code-review-at-"))
  mkdirSync(join(dir, ".git"))
  mkdirSync(join(dir, "src"))
  mkdirSync(join(dir, "@pkg"))
  assert.equal(resolveDiffScope(dir, "@src")?.relPath, "src")
  assert.equal(resolveDiffScope(dir, "@pkg")?.relPath, "@pkg")
  rmSync(dir, { recursive: true, force: true })
})

test("git-quoted paths are unquoted in patches and name-status output", () => {
  assert.equal(unquoteGitPath('"a/foo\\tbar.ts"'), "a/foo\tbar.ts")
  assert.equal(unquoteGitPath('"b/src/caf\\303\\251.ts"'), "b/src/café.ts")
  assert.equal(unquoteGitPath('"bell\\a.ts"'), "bell\x07.ts")
  const patch = [
    'diff --git "a/src/foo\\tbar.ts" "b/src/foo\\tbar.ts"',
    '--- "a/src/foo\\tbar.ts"',
    '+++ "b/src/foo\\tbar.ts"',
  ].join("\n")
  assert.deepEqual([...scanPatchChurn(patch).paths], ["src/foo\tbar.ts"])
  const quotedChurn = buildContextPackage(
    `${patch}\n@@ -1 +1 @@\n-a\n+b`,
    "/repo",
    "x",
  )
  assert.match(quotedChurn, /src\/foo\tbar\.ts \+1 -1/)
})

test("the context package reports churn, binary files, and the 200-file cap", () => {
  const patch = [
    "diff --git a/src/a.ts b/src/a.ts",
    "--- a/src/a.ts",
    "+++ b/src/a.ts",
    "@@ -1,2 +1,2 @@",
    "-old",
    "+new",
    "+extra",
    "diff --git a/img.png b/img.png",
    "Binary files a/img.png and b/img.png differ",
  ].join("\n")
  const pkg = buildContextPackage(patch, "/repo", "range main...HEAD")
  assert.match(pkg, /Repo root: \/repo/)
  assert.match(pkg, /Diff scope: range main\.\.\.HEAD/)
  assert.match(pkg, /src\/a\.ts \+2 -1/)
  assert.match(pkg, /img\.png \(binary\)/)
  const many = Array.from({ length: 201 }, (_, i) => `diff --git a/f${i}.ts b/f${i}.ts`).join("\n")
  assert.match(buildContextPackage(many, "/repo", "x"), /… and 1 more/)
})

test("a hung git call fails with a clear timeout error", async () => {
  const dir = mkdtempSync(join(tmpdir(), "code-review-timeout-"))
  const exec: Exec = async () => ({ stdout: "", stderr: "", code: 1, timedOut: true })
  await assert.rejects(() => resolveScope({ cwd: dir, exec }), /timed out/)
  rmSync(dir, { recursive: true, force: true })
})

test("an aborted scope discovery fails with a cancellation error", async () => {
  const dir = mkdtempSync(join(tmpdir(), "code-review-abort-"))
  const exec: Exec = async () => ({ stdout: "", stderr: "", code: 1, aborted: true })
  await assert.rejects(() => resolveScope({ cwd: dir, exec }), /cancelled/)
  rmSync(dir, { recursive: true, force: true })
})

test("a PR review downloads the patch once and verifies the head", async () => {
  const dir = mkdtempSync(join(tmpdir(), "code-review-pr-"))
  mkdirSync(join(dir, ".git"))
  const calls: string[][] = []
  const patch = [
    "diff --git a/src/a.ts b/src/a.ts",
    "--- a/src/a.ts",
    "+++ b/src/a.ts",
    "@@ -1 +1 @@",
    "-a",
    "+b",
  ].join("\n")
  const exec: Exec = async (argv) => {
    calls.push(argv)
    if (argv[0] === "git" && argv.includes("rev-parse") && argv.includes("--show-toplevel")) {
      return { code: 0, stdout: `${dir}\n`, stderr: "" }
    }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "diff") return { code: 0, stdout: patch, stderr: "" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view") {
      return {
        code: 0,
        stdout: JSON.stringify({
          files: [{ path: "src/a.ts" }],
          additions: 4,
          deletions: 3,
          headRefOid: "abc123",
          url: "https://github.com/o/r/pull/42",
        }),
        stderr: "",
      }
    }
    return { code: 0, stdout: "", stderr: "" }
  }
  const scope = await resolveScope({ cwd: dir, target: "42", exec })
  assert.deepEqual(scope.files, ["src/a.ts"])
  assert.equal(scope.diffLines, 7)
  assert.equal(scope.diffText, patch)
  assert.equal(scope.prHeadOid, "abc123")
  assert.equal(scope.prUrl, "https://github.com/o/r/pull/42")
  assert.equal(calls.filter((c) => c[0] === "gh" && c[1] === "pr" && c[2] === "diff").length, 1)
  // Head-only reads bracket the patch; the metadata read supplies the file
  // list and line count. The patch and metadata downloads still overlap.
  assert.equal(calls.filter((c) => c[0] === "gh" && c[1] === "pr" && c[2] === "view").length, 3)
  rmSync(dir, { recursive: true, force: true })
})

test("a local PR review skips the post-capture head check", async () => {
  const dir = mkdtempSync(join(tmpdir(), "code-review-pr-nohead-"))
  mkdirSync(join(dir, ".git"))
  const calls: string[][] = []
  const patch = "diff --git a/src/a.ts b/src/a.ts\n--- a/src/a.ts\n+++ b/src/a.ts\n@@ -1 +1 @@\n-a\n+b\n"
  const exec: Exec = async (argv) => {
    calls.push(argv)
    if (argv[0] === "git" && argv.includes("rev-parse") && argv.includes("--show-toplevel")) {
      return { code: 0, stdout: `${dir}\n`, stderr: "" }
    }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "diff") return { code: 0, stdout: patch, stderr: "" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view") {
      return {
        code: 0,
        stdout: JSON.stringify({
          files: [{ path: "src/a.ts" }],
          headRefOid: "abc123",
          url: "https://github.com/o/r/pull/42",
        }),
        stderr: "",
      }
    }
    return { code: 0, stdout: "", stderr: "" }
  }
  const scope = await resolveScope({ cwd: dir, target: "42", exec, verifyPrHead: false })
  assert.equal(scope.prHeadOid, "abc123")
  assert.equal(calls.filter((c) => c[0] === "gh" && c[1] === "pr" && c[2] === "view").length, 1)
  rmSync(dir, { recursive: true, force: true })
})

test("an unavailable head check leaves the PR head unverified", async () => {
  const dir = mkdtempSync(join(tmpdir(), "code-review-pr-headfail-"))
  mkdirSync(join(dir, ".git"))
  const patch = "diff --git a/src/a.ts b/src/a.ts\n--- a/src/a.ts\n+++ b/src/a.ts\n@@ -1 +1 @@\n-a\n+b\n"
  const exec: Exec = async (argv) => {
    if (argv[0] === "git" && argv.includes("rev-parse") && argv.includes("--show-toplevel")) {
      return { code: 0, stdout: `${dir}\n`, stderr: "" }
    }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "diff") return { code: 0, stdout: patch, stderr: "" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view") {
      if (
        argv.some((a) => a.includes("headRefOid")) &&
        !argv.includes("files,additions,deletions,headRefOid,url")
      ) {
        return { code: 1, stdout: "", stderr: "rate limited" }
      }
      return {
        code: 0,
        stdout: JSON.stringify({
          files: [{ path: "src/a.ts" }],
          headRefOid: "abc123",
          url: "https://github.com/o/r/pull/42",
        }),
        stderr: "",
      }
    }
    return { code: 0, stdout: "", stderr: "" }
  }
  const scope = await resolveScope({ cwd: dir, target: "42", exec })
  // An unavailable check is not proof that the patch matches. The patch is
  // still captured, but posting must not pin an unverified head.
  assert.equal(scope.prHeadOid, undefined)
  assert.deepEqual(scope.files, ["src/a.ts"])
  assert.equal(scope.diffText, patch)
  rmSync(dir, { recursive: true, force: true })
})

test("a failed PR metadata call still uses the cached patch", async () => {
  const dir = mkdtempSync(join(tmpdir(), "code-review-pr-fallback-"))
  mkdirSync(join(dir, ".git"))
  const calls: string[][] = []
  const patch = "diff --git a/src/a.ts b/src/a.ts\n--- a/src/a.ts\n+++ b/src/a.ts\n@@ -1 +1 @@\n-a\n+b\n"
  const exec: Exec = async (argv) => {
    calls.push(argv)
    if (argv[0] === "git" && argv.includes("rev-parse") && argv.includes("--show-toplevel")) {
      return { code: 0, stdout: `${dir}\n`, stderr: "" }
    }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "diff") return { code: 0, stdout: patch, stderr: "" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view") return { code: 1, stdout: "", stderr: "api error" }
    return { code: 0, stdout: "", stderr: "" }
  }
  const scope = await resolveScope({ cwd: dir, target: "42", exec })
  assert.deepEqual(scope.files, ["src/a.ts"])
  assert.equal(scope.diffLines, 2)
  assert.equal(scope.diffText, patch)
  // A missing head only affects --comment posting; the patch and file list
  // were fully recovered, so the review must not be marked partial.
  assert.equal(scope.prHeadOid, undefined)
  assert.equal(scope.warnings?.some((w) => w.includes("could not capture")) ?? false, false)
  assert.equal(calls.filter((c) => c[0] === "gh" && c[1] === "pr" && c[2] === "diff").length, 1)
  rmSync(dir, { recursive: true, force: true })
})

test("a verified head is pinned when only the metadata read fails", async () => {
  const dir = mkdtempSync(join(tmpdir(), "code-review-pr-headonly-"))
  mkdirSync(join(dir, ".git"))
  const patch = "diff --git a/src/a.ts b/src/a.ts\n--- a/src/a.ts\n+++ b/src/a.ts\n@@ -1 +1 @@\n-a\n+b\n"
  const exec: Exec = async (argv) => {
    if (argv[0] === "git" && argv.includes("rev-parse") && argv.includes("--show-toplevel")) {
      return { code: 0, stdout: `${dir}\n`, stderr: "" }
    }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "diff") return { code: 0, stdout: patch, stderr: "" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view") {
      if (argv.includes("files,additions,deletions,headRefOid,url")) {
        return { code: 1, stdout: "", stderr: "api error" }
      }
      return {
        code: 0,
        stdout: JSON.stringify({
          headRefOid: "abc123",
          url: "https://github.com/o/r/pull/42",
        }),
        stderr: "",
      }
    }
    return { code: 0, stdout: "", stderr: "" }
  }
  const scope = await resolveScope({ cwd: dir, target: "42", exec })
  // The head-only reads bracket the patch and agree; the metadata payload is
  // not required to pin the verified head or recover the PR URL.
  assert.equal(scope.prHeadOid, "abc123")
  assert.equal(scope.prUrl, "https://github.com/o/r/pull/42")
  assert.deepEqual(scope.files, ["src/a.ts"])
  assert.equal(scope.diffText, patch)
  rmSync(dir, { recursive: true, force: true })
})

test("a moved head keeps the captured patch and leaves the head unverified", async () => {
  const dir = mkdtempSync(join(tmpdir(), "code-review-pr-moved-"))
  mkdirSync(join(dir, ".git"))
  const calls: string[][] = []
  const patch = "diff --git a/src/a.ts b/src/a.ts\n--- a/src/a.ts\n+++ b/src/a.ts\n@@ -1 +1 @@\n-a\n+b\n"
  let headCalls = 0
  const exec: Exec = async (argv) => {
    calls.push(argv)
    if (argv[0] === "git" && argv.includes("rev-parse") && argv.includes("--show-toplevel")) {
      return { code: 0, stdout: `${dir}\n`, stderr: "" }
    }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "diff") return { code: 0, stdout: patch, stderr: "" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view") {
      if (argv.includes("files,additions,deletions,headRefOid,url")) {
        return {
          code: 0,
          stdout: JSON.stringify({
            files: [{ path: "src/a.ts" }],
            headRefOid: "old",
            url: "https://github.com/o/r/pull/42",
          }),
          stderr: "",
        }
      }
      headCalls++
      return {
        code: 0,
        stdout: JSON.stringify({
          headRefOid: headCalls === 1 ? "old" : "new",
          url: "https://github.com/o/r/pull/42",
        }),
        stderr: "",
      }
    }
    return { code: 0, stdout: "", stderr: "" }
  }
  const scope = await resolveScope({ cwd: dir, target: "42", exec })
  // The mismatch keeps the already-captured patch; the head is unverified and
  // posting falls back to a general comment.
  assert.equal(scope.prHeadOid, undefined)
  assert.equal(scope.prUrl, "https://github.com/o/r/pull/42")
  assert.equal(calls.filter((c) => c[0] === "gh" && c[1] === "pr" && c[2] === "diff").length, 1)
  rmSync(dir, { recursive: true, force: true })
})

test("a persistent head probe failure is not retried", async () => {
  const dir = mkdtempSync(join(tmpdir(), "code-review-pr-persistent-"))
  mkdirSync(join(dir, ".git"))
  const calls: string[][] = []
  const patch = "diff --git a/src/a.ts b/src/a.ts\n--- a/src/a.ts\n+++ b/src/a.ts\n@@ -1 +1 @@\n-a\n+b\n"
  const exec: Exec = async (argv) => {
    calls.push(argv)
    if (argv[0] === "git" && argv.includes("rev-parse") && argv.includes("--show-toplevel")) {
      return { code: 0, stdout: `${dir}\n`, stderr: "" }
    }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "diff") return { code: 0, stdout: patch, stderr: "" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view") {
      if (argv.includes("files,additions,deletions,headRefOid,url")) {
        return {
          code: 0,
          stdout: JSON.stringify({
            files: [{ path: "src/a.ts" }],
            headRefOid: "abc123",
            url: "https://github.com/o/r/pull/42",
          }),
          stderr: "",
        }
      }
      return { code: 1, stdout: "", stderr: "authentication failed" }
    }
    return { code: 0, stdout: "", stderr: "" }
  }
  const scope = await resolveScope({ cwd: dir, target: "42", exec })
  assert.equal(scope.prHeadOid, undefined)
  const headOnlyReads = calls.filter(
    (c) =>
      c[0] === "gh" &&
      c[1] === "pr" &&
      c[2] === "view" &&
      c.some((a) => a.includes("headRefOid")) &&
      !c.includes("files,additions,deletions,headRefOid,url"),
  )
  // One pre-patch and one post-patch attempt; an auth failure is not retried.
  assert.equal(headOnlyReads.length, 2)
  rmSync(dir, { recursive: true, force: true })
})

test("a failed patch fetch does not run the trailing head read", async () => {
  const dir = mkdtempSync(join(tmpdir(), "code-review-pr-badpatch-"))
  mkdirSync(join(dir, ".git"))
  const calls: string[][] = []
  const exec: Exec = async (argv) => {
    calls.push(argv)
    if (argv[0] === "git" && argv.includes("rev-parse") && argv.includes("--show-toplevel")) {
      return { code: 0, stdout: `${dir}\n`, stderr: "" }
    }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "diff") {
      return { code: 1, stdout: "", stderr: "not found" }
    }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view") {
      return { code: 0, stdout: JSON.stringify({ headRefOid: "abc123" }), stderr: "" }
    }
    return { code: 0, stdout: "", stderr: "" }
  }
  await assert.rejects(() => resolveScope({ cwd: dir, target: "42", exec }), /Could not fetch PR/)
  const headOnlyReads = calls.filter(
    (c) =>
      c[0] === "gh" &&
      c[1] === "pr" &&
      c[2] === "view" &&
      c.some((a) => a.includes("headRefOid")) &&
      !c.includes("files,additions,deletions,headRefOid,url"),
  )
  // The pre-patch bracket read runs; the trailing read (and its retry) is
  // skipped because the patch already failed.
  assert.equal(headOnlyReads.length, 1)
  rmSync(dir, { recursive: true, force: true })
})

test("a failed file listing awaits the already-started diff captures", async () => {
  const dir = makeRepo()
  writeFileSync(join(dir, "a.ts"), "export const a = 2\n")
  const calls: string[][] = []
  let captureSettled = false
  const exec: Exec = async (argv, cwd, opts) => {
    calls.push(argv)
    if (argv.includes("--name-status")) {
      return { code: 128, stdout: "", stderr: "bad revision" }
    }
    if (
      argv.includes("diff") &&
      !argv.includes("--quiet") &&
      !argv.includes("--numstat")
    ) {
      await new Promise((resolve) => setTimeout(resolve, 5))
      captureSettled = true
      return { code: 0, stdout: "", stderr: "" }
    }
    return defaultExec(argv, cwd, opts)
  }
  await assert.rejects(() => resolveScope({ cwd: dir, exec }), /Could not list changed files/)
  const captures = calls.filter(
    (argv) =>
      argv.includes("diff") &&
      !argv.includes("--name-status") &&
      !argv.includes("--quiet") &&
      !argv.includes("--numstat"),
  )
  // The captures overlap the listings, but the all-listings-failed path must
  // await them before throwing so no child is left running.
  assert.ok(captures.length > 0)
  assert.equal(captureSettled, true)
  rmSync(dir, { recursive: true, force: true })
})

test("user-level conventions come last and each source gets a fair budget", () => {
  const root = mkdtempSync(join(tmpdir(), "code-review-conv-"))
  const home = mkdtempSync(join(tmpdir(), "code-review-home-"))
  mkdirSync(join(root, "src"), { recursive: true })
  mkdirSync(join(home, ".claude"), { recursive: true })
  writeFileSync(join(root, "CLAUDE.md"), `# root\n${"x".repeat(5000)}\n`)
  writeFileSync(join(root, "src", "CLAUDE.md"), "# src\nNo default exports.\n")
  writeFileSync(join(home, ".claude", "CLAUDE.md"), "# user\nUser rule.\n")
  const { paths, text } = discoverConventions(root, ["src/a.ts"], 3000, home)
  assert.deepEqual(paths, [
    join(root, "CLAUDE.md"),
    join(root, "src", "CLAUDE.md"),
    join(home, ".claude", "CLAUDE.md"),
  ])
  assert.match(text, /No default exports/)
  assert.match(text, /User rule/)
  rmSync(root, { recursive: true, force: true })
  rmSync(home, { recursive: true, force: true })
})

test("a fully read conventions file over the character budget carries the truncation marker", () => {
  const root = mkdtempSync(join(tmpdir(), "code-review-conv-cut-"))
  writeFileSync(join(root, "CLAUDE.md"), "x".repeat(50_000))
  const { text } = discoverConventions(root, ["a.ts"], 20_000)
  assert.ok(text.length <= 20_000)
  assert.match(text, /…\(truncated\)$/)
  rmSync(root, { recursive: true, force: true })
})

test("a conventions budget smaller than the marker still marks truncation", () => {
  const root = mkdtempSync(join(tmpdir(), "code-review-conv-tiny-"))
  writeFileSync(join(root, "CLAUDE.md"), "x".repeat(500))
  const { text } = discoverConventions(root, ["a.ts"], 5)
  // The short marker fits the tiny budget; a silent fragment would look like
  // the complete file.
  assert.match(text, /…/)
  rmSync(root, { recursive: true, force: true })
})

test("readCapped keeps a tiny budget while still signalling truncation", () => {
  const dir = mkdtempSync(join(tmpdir(), "code-review-readcapped-"))
  const path = join(dir, "CLAUDE.md")
  writeFileSync(path, "x".repeat(500))
  for (const budget of [1, 2, 5, 12]) {
    const text = readCapped(path, budget)
    assert.ok(text.length <= budget, `budget ${budget} returned ${text.length} characters`)
    assert.match(text, /…/, `budget ${budget} did not signal truncation`)
  }
  rmSync(dir, { recursive: true, force: true })
})

test("a partial capture adds failed numstat to the successful patch total", async () => {
  const dir = makeRepo()
  git(dir, "checkout", "-b", "feature")
  writeFileSync(join(dir, "big.ts"), Array.from({ length: 100 }, (_, i) => `export const v${i} = ${i}\n`).join(""))
  git(dir, "add", "big.ts")
  git(dir, "commit", "-m", "add big file")
  writeFileSync(join(dir, "a.ts"), "export const a = 99\nexport const b = 100\n")
  const exec: Exec = async (argv, cwd, opts) => {
    if (
      argv.includes("diff") &&
      argv.includes("HEAD") &&
      !argv.includes("main...HEAD") &&
      !argv.includes("--quiet") &&
      !argv.includes("--name-status") &&
      !argv.includes("--numstat")
    ) {
      return { code: 1, stdout: "", stderr: "partial capture failed" }
    }
    if (argv.includes("--numstat") && argv.includes("HEAD")) {
      return { code: 0, stdout: "2\t0\ta.ts\n", stderr: "" }
    }
    return defaultExec(argv, cwd, opts)
  }
  const scope = await resolveScope({ cwd: dir, exec })
  // 100 lines from the successful range patch + 2 from the failed HEAD entry.
  assert.equal(scope.diffLines, 102)
  rmSync(dir, { recursive: true, force: true })
})

test("a path target outside any repository is an error", async () => {
  const repo = makeRepo()
  const outside = mkdtempSync(join(tmpdir(), "code-review-outside-"))
  writeFileSync(join(outside, "x.ts"), "export const x = 1\n")
  await assert.rejects(() => resolveScope({ cwd: repo, target: outside }), /not inside a git repository/)
  rmSync(repo, { recursive: true, force: true })
  rmSync(outside, { recursive: true, force: true })
})

test("a single-commit repository with no upstream or main falls back to HEAD", async () => {
  const dir = makeRepo("trunk")
  const scope = await resolveScope({ cwd: dir })
  // HEAD~1 does not exist and there is no upstream/main; HEAD is the only
  // valid base. The clean checkout must report no changes, not a failed review.
  assert.deepEqual(scope.files, [])
  assert.equal(scope.warnings, undefined)
  assert.match(scope.diffCommand, /git .*diff .*--end-of-options HEAD/)
  rmSync(dir, { recursive: true, force: true })
})

test("a bare branch target wins over a same-named path", async () => {
  const dir = makeRepo()
  git(dir, "checkout", "-b", "src")
  git(dir, "checkout", "main")
  git(dir, "checkout", "-b", "feature")
  writeFileSync(join(dir, "feature.ts"), "export const feature = 1\n")
  mkdirSync(join(dir, "src"))
  writeFileSync(join(dir, "src", "path.ts"), "export const path = 1\n")
  git(dir, "add", ".")
  git(dir, "commit", "-m", "feature change")
  const scope = await resolveScope({ cwd: dir, target: "src" })
  assert.equal(scope.branch, "src")
  assert.equal(scope.scopeKind, "branch")
  assert.match(scope.diffCommand, /src\.\.\.HEAD/)
  assert.ok(scope.files.includes("feature.ts"))
  rmSync(dir, { recursive: true, force: true })
})

test("a remote-only branch target resolves its remote-tracking ref", async () => {
  const dir = makeRepo()
  git(dir, "remote", "add", "origin", "https://example.com/repo.git")
  git(dir, "update-ref", "refs/remotes/origin/release/2.0", "HEAD")
  git(dir, "checkout", "-b", "feature")
  writeFileSync(join(dir, "feature.ts"), "export const feature = 1\n")
  git(dir, "add", ".")
  git(dir, "commit", "-m", "feature change")
  const scope = await resolveScope({ cwd: dir, target: "release/2.0" })
  assert.equal(scope.branch, "release/2.0")
  assert.equal(scope.scopeKind, "branch")
  assert.equal(scope.diffBase, "origin/release/2.0")
  assert.match(scope.diffCommand, /origin\/release\/2\.0\.\.\.HEAD/)
  rmSync(dir, { recursive: true, force: true })
})

test("an @-named branch is resolved instead of being treated as a path", async () => {
  const dir = makeRepo()
  git(dir, "branch", "@release")
  git(dir, "checkout", "-b", "feature")
  writeFileSync(join(dir, "feature.ts"), "export const feature = 1\n")
  git(dir, "add", ".")
  git(dir, "commit", "-m", "feature change")
  const scope = await resolveScope({ cwd: dir, target: "@release" })
  assert.equal(scope.branch, "@release")
  assert.equal(scope.scopeKind, "branch")
  assert.match(scope.diffCommand, /@release\.\.\.HEAD/)
  assert.ok(scope.files.includes("feature.ts"))
  rmSync(dir, { recursive: true, force: true })
})

test("a free-form target narrows to a path named inside it", async () => {
  const dir = makeRepo()
  mkdirSync(join(dir, "src"), { recursive: true })
  writeFileSync(join(dir, "src", "a.ts"), "export const a = 1\n")
  git(dir, "add", ".")
  git(dir, "commit", "-m", "add src")
  writeFileSync(join(dir, "src", "a.ts"), "export const a = 2\n")
  writeFileSync(join(dir, "b.ts"), "export const b = 3\n")
  const scope = await resolveScope({ cwd: dir, target: "focus on src/a.ts for bugs" })
  assert.deepEqual(scope.files, ["src/a.ts"])
  assert.match(scope.diffCommand, /-- src\/a\.ts/)
  assert.match(scope.diffText ?? "", /a = 2/)
  assert.doesNotMatch(scope.diffText ?? "", /b = 3/)
  rmSync(dir, { recursive: true, force: true })
})

test("includeDiffLines false skips the numstat pass", async () => {
  const dir = makeRepo()
  writeFileSync(join(dir, "a.ts"), "export const a = 9\n")
  const calls: string[][] = []
  const exec: Exec = async (argv, cwd, opts) => {
    calls.push(argv)
    return defaultExec(argv, cwd, opts)
  }
  const scope = await resolveScope({ cwd: dir, exec, includeDiffLines: false })
  assert.equal(scope.diffLines, 0)
  assert.equal(calls.some((argv) => argv.includes("--numstat")), false)
  rmSync(dir, { recursive: true, force: true })
})

test("includeConventions false lists paths but skips the CLAUDE.md text", async () => {
  const dir = makeRepo()
  writeFileSync(join(dir, "CLAUDE.md"), "# root\nRULE_NOT_READ\n")
  writeFileSync(join(dir, "c.ts"), "export const c = 3\n")
  git(dir, "add", "c.ts")
  const scope = await resolveScope({ cwd: dir, includeConventions: false })
  assert.ok(scope.claudeMdFiles.some((path) => path.endsWith("CLAUDE.md")))
  assert.equal(scope.conventions, "(none noted)")
  rmSync(dir, { recursive: true, force: true })
})

test("a failed capture only re-walks the failed plan entry for numstat", async () => {
  const dir = makeRepo()
  // A tracked change adds the worktree entry to the plan; the range capture
  // fails, so only the range entry should be re-walked for numstat.
  writeFileSync(join(dir, "a.ts"), "export const a = 99\n")
  const calls: string[][] = []
  const exec: Exec = async (argv, cwd, opts) => {
    calls.push(argv)
    if (
      argv.includes("main...HEAD") &&
      argv.includes("diff") &&
      !argv.includes("--numstat") &&
      !argv.includes("--name-status") &&
      !argv.includes("--quiet")
    ) {
      return { code: 1, stdout: "", stderr: "boom" }
    }
    return defaultExec(argv, cwd, opts)
  }
  await resolveScope({ cwd: dir, target: "main...HEAD", exec })
  const numstat = calls.filter((argv) => argv.includes("--numstat"))
  assert.equal(numstat.length, 1)
  assert.ok(numstat[0].includes("main...HEAD"))
  rmSync(dir, { recursive: true, force: true })
})

test("a range target with a dotted ref is resolved as a range", async () => {
  const dir = makeRepo()
  git(dir, "tag", "v1.2.3")
  writeFileSync(join(dir, "a.ts"), "export const a = 10\n")
  git(dir, "add", ".")
  git(dir, "commit", "-m", "after tag")
  const scope = await resolveScope({ cwd: dir, target: "v1.2.3...HEAD" })
  assert.equal(scope.scopeKind, "range")
  assert.deepEqual(scope.files, ["a.ts"])
  assert.match(scope.diffCommand, /v1\.2\.3\.\.\.HEAD/)
  rmSync(dir, { recursive: true, force: true })
})

test("a changed filename with leading whitespace is preserved", async () => {
  const dir = makeRepo()
  writeFileSync(join(dir, " leading.ts"), "export const leading = 1\n")
  git(dir, "add", ".")
  git(dir, "commit", "-m", "add leading-space file")
  writeFileSync(join(dir, " leading.ts"), "export const leading = 2\n")
  const scope = await resolveScope({ cwd: dir })
  assert.ok(scope.files.includes(" leading.ts"), `got ${JSON.stringify(scope.files)}`)
  rmSync(dir, { recursive: true, force: true })
})

test("a failed diff capture is reported instead of a clean empty review", async () => {
  const dir = makeRepo()
  writeFileSync(join(dir, "a.ts"), "export const a = 11\n")
  const exec: Exec = async (argv, cwd, opts) => {
    const result = await defaultExec(argv, cwd, opts)
    if (argv.includes("rev-parse") && argv.includes("--show-toplevel")) return result
    if (argv[0] === "git" && argv.includes("diff") && !argv.includes("--name-status") && !argv.includes("--numstat") && !argv.includes("--quiet")) {
      return { code: 128, stdout: "", stderr: "fatal: unable to read tree" }
    }
    return result
  }
  // Every diff capture failed; the review must not claim there was nothing to review.
  await assert.rejects(() => resolveScope({ cwd: dir, exec }), /Could not read the diff/)
  rmSync(dir, { recursive: true, force: true })
})

test("diffLines sums an empty primary range and a dirty worktree", async () => {
  const dir = makeRepo()
  writeFileSync(join(dir, "a.ts"), "export const a = 12\n")
  const scope = await resolveScope({ cwd: dir })
  assert.ok(scope.diffLines > 0, `expected worktree churn, got ${scope.diffLines}`)
  rmSync(dir, { recursive: true, force: true })
})

test("a dirty HEAD~1 fallback does not capture the working tree twice", async () => {
  const dir = makeRepo("master")
  writeFileSync(join(dir, "a.ts"), "export const a = 2\n")
  git(dir, "add", ".")
  git(dir, "commit", "-m", "second commit")
  writeFileSync(join(dir, "a.ts"), "export const a = 3\n")
  const scope = await resolveScope({ cwd: dir })
  assert.doesNotMatch(scope.diffCommand, /; git diff HEAD /)
  assert.deepEqual(scope.diffCommands?.length, 1)
  // HEAD~1 compares the commit to the worktree, so the single hunk is -1 +3.
  assert.equal(scope.diffLines, 2)
  assert.equal((scope.diffText?.match(/\+export const a = 3/g) ?? []).length, 1)
  rmSync(dir, { recursive: true, force: true })
})

test("a changed path with braces is shell-quoted in the diff command", async () => {
  const dir = makeRepo()
  writeFileSync(join(dir, "{a,b}.ts"), "export const brace = 1\n")
  git(dir, "add", "{a,b}.ts")
  const scope = await resolveScope({ cwd: dir, target: "{a,b}.ts" })
  assert.deepEqual(scope.files, ["{a,b}.ts"])
  assert.match(scope.diffCommand, /'\{a,b\}\.ts'/)
  rmSync(dir, { recursive: true, force: true })
})

test("a PR name-only fallback preserves leading whitespace in a filename", async () => {
  const dir = mkdtempSync(join(tmpdir(), "code-review-pr-name-"))
  mkdirSync(join(dir, ".git"))
  const exec: Exec = async (argv) => {
    if (argv[0] === "git" && argv.includes("--show-toplevel")) return { code: 0, stdout: `${dir}\n`, stderr: "" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "diff") {
      if (argv.includes("--name-only")) return { code: 0, stdout: " logo.png\n", stderr: "" }
      return { code: 0, stdout: "Binary files a/logo.png and b/logo.png differ\n", stderr: "" }
    }
    // The metadata call fails, so the patch scan has no file blocks either.
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view") return { code: 1, stdout: "", stderr: "api error" }
    return { code: 0, stdout: "", stderr: "" }
  }
  const scope = await resolveScope({ cwd: dir, target: "42", exec })
  assert.deepEqual(scope.files, [" logo.png"])
  rmSync(dir, { recursive: true, force: true })
})

test("PR patch churn counts content lines that start with ++ or --", async () => {
  const dir = mkdtempSync(join(tmpdir(), "code-review-patchcount-"))
  const patch = [
    "diff --git a/src/a.ts b/src/a.ts",
    "--- a/src/a.ts",
    "+++ b/src/a.ts",
    "@@ -1 +1,2 @@",
    "-old",
    "+++ counter",
  ].join("\n")
  const exec: Exec = async (argv) => {
    if (argv[0] === "git") return { code: 0, stdout: dir, stderr: "" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "diff") return { code: 0, stdout: patch, stderr: "" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view") return { code: 1, stdout: "", stderr: "api error" }
    return { code: 0, stdout: "", stderr: "" }
  }
  const scope = await resolveScope({ cwd: dir, target: "42", exec })
  assert.deepEqual(scope.files, ["src/a.ts"])
  // -old + added "++ counter" = 2 changed lines, not 1.
  assert.equal(scope.diffLines, 2)
  rmSync(dir, { recursive: true, force: true })
})

test("a symlinked path target resolves the repository that physically contains it", async () => {
  const dir = makeRepo()
  mkdirSync(join(dir, "src"))
  writeFileSync(join(dir, "src", "a.ts"), "export const a = 21\n")
  git(dir, "add", "src/a.ts")
  const link = join(mkdtempSync(join(tmpdir(), "code-review-link-")), "link")
  symlinkSync(join(dir, "src"), link)
  const scope = await resolveScope({ cwd: dir, target: link })
  assert.equal(realpathSync(scope.root), realpathSync(dir))
  assert.ok(scope.files.includes("src/a.ts"))
  rmSync(link, { force: true })
  rmSync(dir, { recursive: true, force: true })
})

test("an existing path whose name contains .. is reviewed as a path, not a range", async () => {
  const dir = makeRepo()
  const name = "foo..bar.ts"
  writeFileSync(join(dir, name), "export const dotted = 1\n")
  git(dir, "add", name)
  const scope = await resolveScope({ cwd: dir, target: name })
  assert.equal(scope.scopeKind, "path")
  assert.deepEqual(scope.files, [name])
  rmSync(dir, { recursive: true, force: true })
})

test("an unrelated added line does not move an old-path anchor to the head side", () => {
  const patch = [
    "diff --git a/src/old.ts b/src/new.ts",
    "similarity index 100%",
    "rename from src/old.ts",
    "rename to src/new.ts",
    "@@ -1,0 +10,1 @@",
    "+unrelated addition",
  ].join("\n")
  const sides = diffSideMap(patch, [{ file: "src/old.ts", line: 10 }])
  assert.equal(sides.hasLine("src/old.ts", 10), false)
})

test("diffSideForLine prefers the head side when a replacement reuses the number", () => {
  const patch = [
    "diff --git a/src/a.ts b/src/a.ts",
    "--- a/src/a.ts",
    "+++ b/src/a.ts",
    "@@ -10,2 +10,2 @@",
    "-old10",
    "+new10",
    "-old11",
    "+new11",
  ].join("\n")
  // Both numbers exist on both sides; a finding reports the head line, so the
  // added line wins over the removed line with the same number.
  assert.equal(diffSideForLine(patch, "src/a.ts", 10), "RIGHT")
  assert.equal(diffSideForLine(patch, "src/a.ts", 11), "RIGHT")
})

test("diffSideForLine anchors a line that exists only on the old side to LEFT", () => {
  const patch = [
    "diff --git a/src/a.ts b/src/a.ts",
    "--- a/src/a.ts",
    "+++ b/src/a.ts",
    "@@ -10,2 +10,1 @@",
    "-removed guard",
    "-older line",
    "+replacement",
  ].join("\n")
  assert.equal(diffSideForLine(patch, "src/a.ts", 11), "LEFT")
  assert.equal(diffSideForLine(patch, "src/a.ts", 10), "RIGHT")
})

test("diffSideForLine treats a renamed-from path as the old side", () => {
  const patch = [
    "diff --git a/src/old.ts b/src/new.ts",
    "similarity index 90%",
    "rename from src/old.ts",
    "rename to src/new.ts",
    "--- a/src/old.ts",
    "+++ b/src/new.ts",
    "@@ -10 +10 @@",
    "-guard",
    "+updated guard",
  ].join("\n")
  assert.equal(diffSideForLine(patch, "src/old.ts", 10), "LEFT")
  assert.equal(diffSideForLine(patch, "src/new.ts", 10), "RIGHT")
  const sides = diffSideMap(patch, [{ file: "src/old.ts", line: 10 }])
  assert.equal(sides.pathFor("src/old.ts", 10), "src/new.ts")
})

test("a small nested conventions file does not truncate a large root file", () => {
  const root = mkdtempSync(join(tmpdir(), "code-review-conv-nested-"))
  const home = mkdtempSync(join(tmpdir(), "code-review-conv-home3-"))
  mkdirSync(join(root, "src"), { recursive: true })
  const tail = "ROOT_RULE_AFTER_10K"
  writeFileSync(join(root, "CLAUDE.md"), `# root\n${"x".repeat(15_000)}\n${tail}\n`)
  writeFileSync(join(root, "src", "CLAUDE.md"), "# src\none line\n")
  const { text } = discoverConventions(root, ["src/a.ts"], 20_000, home)
  assert.match(text, new RegExp(tail))
  rmSync(root, { recursive: true, force: true })
  rmSync(home, { recursive: true, force: true })
})

test("leftover nested budget is not taken from a large root file", () => {
  const root = mkdtempSync(join(tmpdir(), "code-review-conv-nested2-"))
  const home = mkdtempSync(join(tmpdir(), "code-review-conv-home4-"))
  mkdirSync(join(root, "src", "nested"), { recursive: true })
  const tail = "ROOT_RULE_AT_THE_END"
  writeFileSync(join(root, "CLAUDE.md"), `# root\n${"x".repeat(19_000)}\n${tail}\n`)
  writeFileSync(join(root, "src", "CLAUDE.md"), "# src\none line\n")
  writeFileSync(join(root, "src", "nested", "CLAUDE.md"), "# nested\none line\n")
  const { text } = discoverConventions(root, ["src/nested/a.ts"], 20_000, home)
  assert.match(text, new RegExp(tail))
  rmSync(root, { recursive: true, force: true })
  rmSync(home, { recursive: true, force: true })
})

test("unused root convention budget is redistributed instead of pre-split equally", () => {
  const root = mkdtempSync(join(tmpdir(), "code-review-conv-redist-"))
  const home = mkdtempSync(join(tmpdir(), "code-review-conv-home5-"))
  mkdirSync(join(root, "src"), { recursive: true })
  const tail = "ROOT_RULE_AFTER_14K"
  writeFileSync(join(root, "CLAUDE.md"), `# root\n${"x".repeat(14_000)}\n${tail}\n`)
  writeFileSync(join(root, "AGENTS.md"), "# agents\nAGENTS_RULE\n")
  const { text } = discoverConventions(root, ["src/a.ts"], 20_000, home)
  assert.match(text, new RegExp(tail))
  assert.match(text, /AGENTS_RULE/)
  rmSync(root, { recursive: true, force: true })
  rmSync(home, { recursive: true, force: true })
})

test("a later nested conventions file still gets a slice when an earlier one is large", () => {
  const root = mkdtempSync(join(tmpdir(), "code-review-conv-later-"))
  const home = mkdtempSync(join(tmpdir(), "code-review-conv-home6-"))
  mkdirSync(join(root, "src"), { recursive: true })
  mkdirSync(join(root, "packages", "b"), { recursive: true })
  writeFileSync(join(root, "CLAUDE.md"), `# root\n${"x".repeat(30_000)}\n`)
  writeFileSync(join(root, "src", "CLAUDE.md"), `# src\n${"y".repeat(20_000)}\n`)
  writeFileSync(join(root, "packages", "b", "AGENTS.md"), "# package b\nLATER_PACKAGE_RULE\n")
  const { text } = discoverConventions(root, ["packages/b/a.ts"], 20_000, home)
  assert.match(text, /LATER_PACKAGE_RULE/)
  rmSync(root, { recursive: true, force: true })
  rmSync(home, { recursive: true, force: true })
})

test("a non-ASCII conventions file fills the character budget", () => {
  const root = mkdtempSync(join(tmpdir(), "code-review-conv-unicode-"))
  const home = mkdtempSync(join(tmpdir(), "code-review-conv-home-unicode-"))
  // 10,000 Chinese characters are ~30,000 UTF-8 bytes but only 10,000
  // characters. The old byte-sized read truncated at ~6,600 characters.
  writeFileSync(join(root, "CLAUDE.md"), `# root\n${"规".repeat(10_000)}\nUNICODE_TAIL\n`)
  const { text } = discoverConventions(root, ["src/a.ts"], 20_000, home)
  assert.match(text, /UNICODE_TAIL/)
  rmSync(root, { recursive: true, force: true })
  rmSync(home, { recursive: true, force: true })
})

test("the context package keeps fallback files that have no churn entry", () => {
  const patch = [
    "diff --git a/src/new.ts b/src/new.ts",
    "--- a/src/new.ts",
    "+++ b/src/new.ts",
    "@@ -1 +1 @@",
    "-a",
    "+b",
  ].join("\n")
  const churn = scanPatchChurnForTest(patch)
  const context = buildContextPackage(patch, "/repo", "range main...HEAD", ["src/old.ts"], churn)
  assert.match(context, /src\/new\.ts \+1 -1/)
  assert.match(context, /src\/old\.ts/)
})

test("a clean upstream range is not overridden by a non-empty HEAD~1", async () => {
  const dir = makeRepo()
  writeFileSync(join(dir, "a.ts"), "export const a = 2\n")
  git(dir, "add", ".")
  git(dir, "commit", "-m", "second commit")
  git(dir, "remote", "add", "origin", dir)
  git(dir, "update-ref", "refs/remotes/origin/main", "HEAD")
  git(dir, "branch", "--set-upstream-to=origin/main", "main")
  const scope = await resolveScope({ cwd: dir })
  assert.deepEqual(scope.files, [])
  assert.equal(scope.summary, "No changes found.")
  assert.doesNotMatch(scope.diffCommand, /HEAD~1/)
  rmSync(dir, { recursive: true, force: true })
})

test("a clean checkout does not read conventions for an empty review", async () => {
  const dir = makeRepo()
  writeFileSync(join(dir, "CLAUDE.md"), "# root\nRULE_NOT_READ\n")
  git(dir, "add", ".")
  git(dir, "commit", "-m", "add rules")
  const scope = await resolveScope({ cwd: dir })
  assert.deepEqual(scope.files, [])
  assert.deepEqual(scope.claudeMdFiles, [])
  assert.equal(scope.conventions, "(none noted)")
  rmSync(dir, { recursive: true, force: true })
})

test("a changed path containing ' b/' is parsed once", () => {
  const patch = [
    "diff --git a/src/ b/x.ts b/src/ b/x.ts",
    "--- a/src/ b/x.ts\t",
    "+++ b/src/ b/x.ts\t",
    "@@ -1 +1 @@",
    "-a",
    "+b",
  ].join("\n")
  assert.deepEqual([...scanPatchChurn(patch).paths], ["src/ b/x.ts"])
})

test("added content that looks like a +++ header is not a changed file", () => {
  const patch = [
    "diff --git a/a.sh b/a.sh",
    "--- a/a.sh",
    "+++ b/a.sh",
    "@@ -1 +1,2 @@",
    " a",
    "+++ b/foo",
  ].join("\n")
  assert.deepEqual([...scanPatchChurn(patch).paths], ["a.sh"])
})

test("a PR review without a finder budget still fetches the file metadata", async () => {
  const dir = mkdtempSync(join(tmpdir(), "code-review-pr-nometa-"))
  mkdirSync(join(dir, ".git"))
  const calls: string[][] = []
  // A binary-only PR: gh pr diff returns no parseable file blocks, so the
  // metadata call is the only file source.
  const patch = "Binary files a/logo.png and b/logo.png differ\n"
  const exec: Exec = async (argv) => {
    calls.push(argv)
    if (argv[0] === "git" && argv.includes("rev-parse") && argv.includes("--show-toplevel")) {
      return { code: 0, stdout: `${dir}\n`, stderr: "" }
    }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "diff") return { code: 0, stdout: patch, stderr: "" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view") {
      return {
        code: 0,
        stdout: JSON.stringify({ files: [{ path: "logo.png" }], additions: 0, deletions: 0 }),
        stderr: "",
      }
    }
    return { code: 0, stdout: "", stderr: "" }
  }
  const scope = await resolveScope({ cwd: dir, target: "42", exec, includeDiffLines: false })
  assert.deepEqual(scope.files, ["logo.png"])
  assert.equal(scope.diffLines, 0)
  assert.equal(calls.some((argv) => argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view"), true)
  rmSync(dir, { recursive: true, force: true })
})

test("a rename whose new path contains ' b/' keeps both real paths", () => {
  const patch = [
    "diff --git a/x b/y b/z",
    "similarity index 100%",
    "rename from x",
    "rename to y b/z",
  ].join("\n")
  assert.deepEqual([...scanPatchChurn(patch).paths], ["x", "y b/z"])
})

test("a timed-out HEAD probe is a discovery failure, not an unborn repository", async () => {
  const dir = mkdtempSync(join(tmpdir(), "code-review-head-timeout-"))
  mkdirSync(join(dir, ".git"))
  const exec: Exec = async (argv) => {
    if (argv[0] === "git" && argv.includes("--show-toplevel")) return { code: 0, stdout: `${dir}\n`, stderr: "" }
    if (argv[0] === "git" && argv.includes("--verify") && argv.includes("HEAD")) {
      return { code: 124, stdout: "", stderr: "", timedOut: true }
    }
    return { code: 0, stdout: "", stderr: "" }
  }
  await assert.rejects(() => resolveScope({ cwd: dir, exec }), /timed out/)
  rmSync(dir, { recursive: true, force: true })
})

test("an asymmetric rename whose new path contains ' b/' keeps both real paths", () => {
  const patch = [
    "diff --git a/x b/y b/zzzzzzzzzz",
    "similarity index 100%",
    "rename from x",
    "rename to y b/zzzzzzzzzz",
  ].join("\n")
  assert.deepEqual([...scanPatchChurn(patch).paths], ["x", "y b/zzzzzzzzzz"])
})

test("a numeric PR target is resolved in the session repository, not a same-named path", async () => {
  const parent = mkdtempSync(join(tmpdir(), "code-review-numeric-parent-"))
  mkdirSync(join(parent, ".git"))
  const nested = join(parent, "42")
  mkdirSync(join(nested, ".git"), { recursive: true })
  const calls: Array<{ argv: string[]; cwd: string }> = []
  const patch = "diff --git a/src/a.ts b/src/a.ts\n--- a/src/a.ts\n+++ b/src/a.ts\n@@ -1 +1 @@\n-a\n+b\n"
  const exec: Exec = async (argv, cwd) => {
    calls.push({ argv, cwd })
    if (argv[0] === "git" && argv.includes("--show-toplevel")) return { code: 0, stdout: `${parent}\n`, stderr: "" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "diff") return { code: 0, stdout: patch, stderr: "" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view") {
      return { code: 0, stdout: JSON.stringify({ files: [{ path: "src/a.ts" }], additions: 1, deletions: 1 }), stderr: "" }
    }
    return { code: 0, stdout: "", stderr: "" }
  }
  const scope = await resolveScope({ cwd: parent, target: "42", exec })
  assert.equal(scope.pr, 42)
  assert.equal(realpathSync(scope.root), realpathSync(parent))
  assert.deepEqual(scope.files, ["src/a.ts"])
  assert.equal(calls.every((c) => c.argv[0] !== "gh" || realpathSync(c.cwd) === realpathSync(parent)), true)
  rmSync(parent, { recursive: true, force: true })
})

test("an old-path anchor stays on the old side for a same-number replacement", () => {
  const patch = [
    "diff --git a/src/old.ts b/src/new.ts",
    "similarity index 90%",
    "rename from src/old.ts",
    "rename to src/new.ts",
    "--- a/src/old.ts",
    "+++ b/src/new.ts",
    "@@ -10,1 +10,1 @@",
    "-old guard",
    "+new guard",
  ].join("\n")
  const sides = diffSideMap(patch, [{ file: "src/old.ts", line: 10 }])
  assert.equal(sides.hasLine("src/old.ts", 10), true)
  assert.equal(sides.sideFor("src/old.ts", 10), "LEFT")
})
