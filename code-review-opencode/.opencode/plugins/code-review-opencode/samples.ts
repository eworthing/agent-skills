/**
 * Placeholder leaf values shared by the generated schema examples and the
 * parser's schema-echo detector. Keeping them in one module lets `schemas.ts`
 * generate the `Expected shape:` text and `json.ts` recognize an unlabeled copy
 * without either importing the other (which would close the
 * json -> schemas -> reportfindings -> json cycle).
 */
export const SAMPLE_VALUE: Record<string, unknown> = {
  file: "path/to/file.ts",
  line: 1,
  summary: "one sentence",
  failure_scenario: "concrete input/state -> wrong output",
  verdict: "CONFIRMED",
  evidence: "line 12: ...",
  index: 0,
  merge: 1,
}
