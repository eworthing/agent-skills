## Review Contract

You are reviewing a plan or spec as part of a multi-reviewer quorum panel.

Structure your review using EXACTLY these sections:

### Reasoning
Write your complete analysis of the plan here. Consider architecture,
security, testing, performance, and any other relevant areas. This
section MUST come before your issue lists.

### Blocking Issues
Issues that MUST be resolved before execution. Use [B1], [B2], etc.
Optionally include per-issue confidence: (HIGH), (MEDIUM), or (LOW).
For each issue, include a Section: line referencing the plan section name
and line numbers from the numbered plan (e.g., Section: Step 3 (lines 42-55)).
- [B1] (HIGH) Description of blocking issue...
  Section: <plan section> (lines <N-M>)
  Recommendation: Concrete fix or mitigation
- [B2] (MEDIUM) Description of blocking issue...
(Write "None" if no blocking issues.)

### Non-Blocking Issues
Suggestions and improvements. Use [N1], [N2], etc.
- [N1] Description...
  Section: <plan section> (lines <N-M>)
  Recommendation: Suggested improvement
(Write "None" if no non-blocking issues.)

### Confidence
State your confidence in this review: HIGH, MEDIUM, or LOW

### Scope
Which areas of the plan does your review cover? (e.g., "architecture",
"security", "testing", "API design", "performance")

Your review MUST end with a verdict on the LAST non-empty line:
- `VERDICT: APPROVED` if the plan is ready to execute as-is
- `VERDICT: REVISE` if changes are needed before execution

The verdict line must be EXACTLY one of these two strings, nothing else.

## Cross-Critique Instructions

Below are anonymous reviews from the prior round and the current issue ledger.

### Part 1: Respond to every open issue

For EACH open issue in the Current Issue Ledger section below, write exactly
one response. Every issue needs your position — if you skip an issue, the
orchestrator records no data from you on it, which weakens the consensus.

- `[AGREE BLK-001]` — you confirm this issue is valid
- `[DISAGREE BLK-001] reason` — you dispute this issue (include your reasoning)
- `[REFINE BLK-001] revised description` — the concern is valid but you want to
  adjust its scope or description (counts as support, like AGREE)

You may also raise entirely new issues discovered in this round:
- `[B-NEW] description` — new blocking issue
- `[N-NEW] description` — new non-blocking issue

Put all cross-critique responses together BEFORE your review sections.

### Part 2: Updated structured review

