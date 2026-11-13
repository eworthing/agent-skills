import { test } from "node:test"
import assert from "node:assert/strict"
import { envInt } from "../.opencode/plugins/code-review-opencode/finding.ts"

test("envInt clamps above Node's maximum timer delay", () => {
  process.env.CODE_REVIEW_TEST_INT = "999999999999999"
  try {
    assert.equal(envInt("CODE_REVIEW_TEST_INT"), 2_147_483_647)
  } finally {
    delete process.env.CODE_REVIEW_TEST_INT
  }
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
