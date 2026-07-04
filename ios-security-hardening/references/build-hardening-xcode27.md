# Build-Time Hardening (Xcode 27 Enhanced Security)

Runtime input-validation (the rest of this skill) defends against attacker-controlled
*data*. This reference covers the complementary *compile-time and process-level* hardening
Xcode 27 exposes through the **Enhanced Security** capability: control-flow integrity,
memory-safety enforcement, and security diagnostics.

Verified against **Xcode 27 beta 2 (build 27A5209h), iPhoneOS27.0 SDK** (re-checked 2026-07-04;
originally 27A5194q / 2026-06-18). No Xcode 27 GM has shipped yet — the stable channel is still
Xcode 26.x — so the "re-verify names against the SDK in use" caveat below stays in force. Beta 2
extended Enhanced Security support to visionOS. Re-verify setting/entitlement names against the
SDK in use before relying on them — names and defaults can shift across betas. Source of truth:
Xcode's bundled "audit-xcode-security-settings" skill + Apple developer documentation.

**Lineage (avoid over-indexing on "27").** Enhanced Security debuted at **WWDC 2025 / Xcode 26 /
iOS 26**, and Memory Integrity Enforcement (MIE) is the **Sep 2025 / iPhone 17** hardware feature
(see below) — neither is new in iOS 27. Xcode 27 is the *current tooling*; the `-string`
entitlement variants and guard objects arrived in the 26.4 cycle. This doc says "Xcode 27" because
that is what you build with today, not because the protections are 27-only.

## Scope — when this applies

- **Process-level protections** (Enhanced Security capability + entitlements) apply to any
  app/target on **iOS, iPadOS, macOS, visionOS, DriverKit** — they harden the running
  process regardless of source language, so they help even a pure-Swift app.
- **Clang code-diagnostic / allocator settings** only matter if the target contains
  **C / C++ / Objective-C / Objective-C++** sources. Do **not** enable clang-only settings
  for a pure-Swift target — they do nothing but add noise.
- Supported product types: application, on-demand-install app, xpc-service, driver-extension
  (build settings only — no entitlements on DriverKit), system-extension, tool. Skip
  frameworks, test bundles, and other extensions.
- **Not on:** watchOS, tvOS, or any Simulator (no arm64e — see Pointer Authentication).

## The master switch — `ENABLE_ENHANCED_SECURITY`

Set **one** build setting at project level and most of the hardening cascades on:

```
ENABLE_ENHANCED_SECURITY = YES
```

It automatically configures (do **not** set these manually — the cascade owns them, and the
Release/Debug split is handled for you):

| Cascaded setting | Effect |
|---|---|
| `GCC_WARN_SHADOW` | `-Wshadow` — shadowed variable declarations |
| `CLANG_WARN_EMPTY_BODY` | `-Wempty-body` — empty control-flow bodies |
| `ENABLE_SECURITY_COMPILER_WARNINGS` | `-Wformat-nonliteral`, `-Warray-bounds`, `-Wbuiltin-memcpy-chk-size`, `-Wreturn-stack-address`, … |
| `CLANG_CXX_STANDARD_LIBRARY_HARDENING` | hardened libc++ (`fast` in Release, `debug` in Debug) — runtime container/iterator checks only |
| `CLANG_ENABLE_C_TYPED_ALLOCATOR_SUPPORT` | passes C type info to the allocator (pairs with the `hardened-heap` entitlement) |
| `CLANG_ENABLE_CPLUSPLUS_TYPED_ALLOCATOR_SUPPORT` | same, for C++ |

Pointer authentication is also required by the capability but is set as its own key (below).

## Build settings to set explicitly

| Setting | Value | Notes |
|---|---|---|
| `ENABLE_ENHANCED_SECURITY` | `YES` | Master switch (above). Project level. |
| `ENABLE_POINTER_AUTHENTICATION` | `YES` | Builds arm64e + signs pointers. Project level; **override to `NO` per-target on non-arm64e platforms** (watchOS/tvOS/Simulator) or those builds fail. |

