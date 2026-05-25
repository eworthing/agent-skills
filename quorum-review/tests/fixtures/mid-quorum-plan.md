# Plan: add /admin/users endpoint to billing-api

## Context

The billing team needs to query active subscribers across all tiers for the upcoming Q3 renewal campaign. Today they pull this from the database directly using a read-only credential. Marketing wants a programmatic API so they can trigger the renewal-reminder workflow without DB access.

## Goals

1. Expose a `GET /admin/users` endpoint on `billing-api` returning `{id, email, tier, subscribed_at, last_active_at}` for every active user.
2. Allow filtering by tier (`?tier=pro|enterprise|free`) and by activity window (`?active_since=ISO8601`).
3. Marketing's automation hits this endpoint from a Lambda; expected QPS is < 1.

## Steps

### Step 1 — Add the route handler

In `src/api/admin.py`, add:

```python
@router.get("/admin/users")
def list_users(tier: Optional[str] = None, active_since: Optional[str] = None):
    query = db.users.find({"status": "active"})
    if tier:
        query = query.filter(tier=tier)
    if active_since:
        query = query.filter(last_active_at__gte=active_since)
    return [user.to_dict() for user in query]
```

Register the route in `src/api/__init__.py` after the existing `/billing` group.

### Step 2 — Wire up the Lambda

Marketing's Lambda lives in their AWS account. We give them an API key with a long-lived bearer token. The Lambda includes the token in the `Authorization` header.

### Step 3 — Document the endpoint

Add a new section to `docs/api.md` describing the endpoint, parameters, and response shape. Include a `curl` example.

### Step 4 — Ship

Merge to `main` after CI passes. Deploy goes out with the next nightly release.

## Rollout

No rollout plan needed because the endpoint is additive — existing endpoints are untouched. If Marketing reports issues, we'll iterate.
