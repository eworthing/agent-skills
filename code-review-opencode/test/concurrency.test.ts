import { test } from "node:test"
import assert from "node:assert/strict"
import { mapLimit } from "../.opencode/plugins/code-review-opencode/concurrency.ts"

test("mapLimit preserves input order and bounds concurrency", async () => {
  let active = 0
  let maxActive = 0
  const values = await mapLimit([1, 2, 3, 4, 5], 2, async (n) => {
    active++
    maxActive = Math.max(maxActive, active)
    await new Promise((resolve) => setTimeout(resolve, 5))
    active--
    return n * 2
  })
  assert.deepEqual(values, [2, 4, 6, 8, 10])
  assert.equal(maxActive, 2)
})

test("mapLimit awaits in-flight work before rethrowing", async () => {
  const started = Date.now()
  await assert.rejects(
    () =>
      mapLimit([1, 2], 2, async (n) => {
        if (n === 1) throw new Error("boom")
        await new Promise((resolve) => setTimeout(resolve, 30))
        return n
      }),
    /boom/,
  )
  // The sibling was allowed to finish instead of being orphaned.
  assert.ok(Date.now() - started >= 20, "rejected before the in-flight sibling settled")
})
