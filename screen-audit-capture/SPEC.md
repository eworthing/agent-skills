# Screen Audit Capture Skill Specification

## Intent

`screen-audit-capture` makes app screenshots that a visual-audit ledger can rely on. It plans the case, device, orientation and appearance matrix, drives the capture channel, verifies each frame from its pixels, writes a provenance-complete capture manifest and registers it with the ledger CLI.

A capture is worth only what it provably shows. The skill exists so that a frame is never registered on the strength of a file on disk, a passing helper or a log line. Each frame must be looked at, named by its visible state and checked for size, orientation, appearance and duplication.

## Scope

In scope:

- Planning a capture session: cases, devices, orientations, appearances and layouts, with a disposition for every matrix row.
- Driving the channels named in the project profile: simulator, physical iPhone or iPad through an XCUITest helper, iPhone Mirroring (only when the owner approves it for the run), Mac windows (native or iPad or iPhone app on Mac), and public store stills.
- Verifying each image: pixel size, orientation, appearance, visible state, duplicates and blank frames.
- Writing the capture manifest and its coverage rows, then `register --dry-run`, `snapshot`, `register`, `validate` and `check --all` through the ledger CLI.
- Recording blockers with a class and a clearable-by value, and handing back the counts.

Out of scope:

- Scoring, rating, auditing or annotating captures. Those belong to `screen-audit-review`.
- Changing product code, test code, simulator settings, system settings or the gate's simulators.
- Designing or critiquing a screen, validating App Store screenshots for submission, or capturing a screen to clone an app's design.
- Writing scripts. The ledger CLI and the helpers named by the profile do the work.

## Users And Trigger Context

Primary users: agents and engineers who capture screens for a visual-audit ledger, usually Claude sessions that hold a device or Mac.

Triggers (should route here):

- "take light and dark iPad shots of the competitor apps"
- "fill the coverage gaps for the live board screen"
- "recapture the on-Mac frames on the real iPhone"
- "write a capture manifest and register it"

Non-triggers (should route elsewhere):

- "rate these 20 screenshots 1 to 10" (`screen-audit-review`)
- "run the DeepSeek audit batch" (`screen-audit-review`)
- "validate my App Store screenshots" (`axiom:screenshot-validator`)
- "screenshot every screen of this app so I can clone it" (`clone`)
- "review this design mockup" (`design:design-critique`)
- "fix this failing UI test" (`xctest-ui-testing`)

## Runtime Contract

### Hard rules (invariants)

1. Capture at real device size. Simulator and device frames come out at native backing pixels; iPad-on-Mac windows are set to the profile's device-size points. A frame whose pixel size is not in the profile's expected set is refused and logged.
2. Capture each case in light and dark and in both orientations where the session matrix asks. A missing variant gets a disposition (`blocked`, `unavailable`, or `equivalent` with a representative capture ID), never silence.
3. The owner switches system appearance on the Mac and on physical devices. The skill asks, waits, then confirms the appearance from the pixels. Only profile-listed simulators may be switched by the agent.
4. iPad-on-Mac and iPhone-on-Mac captures are labelled non-native (`platform_variant`, `layout_variant`, a NOT NATIVE observation note) and keep a coverage row open for the real-device recapture.
5. Store listing images are tier D `public-still` evidence: valid, always labelled, never counted as a device capture.
6. Verify by looking. A file on disk, a test that passed or a helper that returned is not a captured screen. A case name is used only after the image has been described.
7. A wrong-screen frame (wrong case, mid-transition, sheet already closed, identical to another frame) is not registered. If already registered, it gets a `defect` note with `wrong-case` or `retake`. Personal information visible in a frame is not a defect and is not flagged.
8. A frame is never registered twice. Original files are never deleted. Superseded frames move to a `superseded-*` folder inside the session, with the reason in the session log.
9. `register --dry-run` runs first; `snapshot` runs before any registration that replaces coverage rows; `validate` and `check --all` run after, and the counts are reported.
10. `build` writes into a new, empty output directory, never into the live viewer folder.

