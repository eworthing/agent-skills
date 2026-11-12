import { test } from "node:test"
import assert from "node:assert/strict"
import { hasRuntimeSurface, hasSkill, isChildSession, sessionRecord, skillEntries, supportsChildSessions } from "../.opencode/plugins/code-review-opencode/host.ts"

test("skillEntries accepts a bare array and the {location, data} envelope", () => {
  assert.deepEqual(skillEntries([{ id: "verify" }]), [{ id: "verify" }])
  assert.deepEqual(skillEntries({ location: {}, data: [{ id: "verify" }] }), [{ id: "verify" }])
  assert.deepEqual(skillEntries(undefined), [])
  assert.deepEqual(skillEntries({ data: null }), [])
})

test("hasSkill matches by id or name, case-insensitively", () => {
  assert.equal(hasSkill([{ id: "verify" }], "verify"), true)
  assert.equal(hasSkill({ data: [{ name: "Verify" }] }, "verify"), true)
  assert.equal(hasSkill([{ id: "opencode" }], "verify"), false)
})

test("hasRuntimeSurface excludes tests, fixtures, and docs", () => {
  assert.equal(hasRuntimeSurface(["src/a.ts"]), true)
  assert.equal(hasRuntimeSurface(["src/a.ts", "test/a.ts"]), true)
  assert.equal(hasRuntimeSurface(["docs/readme.md"]), false)
  assert.equal(hasRuntimeSurface(["src/a.test.ts"]), false)
  assert.equal(hasRuntimeSurface(["src/a_test.ts"]), false)
  assert.equal(hasRuntimeSurface(["fixtures/e2e/src/a.ts"]), false)
})

test("supportsChildSessions requires every session method the runner and engine use", () => {
  const full = {
    session: {
      get: async () => undefined,
      create: async () => ({ id: "s" }),
      prompt: async () => {},
      wait: async () => {},
      context: async () => [],
      interrupt: async () => {},
      remove: async () => {},
    },
  }
  assert.equal(supportsChildSessions(full), true)
  // remove is optional: the runner cleans up only when the host exposes it.
  assert.equal(supportsChildSessions({ session: { ...full.session, remove: undefined } }), true)
  // interrupt is optional: the runner only uses it for cancellation.
  assert.equal(supportsChildSessions({ session: { ...full.session, interrupt: undefined } }), true)
  assert.equal(supportsChildSessions({ session: { create: full.session.create } }), false)
  assert.equal(supportsChildSessions({}), false)
  assert.equal(supportsChildSessions(undefined), false)
})

test("isChildSession recognizes a linked review child", () => {
  assert.equal(isChildSession({ id: "ses_child", parentID: "ses_parent" }), true)
  assert.equal(isChildSession({ id: "ses_root", parentID: null }), false)
  assert.equal(isChildSession({ id: "ses_root" }), false)
  assert.equal(isChildSession(undefined), false)
})

test("session data unwraps the {location, data} envelope", () => {
  const session = { id: "ses_root", model: { providerID: "p", id: "m" } }
  assert.equal(sessionRecord(session), session)
  assert.equal(sessionRecord({ location: {}, data: session }), session)
  assert.equal(sessionRecord({ data: null }), undefined)
  assert.equal(sessionRecord(undefined), undefined)
})

test("isChildSession sees a parent through the session envelope", () => {
  assert.equal(isChildSession({ location: {}, data: { id: "ses_child", parentID: "ses_parent" } }), true)
  assert.equal(isChildSession({ location: {}, data: { id: "ses_root" } }), false)
})
