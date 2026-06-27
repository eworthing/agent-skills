<!-- Spliced into CURRENT_REVIEW.md under "## Findings" as the targeted Priority-1
finding. The loop_result section below records the Unified Seam Policy justification
the reviewer reads during Check 2. -->

Discovery lens: lens-apple.md

### F1 — AudioSessionManager calls AVAudioSession directly; hardware-bound errors propagate to callers with no isolation (Priority 1)

- **Claim:** `AudioSessionManager` calls `AVAudioSession.sharedInstance()` inline in three methods, so `setCategory(_:mode:)` and `setActive(_:)` errors throw directly to callers (`PlaybackEngine`, `RecorderCoordinator`, `OnboardingPermissionFlow`). No Seam isolates the hardware-bound API surface.
- **Source:** `Sources/AudioSessionManager.swift:10` (`try session.setCategory(.playback, mode: .default)`), `:16` (`try session.setCategory(.record, mode: .measurement)`), `:22` (`try AVAudioSession.sharedInstance().setActive(false)`) — direct AVAudioSession calls; no protocol boundary at any injection site.
- **Consequence:** tests that exercise `PlaybackEngine` or `RecorderCoordinator` call real AVAudioSession, which requires audio hardware (fails on CI simulators in audio-restricted environments); route-change and interruption behavior cannot be simulated. Dependency category: `true-external` (hardware-bound platform API).
- **Severity:** Serious deduction.
- **Remedy (minimal_correction_path):** introduce a protocol Seam at the AVAudioSession boundary. A single prod adapter is justified under Unified Seam Policy (b)(iii) — see loop_result below.

**loop_result Unified Seam Policy justification:** the new `AudioSessionConfiguring` protocol has one prod adapter (`SystemAudioSessionConfigurator`). This satisfies Unified Seam Policy (b)(iii) platform-isolation: `AVAudioSession` is a hardware-bound system API with no test harness — it falls within the "SDK with no test harness, e.g. Spotify SDK, hardware-bound APIs" carve-out stated verbatim in the policy. `setCategory(_:mode:)` and `setActive(_:)` interact with real audio hardware and cannot be reliably stubbed at the framework level; the protocol boundary enables injecting a `ThrowingAudioSessionConfigurator` (for error-path tests) or a `NoOpAudioSessionConfigurator` (for CI environments without audio hardware). No second adapter is required when (b)(iii) applies. Evidence recorded in loop artifacts; no open questions.
