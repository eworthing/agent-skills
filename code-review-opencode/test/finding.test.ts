import { test } from "node:test"
import assert from "node:assert/strict"
import { envInt, pluralize, pluralWord, renderedLocation } from "../.opencode/plugins/code-review-opencode/finding.ts"

test("envInt clamps above Node's maximum timer delay", () => {
  process.env.CODE_REVIEW_TEST_INT = "999999999999999"
  try {
    assert.equal(envInt("CODE_REVIEW_TEST_INT"), 2_147_483_647)
  } finally {
    delete process.env.CODE_REVIEW_TEST_INT
  }
})

test("pluralize includes the count while pluralWord does not", () => {
  assert.equal(pluralize(3, "candidate"), "3 candidates")
  assert.equal(pluralize(1, "candidate"), "1 candidate")
  assert.equal(pluralize(0, "candidate"), "0 candidates")
  assert.equal(pluralWord(3, "candidate"), "candidates")
})

test("renderedLocation escapes line and paragraph separators", () => {
  assert.equal(renderedLocation({ file: "src/a\u2028b.ts" }), "src/a\\u{2028}b.ts")
  assert.equal(renderedLocation({ file: "src/a\u2029b.ts" }), "src/a\\u{2029}b.ts")
})

test("envInt keeps zero and rejects invalid spellings", () => {
  process.env.CODE_REVIEW_TEST_INT = "0"
  try {
    assert.equal(envInt("CODE_REVIEW_TEST_INT"), 0)
    process.env.CODE_REVIEW_TEST_INT = "1.5"
    assert.equal(envInt("CODE_REVIEW_TEST_INT"), undefined)
  } finally {
    delete process.env.CODE_REVIEW_TEST_INT
  }
})
