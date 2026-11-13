import { test } from "node:test"
import assert from "node:assert/strict"
import {
  buildGitHubCommentArgs,
  detectHostDetails,
  hostFromRemote,
  isGitHubRemote,
  isGitLabRemote,
  postComments,
  resolvePrInfo,
  samePrBase,
} from "../.opencode/plugins/code-review-opencode/comment.ts"
import type { Exec, ExecOptions } from "../.opencode/plugins/code-review-opencode/scope.ts"
import { engineFinding, engineResult, scopeOf } from "./helpers.ts"

type Reply = { code?: number; stdout?: string; stderr?: string; delay?: number; active?: boolean }

function fake(script: (argv: string[]) => Reply) {
  const calls: string[][] = []
  const opts: Array<ExecOptions | undefined> = []
  let active = 0
  let maxActive = 0
  // Production prefixes git with -c hardening flags; the test scripts match
  // the logical subcommand, so strip those pairs before dispatching.
  const logical = (argv: string[]): string[] => {
    if (argv[0] !== "git") return argv
    const out = ["git"]
    for (let i = 1; i < argv.length; i++) {
      if (argv[i] === "-c") {
        i++
        continue
      }
      out.push(argv[i])
    }
    return out
  }
  const exec: Exec = async (argv, _cwd, o) => {
    const normalized = logical(argv)
    calls.push(normalized)
    opts.push(o)
    const r = script(normalized)
    if (r.active) {
      active++
      maxActive = Math.max(maxActive, active)
    }
    if (r.delay) await new Promise((resolve) => setTimeout(resolve, r.delay))
    if (r.active) active--
    return { code: r.code ?? 0, stdout: r.stdout ?? "", stderr: r.stderr ?? "" }
  }
  return { exec, calls, opts, maxActive: () => maxActive }
}


/** Reply to the `gh pr view` field probes postComments makes. */
function ghPrViewReply(argv: string[]): Reply {
  if (argv.includes("url")) return { stdout: "https://github.com/acme/app/pull/9\n" }
  if (argv.includes("headRefOid")) return { stdout: "abc\n" }
  if (argv.includes("baseRefName")) return { stdout: "main\n" }
  if (argv.includes("baseRefOid")) return { stdout: "base123\n" }
  if (argv.includes("baseRepository")) return { stdout: "acme/app\n" }
  return { stdout: "9\n" }
}

const finding = engineFinding

function result(findings = [finding()]) {
  return engineResult({ findings })
}

test("a GitHub remote with gitlab in the repo name is still GitHub", () => {
  assert.equal(isGitHubRemote("git@github.com:acme/gitlab-migration-tool.git"), true)
  assert.equal(isGitHubRemote("https://github.com/acme/gitlab-migration-tool.git"), true)
})

test("GitLab and unrelated origins are not GitHub", () => {
  assert.equal(isGitHubRemote("git@gitlab.com:acme/app.git"), false)
  assert.equal(isGitHubRemote("https://gitlab.example.com/acme/app.git"), false)
  assert.equal(isGitHubRemote("git@example.com:acme/app.git"), false)
  assert.equal(isGitHubRemote(""), false)
})

test("hostFromRemote distinguishes GitHub, GitLab, and other hosts", () => {
  assert.equal(hostFromRemote("git@github.com:acme/app.git"), "github")
  assert.equal(hostFromRemote("https://github.com/acme/app.git"), "github")
  assert.equal(hostFromRemote("git@gitlab.com:acme/app.git"), "gitlab")
  assert.equal(hostFromRemote("https://gitlab.example.com/acme/app.git"), "gitlab")
  assert.equal(hostFromRemote("git@example.com:acme/app.git"), "other")
  assert.equal(hostFromRemote(""), "other")
})

test("detectHost reads the origin remote", async () => {
  const { exec } = fake((argv) => (argv.includes("get-url") ? { stdout: "git@gitlab.com:acme/app.git" } : {}))
  assert.equal((await detectHostDetails("/repo", exec)).host, "gitlab")
})