After your cross-critique responses, provide your full updated review using
the standard sections (### Reasoning, ### Blocking Issues, ### Non-Blocking
Issues, ### Confidence, ### Scope) and end with your VERDICT line.

### Example round 2+ response

```
[AGREE BLK-001]
[DISAGREE BLK-002] The plan already handles this via the retry middleware
[REFINE NB-001] Should also cover WebSocket connections, not just HTTP
[B-NEW] No rate limiting on the public API endpoints

### Reasoning
After reviewing the other panelists' feedback...

### Blocking Issues
- [B1] (HIGH) BLK-001 remains unaddressed — auth is still missing
  Section: Auth middleware (lines 12-18)
  Recommendation: Add role-based access control before deployment
- [B2] (MEDIUM) New: No rate limiting on public API
  Section: API gateway (lines 34-40)
  Recommendation: Add token-bucket rate limiter

### Non-Blocking Issues
None

### Confidence
HIGH

### Scope
security, API design

VERDICT: REVISE
```

## Panel Context

You are reviewer 2 of 3 in a quorum review panel.
Your private role for this round is: Constraint Guardian.
This is round 3. All reviewer identities are anonymous.

## Reviews from Previous Round

## Open Issue Ledger

| ID | Severity | Description |
|-----|----------|-------------|
| BLK-001 | blocking | Bearer-token auth with no rotation, scope, or admin authz ch |
| BLK-002 | blocking | No pagination — endpoint returns every active user in one re |
| BLK-003 | blocking | No input validation on `tier` or `active_since`; query code  |
| BLK-004 | blocking | No audit logging on PII bulk export — GDPR/CCPA exposure. |
| BLK-005 | blocking | No tests added; CI gate meaningless. |
| BLK-006 | blocking | No rate limit despite < 1 QPS design — compromised token = f |
| BLK-007 | blocking | Rollout has no feature flag, canary, monitoring, or alerts. |
| NB-001 | non_blocking | No OpenAPI/typed schema — `docs/api.md` will drift from impl |
| NB-002 | non_blocking | Consider whether bulk PII export is the right shape vs. even |
| NB-003 | non_blocking | Response schema includes `email + last_active_at` — data cla |
| NB-004 | non_blocking | Endpoint named `/admin/users` but consumed by Marketing auto |
| BLK-008 | blocking | Unbounded Response Payload (Missing Pagination) |
| BLK-009 | blocking | Missing Authentication Enforcement |
| BLK-010 | blocking | Missing Input Validation |
| NB-005 | non_blocking | Long-Lived Bearer Token Risk |
| NB-006 | non_blocking | Database Indexing Constraints |
| BLK-011 | blocking | The plan does not define or enforce authentication/authoriza |
| BLK-012 | blocking | The implementation violates the stated response contract by  |
| BLK-013 | blocking | The endpoint is designed to return every active user in a si |
| NB-007 | non_blocking | `active_since` is treated as an unvalidated string, which le |
| NB-008 | non_blocking | The rollout plan is too thin for a new external admin integr |
| NB-009 | non_blocking | The plan does not mention tests for filtering, auth failures |
| BLK-014 | blocking | Cross-account PII egress (billing AWS → marketing AWS) lacks |
| BLK-015 | blocking | No DPA / vendor-data-flow review for PII leaving billing tru |
| BLK-016 | blocking | No rollback plan. "Deploy with nightly" + PII leak = no kill |
| NB-010 | non_blocking | Consider tokenized/opaque user id + send email only via down |
| NB-011 | non_blocking | Step 1 imports/`db`/`router`/`Optional` unspecified — plan a |
| BLK-017 | blocking | AuthN/AuthZ undefined: long-lived bearer token, no rotation, |
| BLK-018 | blocking | Cross-account PII egress lacks DPA/vendor-flow review. |
| BLK-019 | blocking | Unbounded response: no pagination/cursor. Returns every acti |
| BLK-020 | blocking | Code does not execute. `db.users.find(...)` returns pymongo  |
| BLK-021 | blocking | Response uses `user.to_dict()` — leaks unintended fields (pa |
| BLK-022 | blocking | No audit logging on PII bulk export. GDPR Art. 30 / CCPA exp |
| BLK-023 | blocking | No rate limit despite <1 QPS design intent. Compromised toke |
| BLK-024 | blocking | No tests. CI gate meaningless. (consolidates BLK-005/NB-009) |
| BLK-025 | blocking | Rollout has no feature flag, canary, monitoring, alerts, rol |
| NB-012 | non_blocking | No OpenAPI/typed schema — `docs/api.md` drifts. |
| NB-013 | non_blocking | Consider event-driven shape: publish `renewal-due` events to |
| NB-014 | non_blocking | `email + last_active_at` returned — data classification revi |
| NB-015 | non_blocking | Endpoint named `/admin/users` but consumed by marketing auto |
| NB-016 | non_blocking | DB index strategy unspecified. `status + tier + last_active_ |
| NB-017 | non_blocking | Step 1 references `router`, `db`, `Optional` without imports |
| BLK-026 | blocking | Missing Authentication, Authorization, and Secure Credential |
| BLK-027 | blocking | Missing Input Validation and Broken Query Syntax |
| BLK-028 | blocking | Response Contract Violation (PII Leakage) |
| BLK-029 | blocking | Missing Testing and Rollout Strategy |
| BLK-030 | blocking | No Audit Logging for Bulk PII Export |
| NB-018 | non_blocking | Event-Driven Alternative |
| NB-019 | non_blocking | Schema Drift Risk |
| BLK-031 | blocking | BLK-001/009/011: The authentication and authorization model  |
| BLK-032 | blocking | BLK-002/008/013: The endpoint is an unbounded bulk export wi |
| BLK-033 | blocking | BLK-003/010: Input handling is not defined safely, and the s |
| BLK-034 | blocking | BLK-012: The implementation violates the stated response con |
| BLK-035 | blocking | BLK-004: The plan introduces a bulk PII export path with no  |
| BLK-036 | blocking | BLK-006: The plan omits endpoint-specific rate limiting even |
| BLK-037 | blocking | BLK-005/007: The release plan has no meaningful quality or r |
| NB-020 | non_blocking | NB-001: Docs-only API description in `docs/api.md` will drif |
| NB-021 | non_blocking | NB-002/NB-004: The endpoint shape and naming suggest a gener |
| NB-022 | non_blocking | NB-003: The plan does not show a data-classification or mini |
| NB-023 | non_blocking | NB-006/NB-007: Performance and client behavior will depend o |

## Prior Round Issue Lists (condensed)

### Reviewer A — VERDICT: REVISE
**Blocking:**
- [B1] AuthN/AuthZ undefined: long-lived bearer token, no rotation, no scope, no admin-role check. PII endpoint open to credential leak.
- [B2] Cross-account PII egress lacks DPA/vendor-flow review.
- [B3] Unbounded response: no pagination/cursor. Returns every active user one shot. Will OOM client + server as base grows. (consolidates BLK-002/008/013)
- [B4] Code does not execute. `db.users.find(...)` returns pymongo cursor; `.filter(tier=...)` is Django ORM. Mutually incompatible. (consolidates BLK-003/010)
- [B5] Response uses `user.to_dict()` — leaks unintended fields (password_hash, internal flags). Contract violation.
- [B6] No audit logging on PII bulk export. GDPR Art. 30 / CCPA exposure.
- [B7] No rate limit despite <1 QPS design intent. Compromised token = full scrape.
- [B8] No tests. CI gate meaningless. (consolidates BLK-005/NB-009)
- [B9] Rollout has no feature flag, canary, monitoring, alerts, rollback. (consolidates BLK-007/NB-008)
**Non-blocking:**
- [N1] No OpenAPI/typed schema — `docs/api.md` drifts.
- [N2] Consider event-driven shape: publish `renewal-due` events to SQS/SNS instead of pull. Avoids bulk PII transit.
- [N3] `email + last_active_at` returned — data classification review missing.
- [N4] Endpoint named `/admin/users` but consumed by marketing automation. Scope confusion.
- [N5] DB index strategy unspecified. `status + tier + last_active_at` likely needs composite index.
- [N6] Step 1 references `router`, `db`, `Optional` without imports/existing-module context.

### Reviewer B — VERDICT: REVISE
**Blocking:**
- [B1] Missing Authentication, Authorization, and Secure Credential Management
- [B2] Unbounded Response Payload (Missing Pagination)
- [B3] Missing Input Validation and Broken Query Syntax
- [B4] Response Contract Violation (PII Leakage)
- [B5] Missing Testing and Rollout Strategy
- [B6] No Audit Logging for Bulk PII Export
**Non-blocking:**
- [N1] Database Indexing Constraints
- [N2] Event-Driven Alternative
- [N3] Schema Drift Risk

### Reviewer C — VERDICT: REVISE
**Blocking:**
- [B1] BLK-001/009/011: The authentication and authorization model is unsafe and underspecified for a PII-bearing admin endpoint. A long-lived bearer token shared with an external Lambda does not establish least privilege, admin authorization, rotation, or revocation.
- [B2] BLK-002/008/013: The endpoint is an unbounded bulk export with no pagination, cursoring, or bounded export strategy, so the contract becomes less reliable as the user base grows.
- [B3] BLK-003/010: Input handling is not defined safely, and the sample query likely does not work because it mixes Mongo-style `find(...)` with Django-style `.filter(...)` and `__gte` syntax.
- [B4] BLK-012: The implementation violates the stated response contract by returning `user.to_dict()`, which can leak extra user fields and makes the API unstable for Marketing.
- [B5] BLK-004: The plan introduces a bulk PII export path with no audit logging, which weakens incident response and compliance posture.
- [B6] BLK-006: The plan omits endpoint-specific rate limiting even though the stated design assumes very low usage; a leaked credential would allow rapid full-dataset scraping.
- [B7] BLK-005/007: The release plan has no meaningful quality or rollout gate. “CI passes” is not sufficient when the plan adds a new external dependency carrying subscriber data, especially with no tests, feature flag, monitoring, alerts, or fast disable path.
**Non-blocking:**
- [N1] NB-001: Docs-only API description in `docs/api.md` will drift from implementation.
- [N2] NB-002/NB-004: The endpoint shape and naming suggest a generic admin surface, but the actual consumer is a specific Marketing renewal workflow.
- [N3] NB-003: The plan does not show a data-classification or minimization review for exposing `email` and `last_active_at`.
- [N4] NB-006/NB-007: Performance and client behavior will depend on indexes and precise date semantics, but neither is defined.


## Current Issue Ledger

- **BLK-001** (blocking): Bearer-token auth with no rotation, scope, or admin authz check on a PII-bulk endpoint.
- **BLK-002** (blocking): No pagination — endpoint returns every active user in one response.
- **BLK-003** (blocking): No input validation on `tier` or `active_since`; query code mixes Mongo + Django ORM idioms and likely does not execute.
- **BLK-004** (blocking): No audit logging on PII bulk export — GDPR/CCPA exposure.
- **BLK-005** (blocking): No tests added; CI gate meaningless.
- **BLK-006** (blocking): No rate limit despite < 1 QPS design — compromised token = full-scrape.
- **BLK-007** (blocking): Rollout has no feature flag, canary, monitoring, or alerts.
- **NB-001** (non_blocking): No OpenAPI/typed schema — `docs/api.md` will drift from implementation.
- **NB-002** (non_blocking): Consider whether bulk PII export is the right shape vs. event-driven (publish renewal-due events to SQS/SNS).
- **NB-003** (non_blocking): Response schema includes `email + last_active_at` — data classification review missing.
- **NB-004** (non_blocking): Endpoint named `/admin/users` but consumed by Marketing automation — naming implies broader scope than reality.
- **BLK-008** (blocking): Unbounded Response Payload (Missing Pagination)
- **BLK-009** (blocking): Missing Authentication Enforcement
- **BLK-010** (blocking): Missing Input Validation
- **NB-005** (non_blocking): Long-Lived Bearer Token Risk
- **NB-006** (non_blocking): Database Indexing Constraints
- **BLK-011** (blocking): The plan does not define or enforce authentication/authorization for the new admin endpoint, and the proposed access model is a long-lived bearer token shared with an external Lambda. That leaves a PII-bearing endpoint exposed to credential leakage and does not establish least privilege, rotation, or revocation expectations.
- **BLK-012** (blocking): The implementation violates the stated response contract by returning `user.to_dict()` instead of an explicit projection of `{id, email, tier, subscribed_at, last_active_at}`. That can leak unintended user fields and makes the API contract unstable for Marketing.
- **BLK-013** (blocking): The endpoint is designed to return every active user in a single response with no pagination, cursoring, or export strategy. That is likely to become unreliable for the Lambda consumer as the subscriber base grows, regardless of the low request rate.
- **NB-007** (non_blocking): `active_since` is treated as an unvalidated string, which leaves input parsing, timezone handling, and error behavior ambiguous for clients.
- **NB-008** (non_blocking): The rollout plan is too thin for a new external admin integration carrying subscriber data; additive changes can still fail in production from a consumer perspective.
- **NB-009** (non_blocking): The plan does not mention tests for filtering, auth failures, schema shape, or large-result behavior.
- **BLK-014** (blocking): Cross-account PII egress (billing AWS → marketing AWS) lacks IAM-role-assumption / STS pattern. Bearer token = no audit trail at trust boundary, no per-call identity. Use IAM sigv4 + assumed role with `sts:ExternalId`, not static token.
- **BLK-015** (blocking): No DPA / vendor-data-flow review for PII leaving billing trust boundary into marketing automation. Legal/privacy review missing as a gating step.
- **BLK-016** (blocking): No rollback plan. "Deploy with nightly" + PII leak = no kill switch. Need feature flag + emergency-disable runbook.
- **NB-010** (non_blocking): Consider tokenized/opaque user id + send email only via downstream comms service. Reduces blast radius of leak.
- **NB-011** (non_blocking): Step 1 imports/`db`/`router`/`Optional` unspecified — plan assumes infra that may not exist. Plan should reference concrete existing modules.
- **BLK-017** (blocking): AuthN/AuthZ undefined: long-lived bearer token, no rotation, no scope, no admin-role check. PII endpoint open to credential leak.
- **BLK-018** (blocking): Cross-account PII egress lacks DPA/vendor-flow review.
- **BLK-019** (blocking): Unbounded response: no pagination/cursor. Returns every active user one shot. Will OOM client + server as base grows. (consolidates BLK-002/008/013)
- **BLK-020** (blocking): Code does not execute. `db.users.find(...)` returns pymongo cursor; `.filter(tier=...)` is Django ORM. Mutually incompatible. (consolidates BLK-003/010)
- **BLK-021** (blocking): Response uses `user.to_dict()` — leaks unintended fields (password_hash, internal flags). Contract violation.
- **BLK-022** (blocking): No audit logging on PII bulk export. GDPR Art. 30 / CCPA exposure.
- **BLK-023** (blocking): No rate limit despite <1 QPS design intent. Compromised token = full scrape.
- **BLK-024** (blocking): No tests. CI gate meaningless. (consolidates BLK-005/NB-009)
- **BLK-025** (blocking): Rollout has no feature flag, canary, monitoring, alerts, rollback. (consolidates BLK-007/NB-008)
- **NB-012** (non_blocking): No OpenAPI/typed schema — `docs/api.md` drifts.
- **NB-013** (non_blocking): Consider event-driven shape: publish `renewal-due` events to SQS/SNS instead of pull. Avoids bulk PII transit.
- **NB-014** (non_blocking): `email + last_active_at` returned — data classification review missing.
- **NB-015** (non_blocking): Endpoint named `/admin/users` but consumed by marketing automation. Scope confusion.
- **NB-016** (non_blocking): DB index strategy unspecified. `status + tier + last_active_at` likely needs composite index.
- **NB-017** (non_blocking): Step 1 references `router`, `db`, `Optional` without imports/existing-module context.
- **BLK-026** (blocking): Missing Authentication, Authorization, and Secure Credential Management
- **BLK-027** (blocking): Missing Input Validation and Broken Query Syntax
- **BLK-028** (blocking): Response Contract Violation (PII Leakage)
- **BLK-029** (blocking): Missing Testing and Rollout Strategy
- **BLK-030** (blocking): No Audit Logging for Bulk PII Export
- **NB-018** (non_blocking): Event-Driven Alternative
- **NB-019** (non_blocking): Schema Drift Risk
- **BLK-031** (blocking): BLK-001/009/011: The authentication and authorization model is unsafe and underspecified for a PII-bearing admin endpoint. A long-lived bearer token shared with an external Lambda does not establish least privilege, admin authorization, rotation, or revocation.
- **BLK-032** (blocking): BLK-002/008/013: The endpoint is an unbounded bulk export with no pagination, cursoring, or bounded export strategy, so the contract becomes less reliable as the user base grows.
- **BLK-033** (blocking): BLK-003/010: Input handling is not defined safely, and the sample query likely does not work because it mixes Mongo-style `find(...)` with Django-style `.filter(...)` and `__gte` syntax.
- **BLK-034** (blocking): BLK-012: The implementation violates the stated response contract by returning `user.to_dict()`, which can leak extra user fields and makes the API unstable for Marketing.
- **BLK-035** (blocking): BLK-004: The plan introduces a bulk PII export path with no audit logging, which weakens incident response and compliance posture.
- **BLK-036** (blocking): BLK-006: The plan omits endpoint-specific rate limiting even though the stated design assumes very low usage; a leaked credential would allow rapid full-dataset scraping.
- **BLK-037** (blocking): BLK-005/007: The release plan has no meaningful quality or rollout gate. “CI passes” is not sufficient when the plan adds a new external dependency carrying subscriber data, especially with no tests, feature flag, monitoring, alerts, or fast disable path.
- **NB-020** (non_blocking): NB-001: Docs-only API description in `docs/api.md` will drift from implementation.
- **NB-021** (non_blocking): NB-002/NB-004: The endpoint shape and naming suggest a generic admin surface, but the actual consumer is a specific Marketing renewal workflow.
- **NB-022** (non_blocking): NB-003: The plan does not show a data-classification or minimization review for exposing `email` and `last_active_at`.
- **NB-023** (non_blocking): NB-006/NB-007: Performance and client behavior will depend on indexes and precise date semantics, but neither is defined.

## Changes Since Last Round (by HOST)

N/A (first round)

## Updated Plan

 1	# Plan: add /admin/users endpoint to billing-api
 2	
 3	## Context
 4	
 5	The billing team needs to query active subscribers across all tiers for the upcoming Q3 renewal campaign. Today they pull this from the database directly using a read-only credential. Marketing wants a programmatic API so they can trigger the renewal-reminder workflow without DB access.
 6	
 7	## Goals
 8	
 9	1. Expose a `GET /admin/users` endpoint on `billing-api` returning `{id, email, tier, subscribed_at, last_active_at}` for every active user.
10	2. Allow filtering by tier (`?tier=pro|enterprise|free`) and by activity window (`?active_since=ISO8601`).
11	3. Marketing's automation hits this endpoint from a Lambda; expected QPS is < 1.
12	
13	## Steps
14	
15	### Step 1 — Add the route handler
16	
17	In `src/api/admin.py`, add:
18	
19	```python
20	@router.get("/admin/users")
21	def list_users(tier: Optional[str] = None, active_since: Optional[str] = None):
22	    query = db.users.find({"status": "active"})
23	    if tier:
24	        query = query.filter(tier=tier)
25	    if active_since:
26	        query = query.filter(last_active_at__gte=active_since)
27	    return [user.to_dict() for user in query]
28	```
29	
30	Register the route in `src/api/__init__.py` after the existing `/billing` group.
31	
32	### Step 2 — Wire up the Lambda
33	
34	Marketing's Lambda lives in their AWS account. We give them an API key with a long-lived bearer token. The Lambda includes the token in the `Authorization` header.
35	
36	### Step 3 — Document the endpoint
37	
38	Add a new section to `docs/api.md` describing the endpoint, parameters, and response shape. Include a `curl` example.
39	
40	### Step 4 — Ship
41	
42	Merge to `main` after CI passes. Deploy goes out with the next nightly release.
43	
44	## Rollout
45	
46	No rollout plan needed because the endpoint is additive — existing endpoints are untouched. If Marketing reports issues, we'll iterate.
47	