### Safety and authorisation

Appendix A of the screen-audit planning document is the canonical shared safety block. The copy in `references/safety-and-authorisation.md` of both skills must stay identical to it; a diff between the two copies is a failed gate.

### Profile discovery order

The skill reads project specifics from a profile and never guesses them.

1. The invoker passes `profile=<path>` in the request. This is the preferred route.
2. Else the environment variable `SCREEN_AUDIT_PROFILE`.
3. Else search the current repository for `*screen-audit-agent-profile*.md`, skipping dependency and build folders (`node_modules/`, `.build/`, `DerivedData/`) and hidden build-output folders. Exactly one hit is used. Zero or several hits: stop and ask.
4. A run never guesses a ledger path, a bundle ID, a device name or an author ID that the profile does not give.

The profile holds the ledger location, the tool's CLI and README paths, the cases file, the app registry, the channels, the expected pixel sizes, the ID patterns and the session caps. The skill body contains none of these values.

### Stop conditions

Sign-in, payment, purchase, subscription, permission, system-setting and web-link prompts stop the capture of that case. The skill records the blocker with its class and clearable-by value and moves to the next case. It continues past a prompt only when the invoker has authorised that specific prompt for this run, and quotes the authorisation.

## Verification Gates

Run these after the skill files are written (the verification task T5 in the implementation plan):

1. Evaluator: `python3 .claude/skills/skill-evaluator-1.0.0/scripts/eval-skill.py screen-audit-capture` (and the same for `screen-audit-review`). Target: all checks pass with no warnings.
2. Size: each `SKILL.md` body (after frontmatter) at most 200 lines and under 16,000 characters; each reference at most 300 lines (`wc -l`).
3. Links: every relative Markdown link in the skill folder resolves to an existing file, and every `references/*.md` is linked from `SKILL.md`.
4. Isolation: a case-insensitive search of both skill folders for project names, home-directory paths, hidden build-output paths, sport names and non-placeholder bundle IDs returns nothing (the exact pattern list is in the T5 brief of the plan), and the Appendix A section of the two `references/safety-and-authorisation.md` files is identical (`diff`).
5. Repository hygiene: `git status --short` shows only the two skill folders and the README index lines as changes made by this work. No Python is added; if a `.py` file exists, `ruff check` and `ruff format --check` must pass.
6. Triggers: a fresh subagent given only the frontmatter descriptions and the neighbouring skill descriptions routes each prompt in the trigger lists above as stated.
7. Behavioral evals: the cases in `evals/evals.json` are run with a subagent holding the skill, graded against their assertions. Results, model and date go in `EVAL.md`; cases not run are listed as owed.

## Reference Architecture

- `SKILL.md`: lean runtime router (at most 200 body lines). Purpose, pre-flight steps, hard rules, channel picker, workflow, verification, manifest essentials, hand-back, stop conditions, and a reference router.
- `SPEC.md`: this specification.
- `EVAL.md`: evaluator score, behavioral eval results and owed cases.
- `evals/evals.json`: six behavioral cases (matrix planning, mid-run permission, file-exists trap, iPad-on-Mac labels, store art, negative trigger).
- `references/safety-and-authorisation.md`: Appendix A in full, the authorisation record format, and the decision table for prompts, settings and web links.
- `references/channels.md`: per-channel preconditions, steps, capture commands and limits (simulator, physical device, Mirroring, Mac, public stills).
- `references/manifest-and-naming.md`: manifest shape, field table, filename and capture-ID patterns, vocabulary and coverage-row rules.
- `references/verify-from-pixels.md`: the per-image checklist with commands, expected-pixel lookup and duplicate checks.
- `references/failure-patterns.md`: symptom, cause, fix and record table for stalls, duplicates, alerts, rotation, appearance and registration rejects.
- `references/profile-template.md`: the profile schema with one line per field and the fields capture needs.
