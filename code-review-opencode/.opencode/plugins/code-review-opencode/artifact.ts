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
import { createHash } from "node:crypto"
import { mkdir, rename, rm, writeFile } from "node:fs/promises"
import { join } from "node:path"
import type { EngineResult } from "./engine.ts"

export type ReportArtifact = {
  report_id: string
  run_id: string
  parent_session_id: string
  scope_id: string
  requested_target?: string
  model: { provider_id: string; id: string; variant?: string } | null
  terminal_status: "complete" | "incomplete" | "failed" | "cancelled"
  terminal_outcome: string
  truncated: boolean
  diagnostics: string[]
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
  result?: EngineResult
  files: string[]
  parentSessionId: string
  scopeId: string
  requestedTarget?: string
  model?: { provider_id: string; id: string; variant?: string }
  terminalStatus?: ReportArtifact["terminal_status"]
  terminalOutcome?: string
  diagnostics?: string[]
  /** Override for tests or hosts that keep state outside the repository. */
  directory?: string
}

export function buildReportArtifact(opts: {
  result?: EngineResult
  files: string[]
  id: string
  generatedAt: Date
  parentSessionId: string
  scopeId: string
  requestedTarget?: string
  model?: { provider_id: string; id: string; variant?: string }
  terminalStatus?: ReportArtifact["terminal_status"]
  terminalOutcome?: string
  diagnostics?: string[]
}): ReportArtifact {
  const result = opts.result
  const truncated = result?.truncatedFrom !== undefined
  const diagnostics = [
    ...(opts.diagnostics ?? []),
    ...(result?.terminalFailure ? [result.terminalFailure] : []),
    ...(result?.warnings ?? []),
  ]
  const terminalStatus = opts.terminalStatus ?? (result?.terminalFailure
    ? "failed"
    : result?.partial || truncated
      ? "incomplete"
      : "complete")
  return {
    report_id: opts.id,
    run_id: opts.id,
    parent_session_id: opts.parentSessionId,
    scope_id: opts.scopeId,
    ...(opts.requestedTarget !== undefined ? { requested_target: opts.requestedTarget } : {}),
    model: opts.model ? { ...opts.model } : null,
    terminal_status: terminalStatus,
    terminal_outcome: opts.terminalOutcome ?? (result?.terminalFailure ? "provider_error" : terminalStatus),
    truncated,
    diagnostics,
    generated_at: opts.generatedAt.toISOString(),
    level: result?.level ?? "unknown",
    cell: result?.cell ?? "unknown",
    summary: result?.summary ?? opts.diagnostics?.join("; ") ?? "Review did not produce an engine report.",
    files_changed: [...opts.files],
    fanned_out: result?.stats.finders ?? 0,
    refuted: result?.refuted.map((r) => ({ ...r })) ?? [],
    stats: result ? { ...result.stats } : { finders: 0, candidates: 0, verifierAgents: 0, verified: 0, refuted: 0, dupes: 0, budgetDropped: 0, reported: 0 },
    partial: result?.partial ?? true,
    warnings: [...(result?.warnings ?? [])],
    findings: result?.findings.map((f) => ({ ...f })) ?? [],
    ...(result?.truncatedFrom !== undefined ? { truncated_from: result.truncatedFrom } : {}),
  }
}

/** Stable identity for the exact reviewed scope and captured snapshot. */
export function scopeIdentity(scope: {
  root: string
  target?: string
  scopeKind?: string
  diffBase?: string
  prHeadOid?: string
  files: string[]
  diffText?: string
}): string {
  const snapshot = createHash("sha256").update(scope.diffText ?? "").digest("hex")
  return createHash("sha256")
    .update(JSON.stringify({
      root: scope.root,
      target: scope.target ?? "",
      scopeKind: scope.scopeKind ?? "",
      diffBase: scope.diffBase ?? "",
      prHeadOid: scope.prHeadOid ?? "",
      files: [...scope.files].sort(),
      snapshot,
    }))
    .digest("hex")
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
    const payload = `${JSON.stringify(buildReportArtifact({ ...opts, files: opts.files, id, generatedAt }), null, 2)}\n`
    // Write privately, then rename so a reader never sees a half-written file.
    await writeFile(temp, payload, { encoding: "utf8", mode: 0o600 })
    await rename(temp, path)
    return path
  } catch {
    await rm(temp, { force: true }).catch(() => {})
    return undefined
  }
}
