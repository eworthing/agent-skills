/**
 * Persistent report artifact.
 *
 * The user-facing contract stays the terminal renderer or the bare `--json`
 * array. This file is the machine-readable record of the same run: the engine
 * result plus the scope and fan-out that produced it. A later run, a host UI,
 * or a debugging session can read it without replaying the review.
 *
 * Writes are best-effort. A read-only checkout, a sandboxed host, or a full
 * disk must not turn a completed review into an error. The plugin only invokes
 * this when CODE_REVIEW_REPORT_DIR opts in, so a normal review never dirties
 * the repository it inspected.
 */
import { randomUUID } from "node:crypto"
import { mkdir, rename, rm, writeFile } from "node:fs/promises"
import { join } from "node:path"
import type { EngineResult } from "./engine.ts"

export type ReportArtifact = {
  report_id: string
  generated_at: string
  level: string
  cell: string
  /** The synthesizer's prose summary, or the engine's fallback summary. */
  summary: string
  files_changed: string[]
  fanned_out: number
  refuted: EngineResult["refuted"]
  stats: EngineResult["stats"]
  partial: boolean
  warnings: string[]
  findings: EngineResult["findings"]
  truncated_from?: number
}

export type ArtifactOptions = {
  root: string
  result: EngineResult
  files: string[]
  /** Override for tests or hosts that keep state outside the repository. */
  directory?: string
}

export function buildReportArtifact(opts: {
  result: EngineResult
  files: string[]
  id: string
  generatedAt: Date
}): ReportArtifact {
  const { result } = opts
  return {
    report_id: opts.id,
    generated_at: opts.generatedAt.toISOString(),
    level: result.level,
    cell: result.cell,
    summary: result.summary,
    files_changed: [...opts.files],
    fanned_out: result.stats.finders,
    refuted: result.refuted.map((r) => ({ ...r })),
    stats: { ...result.stats },
    partial: result.partial,
    warnings: [...result.warnings],
    findings: result.findings.map((f) => ({ ...f })),
    ...(result.truncatedFrom !== undefined ? { truncated_from: result.truncatedFrom } : {}),
  }
}

/** `<timestamp>-<uuid>.json`, filesystem-safe and sortable. */
export function artifactFileName(id: string, generatedAt: Date): string {
  return `${generatedAt.toISOString().replace(/[:.]/g, "-")}-${id}.json`
}

export async function writeReportArtifact(opts: ArtifactOptions): Promise<string | undefined> {
  const id = randomUUID()
  const generatedAt = new Date()
  const dir = opts.directory ?? join(opts.root, ".opencode", "code-review-opencode", "reports")
  const path = join(dir, artifactFileName(id, generatedAt))
  const temp = `${path}.tmp-${process.pid}`
  try {
    await mkdir(dir, { recursive: true })
    const payload = `${JSON.stringify(buildReportArtifact({ result: opts.result, files: opts.files, id, generatedAt }), null, 2)}\n`
    // Write privately, then rename so a reader never sees a half-written file.
    await writeFile(temp, payload, { encoding: "utf8", mode: 0o600 })
    await rename(temp, path)
    return path
  } catch {
    await rm(temp, { force: true }).catch(() => {})
    return undefined
  }
}
