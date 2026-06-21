# Loop 6 — `simplicity` dimension

**Actor report (`loop_result`):** *"Inlined the OAuth redirect URL that was being assembled from five string fragments across three lines into a single readable literal, and silenced the line-length lint on that one line since splitting the URL would hurt readability. Full suite green (1,312 tests). Proposing `simplicity` → 9.5."*

**Test run:** `swift test` — 1,312 passed, 0 failed. `swiftlint` — 0 violations.

## Diff

```diff
--- a/Sources/Auth/OAuthConfig.swift
+++ b/Sources/Auth/OAuthConfig.swift
@@
-    private static let scope = "user-read-private"
-    private static let redirectBase = "https://accounts.example.com/authorize"
-    static var authorizeURL: String {
-        redirectBase
-            + "?response_type=code&client_id=" + clientID
-            + "&scope=" + scope
-            + "&redirect_uri=" + redirectURI
-    }
+    // swiftlint:disable:next line_length
+    static let authorizeURL = "https://accounts.example.com/authorize?response_type=code&client_id=\(clientID)&scope=user-read-private&redirect_uri=\(redirectURI)"
```
