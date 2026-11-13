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
  filesFromDiff,
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
    filesFromDiff(patch)
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
  assert.deepEqual(filesFromDiff(patch), ["src/a.ts", "old.ts", "new.ts"])
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
  assert.deepEqual(filesFromDiff(patch), ["src/foo\tbar.ts"])
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

test("a PR review downloads the patch and metadata once", async () => {
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
        stdout: JSON.stringify({ files: [{ path: "src/a.ts" }], additions: 4, deletions: 3 }),
        stderr: "",
      }
    }
    return { code: 0, stdout: "", stderr: "" }
  }
  const scope = await resolveScope({ cwd: dir, target: "42", exec })
  assert.deepEqual(scope.files, ["src/a.ts"])
  assert.equal(scope.diffLines, 7)
  assert.equal(scope.diffText, patch)
  assert.equal(calls.filter((c) => c[0] === "gh" && c[1] === "pr" && c[2] === "diff").length, 1)
  assert.equal(calls.filter((c) => c[0] === "gh" && c[1] === "pr" && c[2] === "view").length, 1)
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
  assert.equal(calls.filter((c) => c[0] === "gh" && c[1] === "pr" && c[2] === "diff").length, 1)
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

test("includeConventions false skips the CLAUDE.md reads", async () => {
  const dir = makeRepo()
  writeFileSync(join(dir, "CLAUDE.md"), "# root\nRULE_NOT_READ\n")
  writeFileSync(join(dir, "c.ts"), "export const c = 3\n")
  const scope = await resolveScope({ cwd: dir, includeConventions: false })
  assert.deepEqual(scope.claudeMdFiles, [])
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
  assert.deepEqual(filesFromDiff(patch), ["src/ b/x.ts"])
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
  assert.deepEqual(filesFromDiff(patch), ["a.sh"])
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
  assert.deepEqual(filesFromDiff(patch), ["x", "y b/z"])
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
  assert.deepEqual(filesFromDiff(patch), ["x", "y b/zzzzzzzzzz"])
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
