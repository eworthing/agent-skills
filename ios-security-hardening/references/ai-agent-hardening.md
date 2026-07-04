# Agentic AI Hardening (iOS 27 Foundation Models / App Intents)

The runtime input-validation patterns in the parent skill defend against untrusted
*data*. This reference covers the distinct threat that arrives when an on-device model can
**take actions** on the user's behalf — calling tools, running App Intents, or reading
attacker-influenced content (calendar events, feeds, web results). Length-capping a prompt
does not address it; the exposure is *indirect prompt injection driving real actions*.

Threat framing from **WWDC 2026 session 347** ("Secure your app: mitigate risks to agentic
features") and session 241 ("What's new in Foundation Models"). All symbol names below were
**verified against live DocC JSON on 2026-07-04** (Foundation Models is published to iOS 27.0
beta). Foundation Models is still in beta — re-verify against the SDK you build against, since
signatures can shift before GM.

## Threat model

**The "Lethal Trifecta"** (Apple's framing, session 347). Risk is highest when all three meet
in one feature:

1. **Private-data access** — the model can read the user's data.
2. **Untrusted-content exposure** — that data or context includes attacker-influenced text
   (a calendar invite, an email, a fetched web page, an RSS item).
3. **External-action capability** — the model can call a tool / App Intent that changes state
   or exfiltrates (send a message, move money, make a request).

Remove any one leg and the exploit collapses. Design features so an untrusted-content path and
a high-privilege action path do not share one unmediated model loop.

**Indirect prompt injection = OWASP LLM01.** The attacker does not type into your prompt; they
plant instructions in content the model later ingests. Two failure shapes:

- **Data poisoning** — injected text tampers with the *parameters* of an action the app already
  intended to take (e.g. rewrites the recipient of a legitimate send).
- **Action poisoning** — injected text redirects *which* action runs (e.g. turns a "summarize"
  into a "forward").

## Apple APIs (verified against DocC)

There is **no built-in "redact history" callback and no "intercept tool call" hook** — despite how
the mitigations are described at a concept level. The real control surfaces are more ordinary, and
that is the point: you own them.

| Control surface | Verified API | Notes |
|---|---|---|
| Redact / spotlight untrusted history | **You own the `Transcript`.** No per-turn transform hook exists. Seed or replace the session's history yourself via `LanguageModelSession(model:tools:transcript:)` (or the `history:` init parameters); `Transcript.history` is read-only. | iOS 26.0+. Sanitize/delimit untrusted spans *before* they enter the transcript you hand to the session. |
| Gate a tool call | **Your own `Tool.call(arguments:)` implementation is the interception point** — there is no `onToolCall`. Inspect `arguments`, require confirmation/auth, and `throw` to abort. | `Tool` protocol, iOS 26.0+. Related error: `LanguageModelSession.ToolCallError`. |
| Authenticate a sensitive intent | `static var authenticationPolicy: IntentAuthenticationPolicy` on `AppIntent`; values `.requiresAuthentication` or the stronger `.requiresLocalDeviceAuthentication` (also `.alwaysAllowed`). | App Intents, iOS 16.0+. Blocks Siri / lock-screen / injected triggers from firing it unauthenticated. |
| Detect a guardrail block | **iOS 27+:** `LanguageModelError.guardrailViolation(_:)`. **iOS 26:** `LanguageModelSession.GenerationError.guardrailViolation` — `GenerationError` is **deprecated in iOS 27**, migrate to `LanguageModelError`. (The new `LanguageModelSession.Error` enum does *not* carry this case.) | Always-on system guardrail; necessary but **not sufficient** — see below. |

## Required app-side controls

Apple's stated guidance: prefer **deterministic** mitigations over probabilistic ones — a
probabilistic filter "could be constructed in a way that negates" it. Concretely:

1. **Redact + spotlight untrusted content before it enters the transcript.** You construct the
   `Transcript` you hand the session, so sanitize and delimit attacker-influenced spans there —
   do not let raw untrusted text sit inline with your instructions. There is no framework hook to
   lean on; this is your code.
2. **Confirmation-gate high-risk actions inside `Tool.call(arguments:)`.** That method is where a
   side effect actually happens, so that is where the human approves it — inspect the arguments,
   require confirmation/auth for irreversible or outward-facing calls, and `throw` to abort. The
   model cannot self-authorize past a gate you enforce in your own code.
3. **`.requiresAuthentication` (or `.requiresLocalDeviceAuthentication`) on every sensitive App
   Intent** — financial, messaging, contact, data-deletion. Authentication is a deterministic
   gate; a guardrail is not.
4. **Do not treat the built-in guardrail as your boundary.** Independent testing of the on-device
   model's prompt-injection block rate found it substantially below 100% (NowSecure, 2026-06-11,
   third-party test — *not* an Apple guarantee, methodology-dependent). Your deterministic
   app-side controls are the boundary; the guardrail is defense-in-depth on top.

## Testing

- **Adversarial, not self-attestation.** Test with content crafted to inject — poisoned calendar
  titles, feed items, web snippets — and confirm the confirmation gate / auth still holds.
- `AppIntentsTesting` validates *functional* behavior, **not** security. Passing functional tests
  does not mean the intent is injection-safe.

## Sources

- WWDC 2026 session 347 — *Secure your app: mitigate risks to agentic features*:
  https://developer.apple.com/videos/play/wwdc2026/347/
- WWDC 2026 session 241 — *What's new in Foundation Models*:
  https://developer.apple.com/videos/play/wwdc2026/241/
- NowSecure, *iOS 27 Security: what WWDC 2026's AI features mean for mobile app risk* (2026-06-11):
  https://www.nowsecure.com/blog/2026/06/11/ios-27-security-what-wwdc-2026s-ai-features-mean-for-mobile-app-risk/
- OWASP LLM01 (prompt injection): https://genai.owasp.org/llmrisk/llm01-prompt-injection/