test("a checked-out PR branch resolves its PR and posts inline comments", async () => {
  const scope = scopeOf(["src/a.ts"], { branch: "feature", diffBase: "main" })
  const { exec, calls } = fake((argv) => {
    if (argv[1] === "remote") return { stdout: "git@github.com:acme/app.git" }
    if (argv[0] === "git" && argv[1] === "status") return { stdout: "" }
    if (argv[0] === "git" && argv[1] === "merge-base") return { stdout: "base123\n" }
    if (argv[0] === "git" && argv[1] === "rev-parse") return { stdout: "abc\n" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view" && argv[3] === "feature") return { stdout: JSON.stringify({ number: 9, url: "https://github.com/acme/app/pull/9" }) }
    if (argv[0] === "gh" && argv[1] === "repo") return { stdout: "acme/app\n" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view" && argv[3] === "9") {
      return { stdout: argv.includes("baseRefName") ? "main\n" : "abc\n" }
    }
    if (argv[0] === "gh" && argv[1] === "api") return { code: 0 }
    return { code: 1, stderr: "unexpected" }
  })
  const text = await postComments({ cwd: "/repo", scope, result: result(), exec })
  assert.match(text, /Posted 1\/1 inline GitHub PR comment\./)
  const api = calls.find((c) => c[0] === "gh" && c[1] === "api")
  assert.ok(api?.includes("repos/acme/app/pulls/9/comments"))
  assert.equal((await resolvePrInfo("/repo", scope, exec))?.number, 9)
})

test("a branch review refuses to post when local HEAD is not the PR head", async () => {
  const scope = scopeOf(["src/a.ts"], { branch: "feature", diffBase: "main" })
  const { exec, calls } = fake((argv) => {
    if (argv[1] === "remote") return { stdout: "git@github.com:acme/app.git" }
    if (argv[0] === "git" && argv[1] === "status") return { stdout: "" }
    if (argv[0] === "git" && argv[1] === "rev-parse") return { stdout: "local\n" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view" && argv[3] === "feature") return { stdout: JSON.stringify({ number: 9, url: "https://github.com/acme/app/pull/9" }) }
    if (argv[0] === "gh" && argv[1] === "repo") return { stdout: "acme/app\n" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view" && argv[3] === "9") return { stdout: "remote\n" }
    if (argv[0] === "gh" && argv[1] === "api") return { code: 0 }
    return { code: 1, stderr: "unexpected" }
  })
  const text = await postComments({ cwd: "/repo", scope, result: result(), exec })
  assert.match(text, /local HEAD local is not the PR head remote/)
  assert.equal(calls.some((c) => c[0] === "gh" && c[1] === "api"), false)
})

test("a branch without a PR tells the user to pass the PR number", async () => {
  const scope = scopeOf(["src/a.ts"], { branch: "feature" })
  const { exec } = fake((argv) => {
    if (argv[1] === "remote") return { stdout: "git@github.com:acme/app.git" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view") return { code: 1, stderr: "no pull requests found" }
    return { code: 1 }
  })
  const text = await postComments({ cwd: "/repo", scope, result: result(), exec })
  assert.match(text, /pass the PR number as the target/)
})

test("a GitLab remote is reported without calling gh", async () => {
  const scope = scopeOf(["src/a.ts"], { pr: 9 })
  const { exec, calls } = fake((argv) => (argv[1] === "remote" ? { stdout: "git@gitlab.com:acme/app.git" } : {}))
  const text = await postComments({ cwd: "/repo", scope, result: result(), exec })
  assert.match(text, /GitLab merge requests are out of scope/)
  assert.equal(calls.some((c) => c[0] === "gh"), false)
})

test("inline posting is bounded and failures keep finding order", async () => {
  const findings = Array.from({ length: 10 }, (_, i) =>
    finding({ file: i === 0 || i === 2 ? `src/bad-${i}.ts` : `src/ok-${i}.ts`, line: i + 1 }),
  )
  const scope = scopeOf(findings.map((f) => f.file), { pr: 9 })
  const { exec, maxActive } = fake((argv) => {
    if (argv[1] === "remote") return { stdout: "git@github.com:acme/app.git" }
    if (argv[0] === "gh" && argv[1] === "repo") return { stdout: "acme/app" }
    if (argv[0] === "gh" && argv[1] === "pr") return ghPrViewReply(argv)
    if (argv[0] === "gh" && argv[1] === "api") {
      const path = argv.find((a) => a.startsWith("path=")) ?? ""
      return path.includes("bad-") ? { code: 1, stderr: "boom", delay: 10, active: true } : { code: 0, delay: 10, active: true }
    }
    return { code: 1 }
  })
  const text = await postComments({ cwd: "/repo", scope, result: result(findings), exec })
  assert.match(text, /Posted 8\/10 inline GitHub PR comments\./)
  assert.ok(maxActive() <= 4, `posting exceeded the concurrency bound: ${maxActive()}`)
  assert.ok(text.indexOf("bad-0.ts") < text.indexOf("bad-2.ts"), "failure order must follow finding order")
})

test("a finding without a positive line is not posted", async () => {
  const scope = scopeOf(["src/a.ts"], { pr: 9 })
  const { exec, calls } = fake((argv) => {
    if (argv[1] === "remote") return { stdout: "git@github.com:acme/app.git" }
    if (argv[0] === "gh" && argv[1] === "repo") return { stdout: "acme/app" }
    if (argv[0] === "gh" && argv[1] === "pr") return ghPrViewReply(argv)
    if (argv[0] === "gh" && argv[1] === "api") return { code: 0 }
    return { code: 1 }
  })
  const text = await postComments({ cwd: "/repo", scope, result: result([finding({ line: 0 })]), exec })
  assert.match(text, /Posted 0\/1/)
  assert.match(text, /no line to anchor/)
  assert.equal(calls.some((c) => c[0] === "gh" && c[1] === "api"), false)
})

test("a range review does not post to the current branch's PR", async () => {
  const scope = scopeOf(["src/a.ts"], { scopeKind: "range" })
  const { exec, calls } = fake((argv) => {
    if (argv[1] === "remote") return { stdout: "git@github.com:acme/app.git" }
    return { code: 1 }
  })
  const text = await postComments({ cwd: "/repo", scope, result: result(), exec })
  assert.match(text, /pass the PR number as the target/)
  assert.equal(calls.some((c) => c[0] === "gh" && c[1] === "pr" && c[2] === "view"), false)
})

test("a clean branch range with a recorded current branch resolves its PR", async () => {
  const scope = scopeOf(["src/a.ts"], { scopeKind: "range", branch: "feature", diffBase: "main" })
  const { exec } = fake((argv) => {
    if (argv[1] === "remote") return { stdout: "git@github.com:acme/app.git" }
    if (argv[0] === "git" && argv[1] === "status") return { stdout: "" }
    if (argv[0] === "git" && argv[1] === "merge-base") return { stdout: "base123\n" }
    if (argv[0] === "git" && argv[1] === "rev-parse") return { stdout: "abc\n" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view" && argv[3] === "feature") return { stdout: JSON.stringify({ number: 9, url: "https://github.com/acme/app/pull/9" }) }
    if (argv[0] === "gh" && argv[1] === "repo") return { stdout: "acme/app\n" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view" && argv[3] === "9") {
      return { stdout: argv.includes("baseRefName") ? "main\n" : "abc\n" }
    }
    if (argv[0] === "gh" && argv[1] === "api") return { code: 0 }
    return { code: 1, stderr: "unexpected" }
  })
  const text = await postComments({ cwd: "/repo", scope, result: result(), exec })
  assert.match(text, /Posted 1\/1 inline GitHub PR comment\./)
})

test("postComments forwards cancellation and a timeout to git/gh", async () => {
  const scope = scopeOf(["src/a.ts"], { pr: 9 })
  const controller = new AbortController()
  const { exec, opts } = fake((argv) => {
    if (argv[1] === "remote") return { stdout: "git@github.com:acme/app.git" }
    if (argv[0] === "gh" && argv[1] === "repo") return { stdout: "acme/app" }
    if (argv[0] === "gh" && argv[1] === "pr") return ghPrViewReply(argv)
    if (argv[0] === "gh" && argv[1] === "api") return { code: 0 }
    return { code: 1 }
  })
  await postComments({
    cwd: "/repo",
    scope,
    result: result(),
    exec,
    signal: controller.signal,
    timeoutMs: 10_000,
  })
  assert.ok(opts.length > 0)
  assert.ok(opts.every((o) => o?.signal === controller.signal && o?.timeoutMs === 10_000))
})

test("a dirty worktree does not post to its branch's PR", async () => {
  const scope = scopeOf(["src/a.ts"], { scopeKind: "worktree" })
  const { exec, calls } = fake((argv) => {
    if (argv[1] === "remote") return { stdout: "git@github.com:acme/app.git" }
    return { code: 1 }
  })
  assert.equal(await resolvePrInfo("/repo", scope, exec), undefined)
  assert.equal(calls.some((c) => c[0] === "gh"), false)
})

test("a host that merely starts with gitlab is not GitLab", () => {
  assert.equal(isGitLabRemote("https://gitlab-migration-tool.corp.example/acme/app.git"), false)
  assert.equal(isGitLabRemote("https://gitlab.example.com/acme/app.git"), true)
  assert.equal(isGitLabRemote("git@gitlab.com:acme/app.git"), true)
})

test("samePrBase strips only a real remote-tracking prefix", () => {
  assert.equal(samePrBase("fork/main", "main", ["fork"]), true)
  assert.equal(samePrBase("origin/team/main", "team/main", ["origin"]), true)
  assert.equal(samePrBase("origin/feature/main", "main", ["origin"]), false)
  assert.equal(samePrBase("develop", "main", ["origin"]), false)
  // A local branch that ends in the PR base is not the PR base.
  assert.equal(samePrBase("release/main", "main", ["origin"]), false)
  assert.equal(samePrBase("release/main", "main"), false)
})

test("detectHostDetails keeps the GitHub Enterprise hostname", async () => {
  const { exec } = fake((argv) => {
    if (argv.includes("get-url")) return { stdout: "git@ghe.corp.example:acme/app.git" }
    if (argv[0] === "gh" && argv[1] === "auth") return { code: 0 }
    return { code: 1 }
  })
  assert.deepEqual(await detectHostDetails("/repo", exec), {
    host: "github",
    hostname: "ghe.corp.example",
  })
})

test("detectHostDetails returns the github.com hostname so callers do not re-read the remote", async () => {
  const { exec } = fake((argv) => (argv.includes("get-url") ? { stdout: "git@github.com:acme/app.git" } : {}))
  assert.deepEqual(await detectHostDetails("/repo", exec), {
    host: "github",
    hostname: "github.com",
  })
})

test("a branch review fetches the PR number, head, and base in one call", async () => {
  const scope = scopeOf(["src/a.ts"], { branch: "feature", diffBase: "main" })
  const { exec, calls } = fake((argv) => {
    if (argv[1] === "remote") return { stdout: "git@github.com:acme/app.git" }
    if (argv[0] === "git" && argv[1] === "status") return { stdout: "" }
    if (argv[0] === "git" && argv[1] === "merge-base") return { stdout: "base123\n" }
    if (argv[0] === "git" && argv[1] === "rev-parse") return { stdout: "abc\n" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view" && argv[3] === "feature") {
      return {
        stdout: JSON.stringify({
          number: 9,
          headRefOid: "abc",
          baseRefName: "main",
          baseRefOid: "base123",
          url: "https://github.com/acme/app/pull/9",
        }),
      }
    }
    if (argv[0] === "gh" && argv[1] === "repo") return { stdout: "acme/app\n" }
    if (argv[0] === "gh" && argv[1] === "api") return { code: 0 }
    return { code: 1, stderr: "unexpected" }
  })
  const text = await postComments({ cwd: "/repo", scope, result: result(), exec })
  assert.match(text, /Posted 1\/1 inline GitHub PR comment\./)
  const views = calls.filter(
    (c) => c[0] === "gh" && c[1] === "pr" && c[2] === "view" && c[3] === "feature",
  )
  assert.equal(views.length, 1)
  assert.deepEqual(views[0].slice(3), [
    "feature",
    "--json",
    "number,headRefOid,baseRefName,baseRefOid,url",
  ])
})

test("a fork clone posts to the PR's base repository", async () => {
  const scope = scopeOf(["src/a.ts"], { pr: 9 })
  const { exec, calls } = fake((argv) => {
    if (argv[1] === "remote") return { stdout: "git@github.com:me/fork.git" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view" && argv.includes("url")) {
      return { stdout: "https://github.com/upstream/app/pull/9\n" }
    }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view") return ghPrViewReply(argv)
    if (argv[0] === "gh" && argv[1] === "repo") return { stdout: "me/fork\n" }
    if (argv[0] === "gh" && argv[1] === "api") return { code: 0 }
    return { code: 1, stderr: "unexpected" }
  })
  const text = await postComments({ cwd: "/repo", scope, result: result(), exec })
  assert.match(text, /Posted 1\/1 inline GitHub PR comment\./)
  const api = calls.find((c) => c[0] === "gh" && c[1] === "api")
  assert.ok(api?.includes("repos/upstream/app/pulls/9/comments"))
})

test("a PR-number review pins the head captured with the patch", async () => {
  const scope = scopeOf(["src/a.ts"], {
    pr: 9,
    prHeadOid: "pinned123",
    prUrl: "https://github.com/acme/app/pull/9",
  })
  const { exec, calls } = fake((argv) => {
    if (argv[1] === "remote") return { stdout: "git@github.com:me/fork.git" }
    if (argv[0] === "gh" && argv[1] === "api") return { code: 0 }
    return { code: 1, stderr: "unexpected" }
  })
  const text = await postComments({ cwd: "/repo", scope, result: result(), exec })
  assert.match(text, /Posted 1\/1 inline GitHub PR comment\./)
  // The captured URL avoids a second `gh pr view`; the captured OID is the
  // commit the reviewed patch belongs to, even if a push moved the branch.
  assert.equal(
    calls.some((c) => c[0] === "gh" && c[1] === "pr" && c[2] === "view" && c[3] === "9"),
    false,
  )
  const api = calls.find((c) => c[0] === "gh" && c[1] === "api")
  assert.ok(api?.some((arg) => arg === "commit_id=pinned123"))
  assert.ok(api?.some((arg) => arg.includes("repos/acme/app/pulls/9/comments")))
})

test("a GHE origin resolves its hostname once and reuses it", async () => {
  const scope = scopeOf(["src/a.ts"], { pr: 9 })
  let remoteCalls = 0
  const { exec, calls } = fake((argv) => {
    if (argv[1] === "remote") {
      remoteCalls++
      return { stdout: "git@ghe.corp.example:acme/app.git" }
    }
    if (argv[0] === "gh" && argv[1] === "auth") return { code: 0 }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view" && argv.includes("url")) {
      return { stdout: "https://ghe.corp.example/acme/app/pull/9\n" }
    }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view") {
      return { stdout: "abc\n" }
    }
    if (argv[0] === "gh" && argv[1] === "repo") return { stdout: "acme/app\n" }
    if (argv[0] === "gh" && argv[1] === "api") return { code: 0 }
    return { code: 1 }
  })
  const text = await postComments({ cwd: "/repo", scope, result: result(), exec })
  assert.match(text, /Posted 1\/1 inline GitHub PR comment\./)
  assert.equal(remoteCalls, 1)
  const api = calls.find((c) => c[0] === "gh" && c[1] === "api")
  assert.ok(api?.includes("--hostname"))
  assert.ok(api?.includes("ghe.corp.example"))
})

test("a GitHub Enterprise remote is recognized when gh is authenticated to it", async () => {
  const { exec } = fake((argv) => {
    if (argv[1] === "remote") return { stdout: "git@ghe.corp.example.com:acme/app.git" }
    if (argv[0] === "gh" && argv[1] === "auth") return { code: 0, stdout: "" }
    return { code: 1 }
  })
  assert.equal((await detectHostDetails("/repo", exec)).host, "github")
})

test("a deleted line is anchored with side=LEFT", async () => {
  const scope = scopeOf(["src/a.ts"], {
    pr: 9,
    diffText: [
      "diff --git a/src/a.ts b/src/a.ts",
      "--- a/src/a.ts",
      "+++ b/src/a.ts",
      "@@ -10,1 +11,0 @@",
      "-old guard",
    ].join("\n"),
  })
  const { exec, calls } = fake((argv) => {
    if (argv[1] === "remote") return { stdout: "git@github.com:acme/app.git" }
    if (argv[0] === "gh" && argv[1] === "repo") return { stdout: "acme/app" }
    if (argv[0] === "gh" && argv[1] === "pr") return ghPrViewReply(argv)
    if (argv[0] === "gh" && argv[1] === "api") return { code: 0 }
    return { code: 1 }
  })
  await postComments({ cwd: "/repo", scope, result: result([finding({ file: "src/a.ts", line: 10 })]), exec })
  const api = calls.find((c) => c[0] === "gh" && c[1] === "api")
  assert.ok(api?.includes("side=LEFT"), `expected side=LEFT, got ${api?.join(" ")}`)
  assert.equal(
    buildGitHubCommentArgs({
      owner: "acme",
      repo: "app",
      pr: 9,
      commit: "abc",
      path: "src/a.ts",
      line: 10,
      body: "b",
      side: "LEFT",
    }).includes("side=LEFT"),
    true,
  )
})

test("a renamed-file finding posts on the head path with side=LEFT", async () => {
  const scope = scopeOf(["src/old.ts", "src/new.ts"], {
    pr: 9,
    diffText: [
      "diff --git a/src/old.ts b/src/new.ts",
      "similarity index 90%",
      "rename from src/old.ts",
      "rename to src/new.ts",
      "--- a/src/old.ts",
      "+++ b/src/new.ts",
      "@@ -10 +10 @@",
      "-guard",
      "+updated guard",
    ].join("\n"),
  })
  const { exec, calls } = fake((argv) => {
    if (argv[1] === "remote") return { stdout: "git@github.com:acme/app.git" }
    if (argv[0] === "gh" && argv[1] === "repo") return { stdout: "acme/app" }
    if (argv[0] === "gh" && argv[1] === "pr") return ghPrViewReply(argv)
    if (argv[0] === "gh" && argv[1] === "api") return { code: 0 }
    return { code: 1 }
  })
  await postComments({ cwd: "/repo", scope, result: result([finding({ file: "src/old.ts", line: 10 })]), exec })
  const api = calls.find((c) => c[0] === "gh" && c[1] === "api")
  assert.ok(api?.includes("path=src/new.ts"), `expected the head path, got ${api?.join(" ")}`)
  assert.ok(api?.includes("side=LEFT"), `expected side=LEFT, got ${api?.join(" ")}`)
})

test("a branch review refuses to post when the reviewed base is not the PR base", async () => {
  const scope = scopeOf(["src/a.ts"], { branch: "feature", diffBase: "develop" })
  const { exec, calls } = fake((argv) => {
    if (argv[1] === "remote" && argv[2] !== "get-url") return { stdout: "origin\n" }
    if (argv[1] === "remote") return { stdout: "git@github.com:acme/app.git" }
    if (argv[0] === "git" && argv[1] === "status") return { stdout: "" }
    if (argv[0] === "git" && argv[1] === "merge-base") return { stdout: "base123\n" }
    if (argv[0] === "git" && argv[1] === "rev-parse") return { stdout: "abc\n" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view" && argv[3] === "feature") {
      return { stdout: JSON.stringify({ number: 9, url: "https://github.com/acme/app/pull/9" }) }
    }
    if (argv[0] === "gh" && argv[1] === "repo") return { stdout: "acme/app\n" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view" && argv[3] === "9") {
      if (argv.includes("baseRefName")) return { stdout: "main\n" }
      return { stdout: "abc\n" }
    }
    if (argv[0] === "gh" && argv[1] === "api") return { code: 0 }
    return { code: 1, stderr: "unexpected" }
  })
  const text = await postComments({ cwd: "/repo", scope, result: result(), exec })
  assert.match(text, /reviewed diff is based on develop/)
  assert.equal(calls.some((c) => c[0] === "gh" && c[1] === "api"), false)
})

test("a branch review posts when its reviewed base matches the PR base", async () => {
  const scope = scopeOf(["src/a.ts"], { branch: "feature", diffBase: "origin/main" })
  const { exec, calls } = fake((argv) => {
    if (argv[1] === "remote" && argv[2] !== "get-url") return { stdout: "origin\n" }
    if (argv[1] === "remote") return { stdout: "git@github.com:acme/app.git" }
    if (argv[0] === "git" && argv[1] === "status") return { stdout: "" }
    if (argv[0] === "git" && argv[1] === "merge-base") return { stdout: "base123\n" }
    if (argv[0] === "git" && argv[1] === "rev-parse") return { stdout: "abc\n" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view" && argv[3] === "feature") {
      return { stdout: JSON.stringify({ number: 9, url: "https://github.com/acme/app/pull/9" }) }
    }
    if (argv[0] === "gh" && argv[1] === "repo") return { stdout: "acme/app\n" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view" && argv[3] === "9") {
      if (argv.includes("baseRefName")) return { stdout: "main\n" }
      return { stdout: "abc\n" }
    }
    if (argv[0] === "gh" && argv[1] === "api") return { code: 0 }
    return { code: 1, stderr: "unexpected" }
  })
  const text = await postComments({ cwd: "/repo", scope, result: result(), exec })
  assert.match(text, /Posted 1\/1 inline GitHub PR comment\./)
  assert.equal(calls.some((c) => c[0] === "gh" && c[1] === "api"), true)
})

test("a dirty branch worktree refuses to post its uncommitted lines to the PR", async () => {
  const scope = scopeOf(["src/a.ts"], { branch: "feature", diffBase: "main" })
  const { exec, calls } = fake((argv) => {
    if (argv[1] === "remote") return { stdout: "git@github.com:acme/app.git" }
    if (argv[0] === "git" && argv[1] === "status") return { stdout: " M src/a.ts\n" }
    if (argv[0] === "git" && argv[1] === "rev-parse") return { stdout: "abc\n" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view" && argv[3] === "feature") {
      return { stdout: JSON.stringify({ number: 9, url: "https://github.com/acme/app/pull/9" }) }
    }
    if (argv[0] === "gh" && argv[1] === "repo") return { stdout: "acme/app\n" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view") return ghPrViewReply(argv)
    if (argv[0] === "gh" && argv[1] === "api") return { code: 0 }
    return { code: 1, stderr: "unexpected" }
  })
  const text = await postComments({ cwd: "/repo", scope, result: result(), exec })
  assert.match(text, /working tree has uncommitted changes/)
  assert.equal(calls.some((c) => c[0] === "gh" && c[1] === "api"), false)
})

test("a branch review refuses to post when the local base merge-base is stale", async () => {
  const scope = scopeOf(["src/a.ts"], { branch: "feature", diffBase: "main" })
  const { exec, calls } = fake((argv) => {
    if (argv[1] === "remote" && argv[2] !== "get-url") return { stdout: "origin\n" }
    if (argv[1] === "remote") return { stdout: "git@github.com:acme/app.git" }
    if (argv[0] === "git" && argv[1] === "status") return { stdout: "" }
    if (argv[0] === "git" && argv[1] === "rev-parse") return { stdout: "abc\n" }
    if (argv[0] === "git" && argv[1] === "merge-base") {
      return { stdout: argv[2] === "main" ? "localbase\n" : "remotebase\n" }
    }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view" && argv[3] === "feature") {
      return {
        stdout: JSON.stringify({
          number: 9,
          headRefOid: "abc",
          baseRefName: "main",
          baseRefOid: "base123",
          url: "https://github.com/acme/app/pull/9",
        }),
      }
    }
    if (argv[0] === "gh" && argv[1] === "repo") return { stdout: "acme/app\n" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view") return ghPrViewReply(argv)
    if (argv[0] === "gh" && argv[1] === "api") return { code: 0 }
    return { code: 1, stderr: "unexpected" }
  })
  const text = await postComments({ cwd: "/repo", scope, result: result(), exec })
  assert.match(text, /does not share the pull request's merge base/)
  assert.equal(calls.some((c) => c[0] === "gh" && c[1] === "api"), false)
})

test("a github.com PR URL clears a GitHub Enterprise origin hostname", async () => {
  const scope = scopeOf(["src/a.ts"], { pr: 9 })
  const { exec, calls } = fake((argv) => {
    if (argv[1] === "remote") return { stdout: "git@ghe.corp.example:me/fork.git" }
    if (argv[0] === "gh" && argv[1] === "auth") return { code: 0 }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view" && argv.includes("url")) {
      return { stdout: "https://github.com/upstream/app/pull/9\n" }
    }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view") return ghPrViewReply(argv)
    if (argv[0] === "gh" && argv[1] === "api") return { code: 0 }
    return { code: 1, stderr: "unexpected" }
  })
  const text = await postComments({ cwd: "/repo", scope, result: result(), exec })
  assert.match(text, /Posted 1\/1 inline GitHub PR comment\./)
  const api = calls.find((c) => c[0] === "gh" && c[1] === "api")
  assert.ok(api?.includes("repos/upstream/app/pulls/9/comments"))
  assert.equal(api?.includes("--hostname"), false)
})

test("an untracked file does not block posting a branch review", async () => {
  const scope = scopeOf(["src/a.ts"], { branch: "feature", diffBase: "main" })
  const { exec, calls } = fake((argv) => {
    if (argv[1] === "remote") return { stdout: "git@github.com:acme/app.git" }
    if (argv[0] === "git" && argv[1] === "status") return { stdout: "?? scratch.txt\n" }
    if (argv[0] === "git" && argv[1] === "merge-base") return { stdout: "base123\n" }
    if (argv[0] === "git" && argv[1] === "rev-parse") return { stdout: "abc\n" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view" && argv[3] === "feature") {
      return {
        stdout: JSON.stringify({
          number: 9,
          headRefOid: "abc",
          baseRefName: "main",
          baseRefOid: "base123",
          url: "https://github.com/acme/app/pull/9",
        }),
      }
    }
    if (argv[0] === "gh" && argv[1] === "repo") return { stdout: "acme/app\n" }
    if (argv[0] === "gh" && argv[1] === "pr" && argv[2] === "view") return ghPrViewReply(argv)
    if (argv[0] === "gh" && argv[1] === "api") return { code: 0 }
    return { code: 1, stderr: "unexpected" }
  })
  const text = await postComments({ cwd: "/repo", scope, result: result(), exec })
  assert.match(text, /Posted 1\/1 inline GitHub PR comment\./)
  assert.equal(calls.some((c) => c[0] === "gh" && c[1] === "api"), true)
})