### Pointer authentication (arm64e)

Signs pointers (return addresses, function/vtable pointers) and traps on mismatch —
mitigates control-flow hijacking and ROP/JOP. Hardware-signed, so overhead is low. Caveats:

- Code that manipulates raw pointers, casts function-pointer types, or uses pointer inline
  asm may crash — test thoroughly.
- arm64e binaries are distinct from arm64. **Binary** dependencies need an arm64e slice; an
  arm64-only XCFramework fails to link — request a universal (arm64 + arm64e) build.
- SPM dependencies are **not** built arm64e automatically. Opt in via the implicit workspace:

```bash
WS=MyProject.xcodeproj/project.xcworkspace/xcshareddata/WorkspaceSettings.xcsettings
plutil -create xml1 "$WS"
plutil -insert iOSPackagesShouldBuildARM64e -bool YES "$WS"
# repeat per platform you ship: macOSPackagesShouldBuildARM64e, visionOSPackagesShouldBuildARM64e
```

### Stack zero-initialization (cascade-independent, lowest-risk first step)

```
CLANG_ENABLE_STACK_ZERO_INIT = YES
```

Zeroes automatic/stack variables, closing info-leak and use-of-uninitialized-value bugs.
No source changes; zeroing memory cannot introduce a crash; runtime cost is minimal in most
code paths (not strictly free — the compiler emits the init). Apple flags it as one of the
safest features to adopt first. (Also cascaded by Enhanced Security; listed here because
it's a safe standalone starting point.)

## Entitlements (per-target `.entitlements`)

Enhanced Security's runtime protections are provisioned by the `hardened-process` entitlement
family. Without the main toggle the runtime pieces are inert.

**Required:**

```xml
<key>com.apple.security.hardened-process</key><true/>
<key>com.apple.security.hardened-process.enhanced-security-version-string</key><string>2</string>
```

**Availability:** the `-string` entitlement variants
(`enhanced-security-version-string`, `platform-restrictions-string`) require an **iOS/iPadOS/
macOS/visionOS 26.4+ runtime** — not 26.0. Their default is the `*` wildcard (auto-latest);
setting `"2"` pins the current generation.

**Default-ON (add when missing):**

- `com.apple.security.hardened-process.hardened-heap` — extra type-isolation allocator
  buckets at runtime; most effective with the cascaded typed-allocator settings.
- `com.apple.security.hardened-process.dyld-ro` — marks dyld state read-only.
- `com.apple.security.hardened-process.platform-restrictions-string` = `"2"` — dyld + Mach
  messaging restrictions.

**Deprecated (remove if present alongside `hardened-process`):**
`…platform-restrictions` (→ `-string` variant) and `…enhanced-security-version`
(→ `-version-string` variant). If you see `…version-string = "1"` or the deprecated
version key, migrate to `"2"`.

## Guard objects (free once you set `version-string = "2"`)

iOS/macOS **26.4+** added an automatic use-after-free defense: freed memory (both VM mappings
and heap allocations) is replaced with inaccessible **guard regions**, so a dangling access
traps instead of reading reused memory. It turns on **automatically** whenever
`enhanced-security-version-string ≥ "2"` — which the required entitlement above already sets — so
you get it for free with no extra key. It is hardware-independent (unlike MTE below).

Opt out **only** if profiling shows a real regression, via:

```xml
<key>com.apple.security.hardened-process.no-guard-objects</key><true/>
```

## Hardware Memory Tagging (MTE) — distinct from the allocator settings

MTE (ARM Memory Tagging / Memory Integrity Enforcement) is **not** the same as the
software typed-allocator / `hardened-heap` checks above — it is hardware tag-checking on
every memory access, catching use-after-free, heap overflow, OOB, and double-free at runtime.
It is **default-OFF** and gated on hardware (iPhone 17 family, M5-class Macs/iPads, Vision
Pro, and later).

```xml
<key>com.apple.security.hardened-process.checked-allocations</key><true/>
<key>com.apple.security.hardened-process.checked-allocations.soft-mode</key><true/>
```

Overhead is **moderate** (profile it). Adoption path: enable **soft mode** first (simulated
crash reports, no termination) → review reports → fix latent memory bugs → disable soft mode
to enforce. Optional: `…checked-allocations.enable-pure-data`,
`…checked-allocations.no-tagged-receive`.

## Separate opt-ins (NOT cascaded by Enhanced Security)

These change language semantics or require code work, so enable them deliberately, per the
languages actually in the target:

| Setting | Applies to | What you take on |
|---|---|---|
| `ENABLE_CPLUSPLUS_BOUNDS_SAFE_BUFFERS` | C++ | Superset of the cascaded hardened-libc++: adds unsafe-buffer-usage **errors** (raw-pointer indexing/arithmetic, 2-arg `std::span`). Fix by moving to `std::span`/`std::array`/iterators. Override per-file with `_LIBCPP_HARDENING_MODE` (`…_NONE/_FAST/_EXTENSIVE/_DEBUG`) before any STL include. |
| `ENABLE_C_BOUNDS_SAFETY` | **C only** (won't bleed onto C++/ObjC) | Turns on `-fbounds-safety` project-wide. Requires `__counted_by` / `__sized_by` / `__ended_by` annotations on pointers — a real adoption effort; adopt per-file first, then flip this on. Adoption flags: `-fbounds-safety-soft-traps=call-minimal` (log instead of trap during rollout — **must be removed** to get the security benefit), `-fbounds-safety-unique-traps` (don't merge traps; easier optimized-build debugging). Does not apply to Swift. See Apple's C bounds-safety docs for the annotation vocabulary. |

## Static-analyzer security checkers (audit, don't blindly flip)

Most default to `YES` in Xcode; treat them as an **audit** item — flag any explicitly set to
`NO`. Relevant only with C/C++/ObjC sources:

`CLANG_ANALYZER_SECURITY_KEYCHAIN_API`,
`CLANG_ANALYZER_SECURITY_INSECUREAPI_UNCHECKEDRETURN`,
`CLANG_ANALYZER_SECURITY_INSECUREAPI_GETPW_GETS`,
`CLANG_ANALYZER_SECURITY_INSECUREAPI_MKSTEMP`,
`CLANG_ANALYZER_SECURITY_INSECUREAPI_VFORK`,
`CLANG_ANALYZER_SECURITY_INSECUREAPI_RAND`,
`CLANG_ANALYZER_SECURITY_INSECUREAPI_STRCPY`.
For Objective-C blocks / completion handlers, also `CLANG_WARN_COMPLETION_HANDLER_MISUSE`.

## Adoption order (lowest risk → highest)

1. `ENABLE_SECURITY_COMPILER_WARNINGS` diagnostics + `CLANG_ENABLE_STACK_ZERO_INIT` — build-time only / no behavior change. (Both cascade from the master switch.)
2. `ENABLE_ENHANCED_SECURITY = YES` + the required/default-ON entitlements.
3. `ENABLE_POINTER_AUTHENTICATION` — after confirming every binary/SPM dependency has an arm64e slice.
4. `ENABLE_CPLUSPLUS_BOUNDS_SAFE_BUFFERS` / `ENABLE_C_BOUNDS_SAFETY` — code-change work, per language, per file.
5. MTE (`checked-allocations`) in **soft mode** on capable hardware → fix → enforce.

## Verification

- `xcodebuild -showBuildSettings -target <T> | grep -E 'ENHANCED_SECURITY|POINTER_AUTH|STACK_ZERO|BOUNDS_SAF|TYPED_ALLOCATOR|LIBRARY_HARDENING'`
  to confirm resolved values per target.
- Build each non-arm64e target (watchOS/tvOS/Simulator) to confirm the `NO` pointer-auth
  override is in place.
- Enable one setting at a time; a clean build that surfaces new warnings/errors is the
  setting working — fix the findings rather than reverting.
