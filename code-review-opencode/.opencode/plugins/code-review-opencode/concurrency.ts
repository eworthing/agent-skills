/**
 * Bounded worker pool shared by the review engine and PR comment posting.
 * Results keep the input order, so callers can build deterministic output.
 */
export async function mapLimit<T, R>(
  items: T[],
  limit: number,
  fn: (item: T, index: number) => Promise<R>,
): Promise<R[]> {
  const results = new Array<R>(items.length)
  let cursor = 0
  // Stop dispatching new items once a worker fails, but await every in-flight
  // worker before rethrowing. Otherwise a rejection leaves already-started
  // child sessions running after the caller has moved on.
  let failed = false
  const workers = Array.from(
    { length: Math.min(Math.max(1, limit), Math.max(1, items.length)) },
    async () => {
      while (!failed) {
        const index = cursor++
        if (index >= items.length) return
        try {
          results[index] = await fn(items[index], index)
        } catch (error) {
          failed = true
          throw error
        }
      }
    },
  )
  const settled = await Promise.allSettled(workers)
  const firstRejection = settled.find((s): s is PromiseRejectedResult => s.status === "rejected")
  if (firstRejection) throw firstRejection.reason
  return results
}
