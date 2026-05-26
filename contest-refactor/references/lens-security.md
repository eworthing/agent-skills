# Security Lens (always-included)

This lens augments the selected stack lens (`lens-apple.md`, `lens-generic.md`). Step 0 loads it alongside the stack lens unconditionally — security concerns are cross-cutting and not stack-specific. Findings here typically score under `framework_idioms` (platform best practices) or `credibility` (when a violation undermines trustworthy claims).

## Contents

- [Input validation & deeplinks](#input-validation--deeplinks)
- [Secrets handling](#secrets-handling)
- [PII in logs & telemetry](#pii-in-logs--telemetry)
- [Keychain & secure storage](#keychain--secure-storage)
- [Biometric & local auth](#biometric--local-auth)
- [Transport security](#transport-security)
- [Dependency hygiene](#dependency-hygiene)

## Input validation & deeplinks

Untrusted input includes: URL-scheme params (`https://app/?id=...`), universal-links, pasteboard, push-notification payloads, app-extension shared containers, IPC payloads, query strings from third-party callbacks.

1. **Deeplink/URL-scheme params**: every incoming URL param used as an identifier (cue id, account id, lookup key) must be validated against an expected shape before use. Pattern: `if let id = UUID(uuidString: param)` not `let id = param`. Hits: `grep -rn 'URL(string:\|incomingURL\|onOpenURL\|application(_:open:' Sources/` — each handler's body must show a validation step.
2. **Pasteboard reads**: `UIPasteboard.general.string` returns arbitrary user data; treat as input. Don't pass directly to `URL(string:)`, `JSONDecoder`, or any code expecting a specific shape without validation.
3. **Push notification payload**: `userInfo` dictionary keys/values from APNS are untrusted (Apple does not validate content). Validate shape before routing to feature code.
4. **App-extension shared containers**: data read from `App Group` containers (`UserDefaults(suiteName:)`, `FileManager.containerURL`) was last written by another process; treat as input even though the process is "yours".
5. **Third-party callback query strings**: OAuth/social-login redirect URLs land in your URL-scheme handler. Validate `state` parameter matches the one you sent (CSRF protection); validate `code` shape before posting to your token endpoint.

## Secrets handling

1. **No plaintext keys in source.** Audit: `grep -rnE 'api[_-]?key|secret|token|password|bearer' Sources/ Resources/ Tests/` (case-insensitive) — every hit must be either (a) a variable name in code that reads from a secure store, (b) a placeholder in a `.xcconfig.example` file, or (c) a test fixture with a clearly fake value. Real values committed to source = Likely Disqualifier.
2. **`.xcconfig` files**: production `*.xcconfig` files must contain build-tier toggles only — no secrets. Production secrets live in a `*.local.xcconfig` file that is `.gitignore`d (mirror the existing `Spotify.local.xcconfig` pattern). Hits: `find . -name '*.xcconfig' -not -path './build/*'` — every file's content must not match the secret-shape grep above.
3. **Hardcoded URLs to internal services**: production backend URLs should be config-driven, not hardcoded. Hardcoded internal-tooling URLs (Grafana, staging endpoints) in committed code = a leakage class.

## PII in logs & telemetry

1. **`os_log` / `Logger` privacy annotations**: by default, `%@` interpolation of non-static strings is `public` (visible in Console.app + sysdiagnose). User data (email, name, identifiers, free-form input) must use `%{private}@` or the `Logger` privacy modifier `\(value, privacy: .private)`. Hits: `grep -rn 'os_log\|Logger()\|Logger(subsystem:' Sources/` — every interpolation site needs an explicit `public`/`private` annotation; absence is a finding.
2. **Crash-reporter user identifiers**: Firebase Crashlytics / Sentry / Bugsnag `setUserId` must use a stable hashed identifier (per-install UUID), never email/phone/account-id verbatim. Audit: `grep -rn 'setUserId\|setUser(' Sources/`.
3. **Analytics events with user content**: tracking events that include free-form user input (cue names, board titles, search queries) leak content to the analytics provider. Either redact (`name.prefix(2) + "***"`), hash, or omit the field. Audit: every `track(`, `logEvent(`, `Analytics.log(` call site.
4. **Filenames + paths in logs**: user-typed filenames in `os_log` leak content. Same `%{private}@` rule applies.

## Keychain & secure storage

1. **`kSecAttrAccessible` explicitness**: every `SecItemAdd` / `Keychain.set` call must set `kSecAttrAccessible` explicitly. Default is `kSecAttrAccessibleWhenUnlocked` which syncs to iCloud Keychain — usually wrong for app-local secrets. Prefer `kSecAttrAccessibleWhenUnlockedThisDeviceOnly` (non-syncing) for tokens/keys; `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly` for items needed during background launch. Hits: `grep -rn 'kSecAttrAccessible\|SecItemAdd\|KeychainAccess\.' Sources/` — every Keychain write needs explicit accessibility set.
2. **Token rotation**: long-lived refresh tokens stored in Keychain must have a rotation policy (expiry tracked; refresh-on-401 path exists). Tokens written once, never rotated = stale-credential class bug.
3. **`UserDefaults` is not secure storage**: any key in `UserDefaults` matching `*token*`, `*secret*`, `*password*`, `*api*key*` is a Serious finding; move to Keychain.

## Biometric & local auth

1. **`LAContext.evaluatePolicy` rationale**: every biometric prompt needs a clear `localizedReason` explaining what the user is authorizing. Generic "Authenticate" = a finding (user can't make an informed consent). Hits: `grep -rn 'evaluatePolicy\|LAContext' Sources/`.
2. **Fall-through on biometric failure**: handle the `LAError.userCancel` / `LAError.userFallback` / `LAError.biometryLockout` cases distinctly. Treating all failures as "denied" hides the lockout class.
3. **Don't gate destructive actions on biometric-only**: delete-account, send-money-type actions should require an additional confirmation. Biometric prompt that auto-confirms-on-success is a UX safety class.

## Transport security

1. **TLS configuration**: `URLSessionConfiguration.default` enforces ATS (App Transport Security). Audit: `grep -rn 'NSAppTransportSecurity\|NSAllowsArbitraryLoads\|TLSMinimumSupportedProtocol' Sources/ Resources/Info.plist` — any non-default value needs justification in code comments.
2. **Certificate pinning**: if this app talks to a backend you control, pin the server certificate or public key (`URLSessionDelegate.urlSession(_:didReceive challenge:)`). Absent on a security-sensitive app = a finding under `framework_idioms`.
3. **WebView traffic**: `WKWebView` can be configured with `WKWebsiteDataStore.nonPersistent()` for private browsing; loaded URLs should be HTTPS-only. Audit `WKWebView` instantiation sites for HTTP fallback.

## Dependency hygiene

1. **SPM dependency lock**: `Package.resolved` must be committed. Audit: `ls Package.resolved` exists; `cat Package.resolved | jq '.pins | length'` matches `grep -c '.package(' Package.swift`.
2. **Stale dependencies**: dependencies pinned to commits/branches (`branch: "main"`) rather than versions are a supply-chain class risk. Audit: `grep -rn 'branch:\|revision:' Package.swift` — each pin needs a comment explaining why an immutable version isn't sufficient.
3. **Unreviewed dependencies with native code**: any SPM dependency containing C/C++/Obj-C/Swift system framework imports gets full process privilege. Audit: a one-time review per dependency on update; cite the SHA reviewed in a comment.

## Stack-agnostic security checks

These apply on any stack (the lens-security.md file loads alongside `lens-generic.md` for non-Apple repos):

- **SQL injection**: any string-concatenated SQL is a Likely Disqualifier. Use parameterized queries.
- **Command injection**: `Process.run(["sh", "-c", "cmd " + userInput])` is the same class as SQL injection.
- **Path traversal**: any user-supplied path written to disk needs `..` rejection + canonical-form check.
- **XSS in WebView**: HTML interpolated with user data needs context-aware escaping.
- **Insecure deserialization**: never deserialize untrusted data into types that allow arbitrary code construction.
