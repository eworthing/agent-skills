[REFINE BLK-001] Valid, but the canonical blocker is broader: the plan lacks a short-lived, scoped, auditable authentication and authorization model for a PII-bearing admin export.
[REFINE BLK-002] Valid; the real blocker is an unbounded bulk-export contract, whether the fix is pagination, cursoring, or a bounded async export.
[REFINE BLK-003] Valid; Step 1 both lacks input validation and mixes incompatible query idioms, so the handler is unsafe and likely non-functional.
[AGREE BLK-004]
[REFINE BLK-005] Valid; because no tests are added, "CI passes" provides no meaningful release signal for this change.
[AGREE BLK-006]
[REFINE BLK-007] Valid, and it should explicitly include rollback or kill-switch capability in addition to feature flagging and monitoring.
[AGREE NB-001]
[AGREE NB-002]
[AGREE NB-003]
[AGREE NB-004]
[REFINE BLK-008] Same core concern as BLK-002: the endpoint is an unbounded export with no bounded retrieval strategy.
[REFINE BLK-009] Valid, but the issue is not only missing authn enforcement; the plan also omits authz, least privilege, and revocation.
[REFINE BLK-010] Same core concern as BLK-003; validation must cover enum constraints, date parsing, timezone handling, and 4xx behavior.
[REFINE NB-005] Real concern, but on a bulk PII endpoint the long-lived bearer token risk is part of the primary blocking auth model issue.
[AGREE NB-006]
[REFINE BLK-011] Same core blocker as BLK-001; the plan does not define a safe access model for this endpoint.
[AGREE BLK-012]
[REFINE BLK-013] Same core concern as BLK-002; low QPS does not make an unbounded one-shot export safe or reliable.
[AGREE NB-007]
[REFINE NB-008] Valid, but for a new external subscriber-data integration this rollout gap is blocking, not merely non-blocking.
[REFINE NB-009] Valid, but in this plan the absence of auth, filter, schema, and scale tests is a blocking release issue.
[REFINE BLK-014] The blocker is the lack of short-lived, attributable cross-account service identity; AWS role assumption and SigV4 are the natural fix here, but any equivalent audited mechanism would satisfy the concern.
[REFINE BLK-015] Replace the vendor/DPA wording with privacy and data-governance approval for cross-account PII sharing unless a third-party processor is actually involved.
[AGREE BLK-016]
[AGREE NB-010]
[AGREE NB-011]
[REFINE BLK-017] Same core blocker as BLK-001: no scoped authz, rotation, or admin-purpose check for a PII export.
[REFINE BLK-018] Same concern as BLK-015; the plan needs explicit privacy and data-flow approval for billing-to-marketing PII transfer.
[REFINE BLK-019] Same core concern as BLK-002: no pagination, cursor, or bounded export path.
[AGREE BLK-020]
[AGREE BLK-021]
[REFINE BLK-022] Same concern as BLK-004; auditability is required for a bulk PII export path.
[REFINE BLK-023] Same concern as BLK-006; the low expected QPS does not remove the need for scrape protection.
[AGREE BLK-024]
[REFINE BLK-025] Same concern as BLK-007, with rollback or emergency disable added explicitly.
[REFINE NB-012] Same concern as NB-001; docs-only contracts drift quickly.
[REFINE NB-013] Same concern as NB-002; an event-driven shape is worth evaluating to avoid bulk export semantics.
[REFINE NB-014] Same concern as NB-003; the data returned should go through minimization and classification review.
[REFINE NB-015] Same concern as NB-004; the route name implies a broader admin surface than the actual marketing-specific use case.
[REFINE NB-016] Same concern as NB-006; index strategy should be explicit if this endpoint will filter on status, tier, and last activity.
[REFINE NB-017] Same concern as NB-011; Step 1 is under-specified against the existing codebase modules.
[REFINE BLK-026] Same core blocker as BLK-001, with secure credential lifecycle management called out explicitly.
[REFINE BLK-027] Same core concern as BLK-003 and BLK-020; the sample query is both unvalidated and likely not executable.
[REFINE BLK-028] Same core concern as BLK-012 and BLK-021; returning `user.to_dict()` makes the response contract unsafe.
[REFINE BLK-029] Valid; both the test gap and the rollout gap are real blockers for this change.
[REFINE BLK-030] Same concern as BLK-004; the plan needs audit logging for who exported what, when, and how much.
[REFINE NB-018] Same concern as NB-002; event-driven delivery may be a better user-facing shape than a generic bulk-read endpoint.
[REFINE NB-019] Same concern as NB-001; generated or typed API contracts are safer than prose-only docs.
[AGREE BLK-031]
[REFINE BLK-032] Same core concern as BLK-002; the export contract is not bounded.
[REFINE BLK-033] Same core concern as BLK-003 and BLK-020; the query semantics and input handling are undefined safely.
[REFINE BLK-034] Same core concern as BLK-012 and BLK-021; explicit projection is required.
[REFINE BLK-035] Same concern as BLK-004, with incident response and compliance posture as the practical consequence.
[REFINE BLK-036] Same concern as BLK-006; lack of rate limiting undermines the low-QPS assumption.
[REFINE BLK-037] Same concern as BLK-029; "CI passes" is not a sufficient ship gate for a new subscriber-data export path.
[REFINE NB-020] Same concern as NB-001; prose docs alone will drift from implementation.
[REFINE NB-021] Same concern as NB-002 and NB-004; the endpoint shape reads as generic admin API but serves one marketing workflow.
[REFINE NB-022] Same concern as NB-003; the plan should justify why both `email` and `last_active_at` are necessary.
[REFINE NB-023] Same concerns as NB-006 and NB-007; client behavior depends on both index support and precise date semantics.

