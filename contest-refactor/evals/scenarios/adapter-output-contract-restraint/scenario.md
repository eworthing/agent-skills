# Loop 14 - `data_flow` dimension

**Actor report (`loop_result`):** *"Moved auth refresh scheduling behind the `AuthClient.Session` stream. The adapter now publishes the SDK token expiry directly through the Interface, and the scheduler consumes that value in tests. Full suite green (731 tests). Proposing `data_flow` -> 9.5."*

**Test run:** `swift test` - 731 passed, 0 failed.

## Context

`AuthClient.Session` is the application Interface emitted by the adapter. Downstream `RefreshScheduler` reads `session.expiresAt` to schedule token renewal before expiry. The external SDK delegate provides the token expiry date on every successful authorization.

## Diff

```diff
--- a/Sources/Auth/LiveAuthAdapter.swift
+++ b/Sources/Auth/LiveAuthAdapter.swift
@@
 final class LiveAuthAdapter: SDKAuthDelegate {
     private let updates: AsyncStream<AuthClient.Session>.Continuation

     func authSDK(_ sdk: AuthSDK, didAuthorize token: SDKToken) {
         updates.yield(AuthClient.Session(
             userID: UserID(rawValue: token.subject),
             accessToken: token.value,
+            expiresAt: token.expiresAt
         ))
     }
 }
--- a/Tests/Auth/RefreshSchedulerTests.swift
+++ b/Tests/Auth/RefreshSchedulerTests.swift
@@
     @Test func schedulesRefreshBeforePublishedExpiry() async {
         let expiry = clock.now.advanced(by: .seconds(3600))
         authUpdates.yield(.init(userID: userID, accessToken: "abc", expiresAt: expiry))

         await scheduler.drain()

         #expect(scheduler.nextRefresh == expiry.advanced(by: .seconds(-300)))
     }
```

The adapter publishes the fact that the Interface promises, and a downstream test asserts the scheduler consumes that exact value. There is no dropped SDK fact and no need for adapter-local stored state.