### Reasoning
From a user-impact perspective, this is not a low-risk additive endpoint. The plan turns an internal billing data pull into a reusable API that exports subscriber PII across an account boundary to a marketing workflow. Step 2 proposes a long-lived bearer token shared with an external Lambda, which is the wrong trust model for a PII-bearing admin surface: it provides weak caller identity, no scoped authorization, and no clean rotation or revocation path. The claim in lines 42-46 that no rollout plan is needed because the change is additive is not defensible; additive data-export endpoints can still fail badly through overexposure, misuse, or lack of an emergency stop.

The implementation details are also not execution-ready. Step 1 mixes PyMongo and Django ORM patterns, accepts raw strings for both filters, and returns `user.to_dict()` instead of the explicit response contract promised in Goals. Even if the handler were corrected, the API is still an unbounded full export with no pagination or bounded export job, no audit logging, no rate limiting, and no meaningful test or rollout gate. Low request rate does not mitigate large payloads, Lambda memory/runtime limits, or the blast radius of a leaked credential. This plan needs a safer contract and a real delivery strategy before it should be executed.

### Blocking Issues
- [B1] (HIGH) The access model is unsafe for a PII-bearing admin export. Step 2 proposes a long-lived bearer token shared with an external Lambda, with no scoped authorization, rotation or revocation plan, or attributable cross-account service identity.
  Section: Step 2 — Wire up the Lambda (lines 32-35)
  Recommendation: Replace the static token with short-lived service-to-service auth that enforces least privilege and caller identity; in AWS, cross-account role assumption with signed requests is the natural fit. Add an explicit admin or business-purpose authorization check.

- [B2] (HIGH) The endpoint is designed as an unbounded bulk export. Returning "every active user" as a single list with no pagination, cursoring, or bounded export mechanism will become unreliable as the subscriber base grows, regardless of the low QPS assumption.
  Section: Step 1 — Add the route handler (lines 19-27)
  Recommendation: Define a bounded retrieval contract such as pagination or cursoring, or switch to an async export or event-driven design with size and failure limits.

- [B3] (HIGH) The proposed handler is not implementable safely as written. `db.users.find(...)` suggests PyMongo, but the code then uses Django-style `.filter(...)` and `__gte` syntax, while `tier` and `active_since` remain unvalidated strings.
  Section: Step 1 — Add the route handler (lines 19-27)
  Recommendation: Choose the actual data-access layer, build the query in that idiom, validate `tier` against an allowed enum, parse `active_since` as ISO8601 with explicit timezone behavior, and define 4xx error handling.

- [B4] (HIGH) The implementation violates the stated response contract by returning `user.to_dict()` instead of an explicit projection of approved fields. That can leak unintended fields and makes the API unstable for the Lambda consumer.
  Section: Step 1 — Add the route handler (lines 21-27)
  Recommendation: Return an explicit serializer or projection containing only `{id, email, tier, subscribed_at, last_active_at}` and define that schema in code, not only in docs.

- [B5] (HIGH) The plan creates a new cross-account bulk PII export path without audit logging or an explicit privacy and data-governance gate. That weakens incident response and leaves the sharing decision under-specified.
  Section: Step 2 — Wire up the Lambda (lines 32-35)
  Recommendation: Add audit logs for caller identity, filters, result count, request ID, and timestamp, and require privacy/security approval for the billing-to-marketing data flow before rollout.

- [B6] (MEDIUM) The design assumes very low usage but adds no endpoint-specific rate limiting or scrape protection. A leaked credential would allow fast repeated export of the subscriber dataset.
  Section: Step 2 — Wire up the Lambda (lines 32-35)
  Recommendation: Add endpoint-level rate limits, quotas, and abuse monitoring sized to the actual Lambda use case.

- [B7] (HIGH) The release plan is not safe for a new external subscriber-data integration. There are no tests for auth, filtering, schema shape, or large-result behavior, and Step 4/Rollout has no feature flag, canary, monitoring, alerts, or emergency disable path.
  Section: Step 4 — Ship / Rollout (lines 40-46)
  Recommendation: Add test coverage, rollout metrics and alerts, a feature flag or kill switch, and a rollback runbook before deployment.

### Non-Blocking Issues
- [N1] The API contract is documented only in `docs/api.md`, which is likely to drift from implementation.
  Section: Step 3 — Document the endpoint (lines 36-38)
  Recommendation: Define the request and response schema in code using the framework's typed or OpenAPI facilities and generate docs from that source.

- [N2] The endpoint shape and name imply a generic admin surface, but the actual consumer is one marketing renewal workflow; an event-driven or workflow-specific interface may be clearer and safer.
  Section: Context / Goals (lines 5-11)
  Recommendation: Re-evaluate whether this should be a marketing-specific export contract or an event stream instead of `/admin/users`.

- [N3] The plan does not justify why both `email` and `last_active_at` are necessary from a data-minimization standpoint.
  Section: Goals (lines 9-11)
  Recommendation: Run a data-classification and minimization review and consider using opaque user IDs or a downstream communication service to reduce blast radius.

- [N4] Performance and client behavior will depend on precise date semantics and supporting indexes, but neither is defined.
  Section: Step 1 — Add the route handler (lines 21-26)
  Recommendation: Specify timezone and precision rules for `active_since` and document the required index strategy for the chosen query pattern.

- [N5] Step 1 assumes `router`, `db`, and `Optional` already exist without pointing to the actual modules or patterns in this codebase.
  Section: Step 1 — Add the route handler (lines 17-30)
  Recommendation: Reference the concrete existing modules and route-registration pattern so the implementation step is directly executable.

### Confidence
HIGH

### Scope
architecture, security, privacy/compliance, API design, correctness, testing, rollout/operability, performance

VERDICT: REVISE